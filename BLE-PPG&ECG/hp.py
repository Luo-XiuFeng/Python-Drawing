# -*- coding: utf-8 -*-
import asyncio
from asyncio.tasks import sleep
from asyncio.windows_events import SelectorEventLoop
from pickle import TRUE
import logging
import numpy as np
import struct
import array
from pandocfilters import Null
from scipy.spatial.transform import Rotation as R
import pyqtgraph as pg
from queue import Queue
from ctypes import *
from threading import Timer
from PyQt5 import QtWidgets,QtCore,QtGui
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Circle
import matplotlib.gridspec
import heartpy as hp
import time
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FC
from PyQt5.QtWidgets import (QWidget, QApplication, QComboBox, QLabel, QPushButton, QHBoxLayout,
                             QVBoxLayout, QToolTip, QMessageBox)
from PyQt5.QtGui import QIntValidator,QDoubleValidator,QRegExpValidator
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from enum import Enum
import neurokit2 as nk
import pandas as pd
from scipy.fftpack import fft,ifft
import numpy.fft as fft

from bleak import BleakClient
from bleak import discover

# sample_rate = 25
# data = hp.get_data(r'C:\Users\LUOXF\Desktop\心率验证\data.txt')



class DynamicEoStatic(Enum):
    Dynamic  = 0
    static   = 1 

class DynamicSon(Enum):
    PPG   = 0
    ECG   = 1 



def hex2dec(string_num): 
  return str(int(string_num.upper(), 16)) 


class MainUi(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainUi,self).__init__()

        # 解决无法显示中文
        plt.rcParams['font.sans-serif'] = ['SimHei']
        # 解决无法显示负号
        plt.rcParams['axes.unicode_minus'] = False

        #主窗口标签页
        self.MainTabLocation = 0
        #动态界面子图标签页
        self.DynamicSonTabLocation = 0


        #程序名
        self.setWindowTitle("BleTool-PPG-ECG")
        
        #主页
        self.maintab = QTabWidget(self)
        
        self.DynamicState()
        self.staticAnalysis()

        #主窗口tab切换回调
        self.maintab.currentChanged.connect(self.DynamicToStaticTabChange)
        self.setCentralWidget(self.maintab)


    #主窗口tab
    def DynamicToStaticTabChange(self,tab):
        self.MainTabLocation = DynamicEoStatic(tab)
     
       


        # self.ax.cla()
        # self.fig.canvas.draw()  # 这里注意是画布重绘，self.figs.canvas
        # self.fig.canvas.flush_events()  # 画布刷新self.figs.canvas
        # print(tab)
       
     #动态界面的子tab---ppg——ecg  
    def DynamicSonTabChange(self,tab):
        self.DynamicSonTabLocation = DynamicSon(tab)
        if(self.DynamicSonTabLocation == DynamicSon.PPG):
            self.plot_plt.setTitle("心率:",size='16pt',color='r')
        elif(self.DynamicSonTabLocation == DynamicSon.ECG):
            self.plot_plt.setTitle("",size='16pt',color='r')



    #静态
    def staticAnalysis(self):

        self.ppgdata = []
        self.hrdata  = []
        self.NormalizedFlag = False

        #静态采样频率
        self.staticSampling = 0

        #允许拖拽文件
        self.setAcceptDrops(True)

        

        self.staticAnalysis_widget = QWidget() # 创建一个主部件
        self.staticAnalysislayout  = QtWidgets.QGridLayout() # 创建一个网格布局
        self.staticAnalysis_widget.setLayout(self.staticAnalysislayout) # 设置主部件的布局为网格
        self.maintab.addTab(self.staticAnalysis_widget,'静态数据分析')
        

        #o工具栏
        self.staticTool = QtWidgets.QGroupBox("")
        self.statictoollayout = QHBoxLayout()

        #采样率
        self.staticLabel = QtWidgets.QLabel("采样率(hz)：")
        self.staticinput = QtWidgets.QLineEdit()
            #实例化整型验证器，并设置范围为1-99
        staticpIntvalidator=QIntValidator(self)
        staticpIntvalidator.setRange(10,1000)
        self.staticinput.setPlaceholderText("10-1000hz,输入并回车")
        self.staticinput.setValidator(staticpIntvalidator)
        self.staticinput.editingFinished.connect(self.staticinputsampling)
        self.statictoollayout.addWidget(self.staticLabel)
        self.statictoollayout.addWidget(self.staticinput)

        #归一化勾选框
        self.checkNormalized = QCheckBox('归一化', self)
        self.checkNormalized.stateChanged.connect(self.checkNormalizedPos)
        self.statictoollayout.addWidget(self.checkNormalized)


        #打开文件
        self.pushButton = QtWidgets.QPushButton()
        self.pushButton.setObjectName("pushButton")
        self.pushButton.setText("打开数据")
        self.pushButton.clicked.connect(self.openfile)
        self.statictoollayout.addWidget(self.pushButton)

        #数据info
        self.datainfo = QLineEdit()
        # self.datainfo.setText("1531655")
        self.datainfo.setEnabled(False)
        self.statictoollayout.addWidget(self.datainfo)

        #切片按钮
        self.DataSliceButt = QPushButton('切片', self)
        self.DataSliceButt.clicked.connect(self.DataSlice)
        self.statictoollayout.addWidget(self.DataSliceButt)

        #切片恢复按钮
        self.DataSliceResButt = QPushButton('切片恢复', self)
        self.DataSliceResButt.clicked.connect(self.DataSliceRestore)
        self.statictoollayout.addWidget(self.DataSliceResButt)


        #弹簧
        self.statictoollayout.addStretch(1)
        self.staticTool.setLayout(self.statictoollayout)



        #曲线图
        self.staticgraph  = QtWidgets.QGroupBox("")
        self.staticlayout = QtWidgets.QFormLayout()
        self.staticfig    = plt.Figure(figsize=(10,10),dpi=100)
        self.staticcanvas = FC(self.staticfig)
        self.fig_ntb1 = NavigationToolbar(self.staticcanvas,self)

        #缩放图工具加到工具栏去
        self.statictoollayout.addWidget(self.fig_ntb1)
        self.statictoollayout.addStretch(6)

        #宽高比例
        ggs = matplotlib.gridspec.GridSpec(3,3,width_ratios=[1,1,2],height_ratios=[1,1,1])
        #左右上下间距 行和列间距
        ggs.update(left=0.025,right=0.99,top=0.96,bottom=0.05,wspace=0.2,hspace=0.3)
       
        self.original  = self.staticfig.add_subplot(ggs[0,0:2])
        self.original.set_title('原始数据、汇顶心率值、自算法心率',fontsize=13)
        self.hr = self.original.twinx()
        self.bpm = self.original.twinx()
        #多轴间距
        rspine = self.bpm.spines['right']
        rspine.set_position(('axes', 1.023))



        self.ppgpeak   = self.staticfig.add_subplot(ggs[1,:-1])
        self.ppgpeak.set_title('带通滤波、峰值查找及平均心率估算',fontsize=13)

        self.ppg5sbpm  = self.staticfig.add_subplot(ggs[2,0])
        self.ppg5sbpm.set_title('分段心率值',fontsize=13)

        self.breathing = self.staticfig.add_subplot(ggs[2,1])
        self.breathing.set_title('呼吸率',fontsize=13)

        self.spectrum =  self.staticfig.add_subplot(ggs[0,-1])
        self.spectrum.set_title('频谱',fontsize=13)

        self.poincare  = self.staticfig.add_subplot(ggs[1:,-1])
        self.poincare.set_title('庞加莱HRV',fontsize=13)


        
        # self.staticfig.tight_layout() 
        self.staticfig.canvas.draw()          # 这里注意是画布重绘
        self.staticfig.canvas.flush_events()  # 画布刷新
        
     
        self.staticlayout.addWidget(self.staticcanvas) 
        self.staticgraph.setLayout(self.staticlayout)

        #注册鼠标缩放
        self.staticfig.canvas.mpl_connect('scroll_event', self.call_back)

        #加入到总图中
        self.staticAnalysislayout.addWidget(self.staticTool, 0, 0)
        self.staticAnalysislayout.addWidget(self.staticgraph, 1, 0)
        self.staticAnalysislayout.setRowStretch(0, 1)
        self.staticAnalysislayout.setRowStretch(1, 99)


    #动态
    def DynamicState(self):

        self.mainwidget = QWidget() # 创建一个主部件
        self.mainwlayout = QtWidgets.QGridLayout() # 创建一个网格布局
        self.mainwidget.setLayout(self.mainwlayout) # 设置主部件的布局为网格
        self.maintab.addTab(self.mainwidget,'动态数据分析')
        

        self.tab = QTabWidget(self)

        #动态子tab标签回调
        self.tab.currentChanged.connect(self.DynamicSonTabChange)

        self.toolui()
        self.ppg_ui()
        self.ecg_ui()
        self.mainwlayout.addWidget(self.info, 1, 0, 1, 2)
        self.mainwlayout.addWidget(self.line, 2, 0, 1, 2)
        self.mainwlayout.addWidget(self.tab,  3, 0, 1, 2)

    def toolui(self):

        #设备连接状态
        self.linksta = False

        #工具界面
        self.info = QtWidgets.QGroupBox("")
            #盒式布局
        self.layout = QHBoxLayout()

            #采样率
        self.performanceLabel = QtWidgets.QLabel("采样率(hz)：")
        self.performanceLabel1 = QtWidgets.QLineEdit()
            #实例化整型验证器，并设置范围为1-99
        pIntvalidator=QIntValidator(self)
        pIntvalidator.setRange(10,1000)
        self.performanceLabel1.setPlaceholderText("10-1000hz,输入并回车")
        self.performanceLabel1.setValidator(pIntvalidator)
        self.performanceLabel1.editingFinished.connect(self.inputsampling)
        self.layout.addWidget(self.performanceLabel)
        self.layout.addWidget(self.performanceLabel1)
        

            #ble设备下拉     
        self.cb = QComboBox(self)
        self.cb.addItem("                                             ")
        self.layout.addWidget(self.cb)

            #扫描
        self.BLE_Scan_button = QPushButton(u'扫描')          
        self.BLE_Scan_button.setToolTip("start Ble device scan")    
        self.BLE_Scan_button.clicked.connect(self.BLE_Scan_handle)   
        self.layout.addWidget(self.BLE_Scan_button)

            #连接
        self.BLE_link_button = QPushButton(u'连接')         
        # self.BLE_link_button.setToolTip("start qt test")   
        self.BLE_link_button.clicked.connect(self.BLE_link_handle)   
        self.layout.addWidget(self.BLE_link_button)
        self.BLE_link_button.setEnabled(False)
        
            #断开
        self.BLE_dis_button = QPushButton(u'断开')         
        self.BLE_dis_button.clicked.connect(self.BLE_dis_handle)   
        self.layout.addWidget(self.BLE_dis_button)
        self.BLE_dis_button.setEnabled(False)
            #弹簧
        self.layout.addStretch(1)
        self.info.setLayout(self.layout)




        #曲线
        self.savedatasize = 300
        self.savenum=0
        self.line = QtWidgets.QGroupBox("")
        self.linelayout = QtWidgets.QFormLayout()
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.plot_plt = pg.PlotWidget() # 实例化一个绘图部件
        self.plot_plt.showGrid(x=True,y=True) # 显示图形网格
        # self.plot_plt.setTitle("心率:",size='16pt',color='r')
        # self.plot_plt.setYRange(min=0)
    
        self.linelayout.addWidget(self.plot_plt) # 添加绘图部件到K线图部件的网格布局层
        # self.line.setFixedSize(800,200)
        self.line.setLayout(self.linelayout)

            # 可动态改变数组的大小,double型数组
            #把数组长度定下来
        self.data = array.array('i') 
        self.data = np.zeros(self.savedatasize).__array__('d') 
        self.curve = self.plot_plt.plot(name="mode2",width=30,pen=pg.mkPen({'color': "#FF0000", 'width': 2}))
        self.ptr1 =0

            # 设定定时器  连接时启动
        self.timer = pg.QtCore.QTimer()
        self.timer.setTimerType(Qt.PreciseTimer)  # 关键的一步，取消默认的精度设置
            # 定时器信号绑定 update_data 函数
        self.timer.timeout.connect(self.update_data)


        
        

    def ppg_ui(self):
        
        #曲线数据
        self.PPG = Queue(maxsize=0)
        #ppg采样率
        self.ppgsampling =0
        #用于计算的原始数据
        self.ppgalgodata =[]
        self.Dhrdata =[]

        self.normalizedorig =[]
        #归一化后数据
        self.normalizedData =[]


        self.ppgui_widget = QWidget() # 创建一个主部件
        self.tab.addTab(self.ppgui_widget,'PPG')
        self.ppg_layout = QtWidgets.QGridLayout() # 创建一个网格布局
        self.ppgui_widget.setLayout(self.ppg_layout) # 设置主部件的布局为网格


        #PPG
        # self.graph = QtWidgets.QGroupBox("")
        self.graphlayout = QtWidgets.QFormLayout()
        self.fig = plt.Figure(figsize=(8,8),dpi=100)
        self.canvas = FC(self.fig)
        
        


        #宽高比例
        gs = matplotlib.gridspec.GridSpec(3,3,width_ratios=[1,1,1],height_ratios=[1,1,1])
        #左右上下间距 列和行间距
        gs.update(left=0.024,right=0.995,top=0.96,bottom=0.05,wspace=0.2,hspace=0.4)


        self.ax = self.fig.add_subplot(gs[0,:-1])
        self.ax.set_title('原始数据、汇顶心率值、自算法心率(t-1)',fontsize=13)
        self.axhr = self.ax.twinx()
        self.axbpm = self.ax.twinx()
        #多轴间距
        Drspine = self.axbpm.spines['right']
        Drspine.set_position(('axes', 1.026))
        
        
    
        self.bx = self.fig.add_subplot(gs[1,:-1])
        self.bx.set_title('带通滤波、峰值查找及平均心率估算(t-1)',fontsize=13)
        
       
       

        self.cx = self.fig.add_subplot(gs[2,:-1])
        self.cx.set_title('呼吸频率(t-1)',fontsize=13)

        self.dx = self.fig.add_subplot(gs[:,-1])
        self.dx.set_title('频谱(t-1)',fontsize=13)

            #注册鼠标缩放
        self.fig.canvas.mpl_connect('scroll_event', self.call_back)
        # self.PoincareGraph.canvas.mpl_connect('scroll_event', self.call_back1)

            #自动排列避免重叠
        self.fig.tight_layout() 


        # 将上述部件添加到布局层中 件名，行，列，占用行数，占用列数，对齐方式
        # self.ppg_layout.addWidget(self.fig_ntb1,1, 0, 1, 1)
      
        self.ppg_layout.addWidget(self.canvas,1, 0, 1, 1)

        
    def ecg_ui(self):
        self.ecgui_widget = QWidget() # 创建一个主部件
        self.ecg_layout = QtWidgets.QGridLayout() # 创建一个网格布局
        self.ecgui_widget.setLayout(self.ecg_layout) # 设置主部件的布局为网格
        self.tab.addTab(self.ecgui_widget,'ECG')

        
    #静态的算法   
    def staticAlgoPPG(self,data,hrdata,sampling):

        self.original.cla()
        self.hr.cla()
        self.ppgpeak.cla()
        self.ppg5sbpm.cla()
        self.breathing.cla()
        self.poincare.cla()
        self.bpm.cla()
        self.spectrum.cla()

        if(self.NormalizedFlag):
            orig = self.datanormalized(data)
        else:
            orig = data





        # # Process it
        # signals, info = nk.rsp_process(orig, sampling)
        # # Visualise the processing
        # nk.rsp_plot(signals, sampling)



        # # Process it
        # signals, info = nk.ppg_process(orig, sampling)
        # # Visualize the processing
        # nk.ppg_plot(signals, sampling)
   



        try:
            #滤波
            self.filtered_ppg = hp.filter_signal(orig, 
                                            cutoff = [0.8, 2.5], 
                                            filtertype = 'bandpass',
                                            sample_rate = sampling,
                                            order = 3,
                                            return_top = False)
    
            working_data, measures = hp.process_segmentwise(self.filtered_ppg, sample_rate=sampling, segment_width = 10, segment_overlap = 0.2)
            wd, m = hp.process(self.filtered_ppg, sample_rate= sampling,high_precision = True)


        except:
            self.messageDialog('数据异常，请切片处理')
            self.original.set_title('原始数据、汇顶心率值、自算法心率',fontsize=13)
            # self.ax.set_xlabel('dot')
            self.original.plot(orig,'-', label = '原始数据',color="green")
            self.hr.plot(hrdata,color="r", label = '汇顶心率值',linestyle=':')
            #x轴
            bpmx = np.arange(10*25,len(orig),8*25)
            rspine = self.bpm.spines['right']
            rspine.set_position(('axes', 1.04))
            if 'bpm' in measures:
                self.bpm.scatter(bpmx, measures['bpm'],label = '自算法心率值')
                for i in range(len(bpmx)):
                    self.bpm.annotate("%.1f" % measures['bpm'][i], xy = (bpmx[i], measures['bpm'][i]), xytext = (bpmx[i]+0.1, measures['bpm'][i]+0.1) )
                self.staticfig.legend(loc=1, bbox_to_anchor=(1,1), bbox_transform=self.original.transAxes)
            # self.original.set_xlabel("point")
            # self.hr.set_ylabel(r"汇顶心率值")
            # self.bpm.set_ylabel(r"自算法心率值")

            Fs = sampling;        # 采样频率
            T = 1/Fs;             # 采样周期
            L = len(orig);        # 信号长度
            t = [i*T for i in range(L)]
            t = np.array(t)
            complex_array = fft.fft(orig)
            # 得到分解波的频率序列
            freqs = fft.fftfreq(t.size, t[1] - t[0])
            # 复数的模为信号的振幅（能量大小）
            pows = np.abs(complex_array)
            self.spectrum.plot(freqs[freqs > 0], pows[freqs > 0], c='orangered', label='Frequency')
            self.spectrum.set_title('频谱',fontsize=13)
        else:

            self.original.set_title('原始数据、汇顶心率值、自算法心率',fontsize=13)
            # self.ax.set_xlabel('dot')
            self.original.plot(orig,'-', label = '原始数据',color="green")
            self.hr.plot(hrdata,color="r", label = '汇顶心率值',linestyle=':')
            #x轴
            bpmx = np.arange(10*25,len(orig),8*25)
            rspine = self.bpm.spines['right']
            rspine.set_position(('axes', 1.04))
            if 'bpm' in measures:
                self.bpm.scatter(bpmx, measures['bpm'],label = '自算法心率值')
                for i in range(len(bpmx)):
                    self.bpm.annotate("%.1f" % measures['bpm'][i], xy = (bpmx[i], measures['bpm'][i]), xytext = (bpmx[i]+0.1, measures['bpm'][i]+0.1) )
                self.staticfig.legend(loc=1, bbox_to_anchor=(1,1), bbox_transform=self.original.transAxes)
            # self.original.set_xlabel("point")
            # self.hr.set_ylabel(r"汇顶心率值")
            # self.bpm.set_ylabel(r"自算法心率值")

            Fs = sampling;        # 采样频率
            T = 1/Fs;             # 采样周期
            L = len(orig);        # 信号长度
            t = [i*T for i in range(L)]
            t = np.array(t)
            complex_array = fft.fft(orig)
            # 得到分解波的频率序列
            freqs = fft.fftfreq(t.size, t[1] - t[0])
            # 复数的模为信号的振幅（能量大小）
            pows = np.abs(complex_array)
            self.spectrum.plot(freqs[freqs > 0], pows[freqs > 0], c='orangered', label='Frequency')
            self.spectrum.set_title('频谱',fontsize=13)




            if(wd or m):
                fs = wd['sample_rate']
                plotx = np.arange(0, len(wd['hr'])/fs, 1/fs)
                
                #check if there's a rounding error causing differing lengths of plotx and signal
                diff = len(plotx) - len(wd['hr'])
                if diff < 0:
                    #add to linspace
                    plotx = np.append(plotx, plotx[-1] + (plotx[-2] - plotx[-1]))
                elif diff > 0:
                    #trim linspace
                    plotx = plotx[0:-diff]
                    
                peaklist = wd['peaklist']
                ybeat = wd['ybeat']
                rejectedpeaks = wd['removed_beats']
                rejectedpeaks_y = wd['removed_beats_y']

                

                #PPG 带通滤波心率估算
                self.ppgpeak.set_title('带通滤波、峰值查找及平均心率估算',fontsize=13)
                # self.ax.set_xlabel('Time(t-1)')
                self.ppgpeak.plot(plotx, wd['hr'], color="dodgerblue", label='滤波数据', zorder=-10)
                self.ppgpeak.scatter(np.asarray(peaklist)/fs, ybeat, color="red",label='平均BPM:%.2f' %(m['bpm']))
                self.ppgpeak.scatter(rejectedpeaks/fs, rejectedpeaks_y,color="fuchsia", label='废弃心峰')
                self.ppgpeak.legend(loc=4,fontsize=12,framealpha=0.5)


                if 'bpm' in measures:
                    bpmx =  np.arange(0, len(measures['bpm']), 1)
                    self.ppg5sbpm.plot(bpmx,measures['bpm'],color="orange")
                    self.ppg5sbpm.set_title('分段心率值',fontsize=13)
                    for i in range(len(bpmx)):
                        self.ppg5sbpm.annotate("%.1f" % measures['bpm'][i], xy = (bpmx[i], measures['bpm'][i]), xytext = (bpmx[i]+0.1, measures['bpm'][i]+0.1) )

                # self.ax.set_xlabel('ms')''
                self.breathing.set_title('呼吸信号',fontsize=13)
                if "breathing_signal" in wd:
                    self.breathing.plot(wd['breathing_signal'], color="m", label='呼吸频率:%.2f hz' %(m['breathingrate'] ))
                    self.breathing.legend(loc=4,fontsize=12,framealpha=0.5)
            
                
                self.poincare.set_title('RR间期庞加莱图')
                if "poincare" in wd:
                    #get values from dict
                    self.x_plus = wd['poincare']['x_plus']
                    self.x_minus = wd['poincare']['x_minus']
                    self.sd1 = m['sd1']
                    self.sd2 = m['sd2']


                if(len(self.x_plus)>0):

                    #plot scatter
                    self.poincare.scatter(self.x_plus, self.x_minus, color = "red",alpha = 0.75, label = 'RR间隔')

                    #plot identity line
                    mins = np.min([self.x_plus, self.x_minus])
                    maxs = np.max([self.x_plus, self.x_minus])
                    identity_line = np.linspace(np.min(mins), np.max(maxs))
                    
                    self.poincare.plot(identity_line, identity_line, color='black',alpha=0.5,label = '标示线')
                    
                    #rotate SD1, SD2 vectors 45 degrees counterclockwise
                    sd1_xrot, sd1_yrot = self.rotate_vec(0, self.sd1, 45)
                    sd2_xrot, sd2_yrot = self.rotate_vec(0, self.sd2, 45)

                    #plot rotated SD1, SD2 lines
                    self.poincare.plot([np.mean(self.x_plus), np.mean(self.x_plus) + sd1_xrot],
                            [np.mean(self.x_minus), np.mean(self.x_minus) + sd1_yrot],
                            color = "blue", label = 'SD1:%.2fms' %(m['sd1']))
                    self.poincare.plot([np.mean(self.x_plus), np.mean(self.x_plus) - sd2_xrot],
                            [np.mean(self.x_minus), np.mean(self.x_minus) + sd2_yrot],
                            color = "gold", label =  'SD2:%.2fms' %(m['sd2']))

                    #plot ellipse
                    xmn = np.mean(self.x_plus)
                    ymn = np.mean(self.x_minus)
                    el = Ellipse((xmn, ymn), width = self.sd2 * 2, height = self.sd1 * 2, angle = 45.0,facecolor= 'yellow', alpha=0.3)
                    self.poincare.add_artist(el)
                    el.set_edgecolor((0,0,0))
                    #不显示填充色
                    el.fill = False

                    self.poincare.set_xlabel('RRi_n (ms)')
                    self.poincare.set_ylabel('RRi_n+1 (ms)')

                    self.poincare.plot(identity_line,identity_line,alpha = 0,color='white',label = 'SDNN(RR间隔标准偏差):%.2f ms' %(m['sdnn']))
                    self.poincare.plot(identity_line, identity_line, alpha = 0,color='white',label = 'RMSSD(逐次差均方根):%.2f ms'%(m['rmssd']))
                    self.poincare.legend(loc=4,fontsize=10,framealpha=0.5)


                for key in m.keys():
                    print('%s: %f' %(key, m[key]))


        #自动排列避免重叠
        self.staticfig.tight_layout() 
        self.staticfig.canvas.draw()  # 这里注意是画布重绘，self.figs.canvas
        self.staticfig.canvas.flush_events()  # 画布刷新self.figs.canvas


    


    #画布清除
    def canvasclean(self):
        self.staticPPG.cla()
        self.algoPPG.cla()
        self.staticfig.tight_layout() 
        self.staticfig.canvas.draw()          # 这里注意是画布重绘，self.figs.canvas
        self.staticfig.canvas.flush_events()  # 画布刷新self.figs.canvas


    #ppg算法
    def DynamicAlgoPPG(self,data,hrdata,sampling):
        
        self.ax.cla()
        self.axhr.cla()
        self.axbpm.cla()
        self.bx.cla()
        self.cx.cla()
        self.dx.cla()

        try:
            
            #计算
            self.filtered_ppg = hp.filter_signal(data, 
                                            cutoff = [0.8, 2.5], 
                                            filtertype = 'bandpass',
                                            sample_rate = sampling,
                                            order = 3,
                                            return_top = False)

            working_data, measures = hp.process_segmentwise(self.filtered_ppg, sample_rate=sampling, segment_width = 9, segment_overlap = 0)
            wd, m = hp.process(self.filtered_ppg, sample_rate= sampling,high_precision = True)

        except:
            # self.messageDialog('数据异常，请切片处理')
            print('数据异常，请切片处理')
        else:

            self.ax.set_title('原始数据、汇顶心率值、自算法心率',fontsize=13)
            # self.ax.set_xlabel('dot')
            self.ax.plot(data,'-', label = '原始数据',color="green")


            #标签x轴的位置
            bpmx = np.arange(9*25,len(data),9*25)
            self.axhr.scatter(0,hex2dec(hrdata),color="white",label = '汇顶心率值%.2f' % float(hex2dec(hrdata)))
            # self.axhr.annotate(format(hex2dec(hrdata)), xy = (0, hex2dec(hrdata)), xytext = (0,hex2dec(hrdata)))
            


            if 'bpm' in measures:
                Drspine = self.axbpm.spines['right']
                Drspine.set_position(('axes', 1.03))
                self.axbpm.scatter(0,measures['bpm'][0],color="white",label = '自算法心率值:%.2f'%(measures['bpm'][0]))
                # self.axbpm.annotate("%.1f" % measures['bpm'][0], xy = (5, measures['bpm'][0]), xytext = (5+0.1, measures['bpm'][0]+0.1) )
                


            self.fig.legend(loc=1,bbox_to_anchor=(1,1),bbox_transform=self.ax.transAxes)
           


            Fs = sampling;        # 采样频率
            T = 1/Fs;             # 采样周期
            L = len(data);        # 信号长度
            t = [i*T for i in range(L)]
            t = np.array(t)
            complex_array = fft.fft(data)
            # 得到分解波的频率序列
            freqs = fft.fftfreq(t.size, t[1] - t[0])
            # 复数的模为信号的振幅（能量大小）
            pows = np.abs(complex_array)
            self.dx.plot(freqs[freqs > 0], pows[freqs > 0], c='orangered', label='Frequency')
            self.dx.set_title('频谱',fontsize=13)

                            

            if(wd or m):
                
                fs = wd['sample_rate']
                plotx = np.arange(0, len(wd['hr'])/fs, 1/fs)
                #check if there's a rounding error causing differing lengths of plotx and signal
                diff = len(plotx) - len(wd['hr'])
                if diff < 0:
                    #add to linspace
                    plotx = np.append(plotx, plotx[-1] + (plotx[-2] - plotx[-1]))
                elif diff > 0:
                    #trim linspace
                    plotx = plotx[0:-diff]
                    
                peaklist = wd['peaklist']
                ybeat = wd['ybeat']
                rejectedpeaks = wd['removed_beats']
                rejectedpeaks_y = wd['removed_beats_y']

    
                
                #PPG 带通滤波心率估算
                self.bx.set_title('带通滤波器后心率估算(t-1)',fontsize=13)
                # self.ax.set_xlabel('Time(t-1)')
                self.bx.plot(plotx, wd['hr'], color="dodgerblue", label='PPG滤波数据', zorder=-10)
                self.bx.scatter(np.asarray(peaklist)/fs, ybeat, color="red",label='平均BPM:%.2f' %(m['bpm']))
                self.bx.scatter(rejectedpeaks/fs, rejectedpeaks_y,color="fuchsia", label='废弃心峰')
                self.bx.legend(loc=4,fontsize=10,framealpha=0.5)


           
                # self.ax.set_xlabel('ms')''
                self.cx.set_title('呼吸信号(t-1)',fontsize=13)
                if "breathing_signal" in wd:
                    self.cx.plot(wd['breathing_signal'], color="dodgerblue", label='呼吸频率:%.2f hz' %(m['breathingrate'] ))
                    self.cx.legend(loc=4,fontsize=10,framealpha=0.5)
       
        
 


                for key in m.keys():
                    print('%s: %f' %(key, m[key]))
          

            #自动排列避免重叠
            self.fig.tight_layout() 
            # self.PoincareGraph.tight_layout() 
            
            self.fig.canvas.draw()  # 这里注意是画布重绘，self.figs.canvas
            self.fig.canvas.flush_events()  # 画布刷新self.figs.canvas

            # self.PoincareGraph.canvas.draw()
            # self.PoincareGraph.canvas.flush_events()



    def rotate_vec(self,x, y, angle):

        theta = np.radians(angle)

        cs = np.cos(theta)
        sn = np.sin(theta)

        x_rot = (x * cs) - (y * sn)
        y_rot = (x * sn) + (y * cs)

        return x_rot, y_rot

    #动态输入频率
    def inputsampling(self):
        self.ppgsampling = int(self.performanceLabel1.text())

    #静态输入频率     
    def staticinputsampling(self):
        self.staticSampling = int(self.staticinput.text())  


    #鼠标处理    
    def call_back(self,event):
        axtemp=event.inaxes
        x_min, x_max = axtemp.get_xlim()
        fanwei = (x_max - x_min) / 10
        if event.button == 'up':
            axtemp.set(xlim=(x_min + fanwei, x_max - fanwei))
            # print('up')
        elif event.button == 'down':
            axtemp.set(xlim=(x_min - fanwei, x_max + fanwei))
            # print('down')
        elif event.button == 'left':
            print("121212")

        if(self.MainTabLocation == DynamicEoStatic.Dynamic):
            self.fig.canvas.draw_idle()  # 绘图动作实时反映在图像上
        elif(self.MainTabLocation == DynamicEoStatic.static):
            self.staticfig.canvas.draw_idle()  # 绘图动作实时反映在图像上




    #扫描协程创建
    def BLE_Scan_handle(self):
        #扫描灰色
        self.BLE_Scan_button.setEnabled(False)
        self.BLE_dis_button.setEnabled(False)
        self.cb.clear()
        self.timer_start(0.001,self.BLE_Scan)
            
    #扫描协程
    def BLE_Scan(self):
        self.loop = asyncio.new_event_loop()
        self.loop.run_until_complete(self.scan())
        self.loop.close()
        

    #5s
    async def scan(self):
        self.dev = await discover()
        for i in range(0,len(self.dev)):
            self.cb.addItem( str(i) + "  " + self.dev[i].name + "  " + self.dev[i].address + "  " + str(self.dev[i].rssi) + "rssi")
        #扫描恢复
        self.BLE_Scan_button.setEnabled(True)
        self.BLE_link_button.setEnabled(True)

    #连接
    def BLE_link_handle(self):
        if self.performanceLabel1.text():
            self.BLE_Scan_button.setEnabled(False)
            self.BLE_link_button.setEnabled(False)
            self.BLE_dis_button.setEnabled(True)

            self.select = self.cb.currentText()
            self.bleMac = self.dev[int(self.select[0:2])].address
            print(self.bleMac)

            #启动曲线数据刷新线程
            self.timer.start(40)
            self.timer_start(0.001,self.wait_link)
            self.timer_start(0.1,self.Count)
        else:
            self.messageDialog('输入采样频率')


    # 并发 异步连接 
    def wait_link(self):
        self.loop1 = asyncio.new_event_loop()
        self.loop1.run_until_complete(self.run())

    #ble连接查找服务订阅通知
    async def run(self,debug=0):
        
        log = logging.getLogger(__name__)
        if debug:   
            import sys

            # log.setLevel(logging.DEBUG)
            # h = logging.StreamHandler(sys.stdout)
            # h.setLevel(logging.DEBUG)
            # log.addHandler(h)
        
        async with BleakClient(self.bleMac) as self.client:
            x = await self.client.is_connected()
            self.linksta = True
            # log.info("Connected: {0}".format(x))
            keyuu = '6e'
            for service in self.client.services:
                print(service.uuid)
                if keyuu not in service.uuid:
                    continue

                # log.info("[Service] {0}: {1}".format(service.uuid, service.description))

                for char in service.characteristics:
                    print(char.properties)
                    if 'notify' not in char.properties:
                        continue
                    else:
                        print(char.uuid)
                        self.noticeuuid = char.uuid
                        try:
                            value = bytes(await self.client.read_gatt_char(char.uuid))
                        except Exception as e:
                            value = str(e).encode()
                    
                    # log.info(
                    #     "\t[Characteristic] {0}: (Handle: {1}) ({2}) | Name: {3}, Value: {4} ".format(
                    #         char.uuid,
                    #         char.handle,
                    #         ",".join(char.properties),
                    #         char.description,
                    #         value,
                    #         ';lkj74'
                    #     )
                    # )

                    for descriptor in char.descriptors:
                        value = await self.client.read_gatt_descriptor(descriptor.handle)
                        # log.info(
                        #     "\t\t[Descriptor] {0}: (Handle: {1}) | Value: {2} ".format(
                        #         descriptor.uuid, descriptor.handle, bytes(value)
                        #     )
                        # )

                        # await asyncio.sleep(1)
                    #await self.client.stop_notify(CHARACTERISTIC_UUID)
            if(self.noticeuuid):
                await self.client.start_notify(self.noticeuuid,self.notification_handler)
                while(True):
                    await asyncio.sleep(0.001)

                
    def get_time_stamp(self):
        ct = time.time()
        local_time = time.localtime(ct)
        data_head = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
        data_secs = (ct - int(ct)) * 1000
        time_stamp = "%s.%03d" % (data_head, data_secs)
        print(time_stamp)
                



    def notification_handler(self,sender,data):
        # self.get_time_stamp()
        dataList=[]


        for x in data:
            tmp = ('{:02x}'.format(x))
            dataList.append(tmp)


        if(len(dataList) !=51 ):
            return

        
        dataList.append(dataList[0])
        del(dataList[0])
        
        self.Dhrdata = dataList[50]

        for i in range(25):
            #struct.unpack用于拼接解析 参数为'<H'为拼接成无符号short 但数据必须是bytes  用bytes.fromhex将数据转换成bytes，"".join用于生成字符串
            self.gs301ppg = struct.unpack('<H', bytes.fromhex("".join([str(x) for x in dataList[i*2:i*2+2]])))[0] 
            self.PPG.put(self.gs301ppg)
            self.ppgalgodata.append(self.gs301ppg)

         
            # if(len(self.normalizedorig) >=100):
            #     del(self.normalizedorig[0])
            #     self.normalizedorig.append(self.gs301ppg)
            # else:
            #     self.normalizedorig.append(self.gs301ppg)
                
            # self.PPG.put(self.normalized(self.gs301ppg,self.normalizedorig))
            # print(self.gs301ppg)


    #归一化    
    def normalized(self,currentdata,olddata):
        Min = np.min(olddata)
        Max = np.max(olddata)
        # Min = 0
        # Max = 66000
        currentdata = (currentdata - Min) / (Max - Min)
        # print(currentdata)
        return currentdata
        
    #归一化    
    def datanormalized(self,olddata):
        data = []
        Min = np.min(olddata)
        Max = np.max(olddata)

        for ind in range(len(olddata)):
            data.append((olddata[ind] - Min) / (Max - Min)) 

        return data

    #创建断开协程
    def BLE_dis_handle(self):
        if(self.linksta):
            self.timer_start(0.001,self.dis_handle)
            self.linksta = False

        
    #创建断开协程
    def dis_handle(self):
        self.disloop = asyncio.new_event_loop()
        self.disloop.run_until_complete(self.waitdis())
        self.disloop.close()
        
    #断开
    async def waitdis(self):
        #数据刷新停止
        self.timer.stop()
        self.BLE_dis_button.setEnabled(False)
        self.BLE_Scan_button.setEnabled(True)
        await self.client.disconnect() 

    def hex2dec(self,string_num):
        return str(int(string_num.upper(), 16))

    #BLE数据刷新
    def update_data(self):
  
        if self.PPG.empty() == 0:
            if self.savenum < self.savedatasize:
                self.data[self.savenum] = self.PPG.get()
                self.savenum+=1
            else:
                self.data[:-1] = self.data[1:]
                self.data[-1] = self.PPG.get()

            # 数据填充到绘制曲线中
            self.curve.setData(self.data)
            # x 轴记录点
            self.ptr1 += 1
            # 重新设定 x 相关的坐标原点
            self.curve.setPos(self.ptr1,0)

            srtr = ''.join(self.hex2dec(self.Dhrdata))
            self.plot_plt.setTitle("心率:" + srtr)

        # self.timer_start(0.04,self.update_data)

    #定时定量执行绘图算法
    def Count(self):
        if(self.DynamicSonTabLocation == DynamicSon.PPG):
            if(len(self.ppgalgodata) >= 250):
                # self.get_time_stamp()
                self.DynamicAlgoPPG(self.ppgalgodata,self.Dhrdata,self.ppgsampling)
                self.ppgalgodata.clear()
            self.timer_start(0.2,self.Count)
        # elif(self.DynamicSonTabLocation == DynamicSon.ECG):



    #通用线程定时器
    def timer_start(self,time,call):
        t = Timer(time,call)
        t.start()

    #警告框
    def messageDialog(self,txt):
        msg_box = QMessageBox(QMessageBox.Warning,'警告',txt)
        msg_box.exec_()


    #定义打开文件夹目录
    def openfile(self):
        if self.staticinput.text():
            fname = QFileDialog.getOpenFileName(self,'打开文件', '*.txt;*.xls')
            if fname[0]:
                data    = pd.read_csv(fname[0],usecols=[0])
                data1   = pd.read_csv(fname[0],usecols=[1])
                self.ppgdata.clear()
                self.hrdata.clear()
                for index in range(len(data)):
                    self.ppgdata.append(data.iat[index,0])

                for index in range(len(data1)):
                    self.hrdata.append(data1.iat[index,0])    

                self.datainfo.setText("数据个数:" +  format(len(self.ppgdata)) + format(" ") + format(len(self.ppgdata)/self.staticSampling) + format("s"))
                self.staticAlgoPPG(self.ppgdata,self.hrdata,self.staticSampling)
        else:
            self.messageDialog('请输入频率')
                
    #切片
    def DataSlice(self):
        
        if(len(self.ppgdata)):
            start, startstatus = QInputDialog.getText(self,'','数据开始点:')
            stop,  stopstatus = QInputDialog.getText(self,'','数据结束点:')
            if startstatus and stopstatus:
                self.staticAlgoPPG(self.ppgdata[int(start):int(stop)],self.hrdata[int(start):int(stop)],self.staticSampling)
        else:
            self.messageDialog('打开数据在切片')
      

                
               
    #切片恢复
    def DataSliceRestore(self):

        if(len(self.ppgdata)):
            self.staticAlgoPPG(self.ppgdata,self.hrdata,self.staticSampling)
        else:
            self.messageDialog('打开数据在切片')
 
            
    def checkNormalizedPos(self):
        choice_1 = self.checkNormalized.text()
        if(self.NormalizedFlag):
            self.NormalizedFlag = False
            print("False")
        else:
            self.NormalizedFlag = True
            print("True")



    # 鼠标拖入事件
    def dragEnterEvent(self, event):
        print(os.path.dirname((event.mimeData().urls())[0].toLocalFile()))






if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    gui = MainUi()
    gui.show()
    sys.exit(app.exec_())
 