# -*- coding: utf-8 -*-
import asyncio
from asyncio.tasks import sleep
from asyncio.windows_events import SelectorEventLoop
from pickle import TRUE
from bleak import BleakClient
from bleak import discover
import logging
import numpy as np
import struct
import array
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from scipy.spatial.transform import Rotation as R
import pyqtgraph as pg
from queue import Queue
from ctypes import *
from threading import Timer
from PyQt5 import QtWidgets,QtCore,QtGui
import sys
import numpy as np
import matplotlib.pyplot as plt
import heartpy as hp
import sys
import wfdb
import time
import signal

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FC
from PyQt5.QtWidgets import QApplication, QPushButton, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtWidgets import (QWidget, QApplication, QComboBox, QLabel, QPushButton, QHBoxLayout,
                             QVBoxLayout, QToolTip, QMessageBox)
from PyQt5.QtGui import QIntValidator,QDoubleValidator,QRegExpValidator
from matplotlib.patches import Ellipse, Circle
import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

sample_rate = 25
data = hp.get_data(r'C:\Users\LUOXF\Desktop\心率验证\data.txt')

class MainUi(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainUi,self).__init__()

        # 解决无法显示中文
        plt.rcParams['font.sans-serif'] = ['SimHei']
        # 解决无法显示负号
        plt.rcParams['axes.unicode_minus'] = False

        self.TabLocation = 0

        self.setWindowTitle("BleTool-PPG-ECG")
        self.mainwidget = QWidget() # 创建一个主部件
        self.mainwlayout = QtWidgets.QGridLayout() # 创建一个网格布局
        self.mainwidget.setLayout(self.mainwlayout) # 设置主部件的布局为网格
        self.tab = QTabWidget(self)
        self.tab.currentChanged.connect(self.tabchange)
        self.toolui()
        self.ppg_ui()
        self.ecg_ui()
        self.staticAnalysis()
        self.mainwlayout.addWidget(self.info, 1, 0, 1, 2)
        self.mainwlayout.addWidget(self.line, 2, 0, 1, 2)
        self.mainwlayout.addWidget(self.tab, 3, 0, 1, 2)
        self.setCentralWidget(self.mainwidget)


    def tabchange(self,tab):
        self.TabLocation = tab
        if(self.TabLocation == 0):
            self.plot_plt.setTitle("心率:",size='16pt',color='r')
        else:
            self.plot_plt.setTitle("",size='16pt',color='r')
        print(tab)


    def staticAnalysis(self):
        self.staticanalysisui_widget = QWidget() # 创建一个主部件
        self.tab.addTab(self.staticanalysisui_widget,'静态数据分析')


    def toolui(self):

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
        self.line = QtWidgets.QGroupBox("")
        self.linelayout = QtWidgets.QFormLayout()
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
        self.data1 = np.zeros(300).__array__('d') 
        self.curve2 = self.plot_plt.plot(self.data1, name="mode2",pen = 'g')
        self.ptr1 = 0

            # 设定定时器  连接时启动
        self.timer = pg.QtCore.QTimer()
            # 定时器信号绑定 update_data 函数
        self.timer.timeout.connect(self.update_data)

    def ppg_ui(self):
        
        #曲线数据
        self.PPG = Queue(maxsize=0)
        #ppg采样率
        self.ppgsampling =0
        #用于计算的原始数据
        self.ppgalgodata =[]

        self.normalizedorig =[]
        #归一化后数据
        self.normalizedData =[]


        self.ppgui_widget = QWidget() # 创建一个主部件
        self.tab.addTab(self.ppgui_widget,'PPG')
        self.ppg_layout = QtWidgets.QGridLayout() # 创建一个网格布局
        self.ppgui_widget.setLayout(self.ppg_layout) # 设置主部件的布局为网格


        #PPG
        self.graph = QtWidgets.QGroupBox("")
        self.graphlayout = QtWidgets.QFormLayout()
        self.fig = plt.Figure(figsize=(8,8),dpi=100)
        self.canvas = FC(self.fig)
        
        self.ax = self.fig.add_subplot(311)
        self.ax.set_title('PPG原始数据(t-1)',fontsize=13)
        # self.ax.set_xlabel('dot',fontsize=10)

        self.bx = self.fig.add_subplot(312)
        self.bx.set_title('带通滤波及心率估算(t-1)',fontsize=13)
        # self.ax.set_xlabel('Time(s)',fontsize=10)
      
        self.cx = self.fig.add_subplot(313)
        self.cx.set_title('呼吸频率(t-1)',fontsize=13)
        
            # 添加绘图部件到网格布局层
        self.graphlayout.addWidget(self.canvas) 
        self.graph.setLayout(self.graphlayout)


        #庞加莱图    
        self.graph1 = QtWidgets.QGroupBox("")
        self.Poincaregraphlayout = QtWidgets.QFormLayout()
        self.PoincareGraph = plt.Figure(figsize=(8,8),dpi=100)
        self.PoincareCanvas = FC(self.PoincareGraph)
    
        self.dx = self.PoincareGraph.add_subplot()
        self.dx.set_title('庞加莱HRV分析(心率变异性)',fontsize=13)
        

            # 添加绘图部件到网格布局层
        self.Poincaregraphlayout.addWidget(self.PoincareCanvas)
        self.graph1.setLayout(self.Poincaregraphlayout)



            #注册鼠标缩放
        self.fig.canvas.mpl_connect('scroll_event', self.call_back)
        self.PoincareGraph.canvas.mpl_connect('scroll_event', self.call_back1)

            #自动排列避免重叠
        self.fig.tight_layout() 
        self.PoincareGraph.tight_layout() 

        # 将上述部件添加到布局层中 件名，行，列，占用行数，占用列数，对齐方式
        # self.ppg_layout.addWidget(self.info, 1, 0, 1, 2)
        # self.ppg_layout.addWidget(self.line, 1, 0, 1, 2)
        self.ppg_layout.addWidget(self.graph,1, 0, 1, 1)
        self.ppg_layout.addWidget(self.graph1,1, 1, 1, 1)
     
        #
        # self.setCentralWidget(self.main_widget)
        

        
    def ecg_ui(self):
        self.ecgui_widget = QWidget() # 创建一个主部件
        self.ecg_layout = QtWidgets.QGridLayout() # 创建一个网格布局
        self.ecgui_widget.setLayout(self.ecg_layout) # 设置主部件的布局为网格
        self.tab.addTab(self.ecgui_widget,'ECG')

        
    #ppg算法
    def ppgalgo(self):
        #计算
        self.filtered_ppg = hp.filter_signal(self.ppgalgodata, 
                                        cutoff = [0.8, 2.5], 
                                        filtertype = 'bandpass',
                                        sample_rate = self.ppgsampling,
                                        order = 3,
                                        return_top = False)

        wd, m = hp.process(self.filtered_ppg, sample_rate=self.ppgsampling,
                        high_precision = True)

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

   
        self.ax.cla()
        self.bx.cla()
        #PPG 原始数据 刷新点       add_subplot 行 列 图中位置 
        self.ax = self.fig.add_subplot(311)
        self.ax.set_title('PPG原始数据(t-1)',fontsize=13)
        # self.ax.set_xlabel('dot')
        self.ax.plot(self.ppgalgodata,color="green")
        
          #PPG 带通滤波心率估算
        self.bx = self.fig.add_subplot(312)
        self.bx.set_title('带通滤波器后心率估算(t-1)',fontsize=13)
        # self.ax.set_xlabel('Time(t-1)')
        self.bx.plot(plotx, wd['hr'], color="dodgerblue", label='PPG滤波数据', zorder=-10)
        self.bx.scatter(np.asarray(peaklist)/fs, ybeat, color="red",label='BPM:%.2f' %(m['bpm']))
        self.bx.scatter(rejectedpeaks/fs, rejectedpeaks_y,color="fuchsia", label='废弃心峰')
        self.bx.legend(loc=4,fontsize=12,framealpha=0.5)


        self.cx.cla()
        self.cx = self.fig.add_subplot(313)
        # self.ax.set_xlabel('ms')''
        self.cx.set_title('呼吸信号(t-1)',fontsize=13)
        if "breathing_signal" in wd:
          self.cx.plot(wd['breathing_signal'], color="dodgerblue", label='呼吸率:%.2f 立方/秒' %(m['breathingrate'] ))
          self.cx.legend(loc=4,fontsize=12,framealpha=0.5)
       
        
 
        self.dx.cla()
        self.dx.set_title('庞加莱HRV分析(心率变异性)')
        if "poincare" in wd:
          #get values from dict
          self.x_plus = wd['poincare']['x_plus']
          self.x_minus = wd['poincare']['x_minus']
          self.sd1 = m['sd1']
          self.sd2 = m['sd2']

          #define figure
          # fig, bx = plt.subplots(subplot_kw={'aspect': 'equal'}, figsize=None)
          if(len(self.x_plus)>0):
            #plot scatter
            self.dx.scatter(self.x_plus, self.x_minus, color = "red",
                        alpha = 0.75, label = '最大峰值间隔')

            #plot identity line
            mins = np.min([self.x_plus, self.x_minus])
            maxs = np.max([self.x_plus, self.x_minus])
            identity_line = np.linspace(np.min(mins), np.max(maxs))

            self.dx.plot(identity_line, identity_line, color='black', alpha=0.5, label = '标识线')
            self.dx.plot(identity_line, identity_line, color='black',alpha=0.5,label = 'SDNN:%.2f ms' %(m['sdnn']))
            self.dx.plot(identity_line, identity_line, color='black',alpha=0.5,label = 'RMSSD:%.2f ms'%(m['rmssd']))        



            #rotate SD1, SD2 vectors 45 degrees counterclockwise
            sd1_xrot, sd1_yrot = self.rotate_vec(0, self.sd1, 45)
            sd2_xrot, sd2_yrot = self.rotate_vec(0, self.sd2, 45)

            #plot rotated SD1, SD2 lines
            self.dx.plot([np.mean(self.x_plus), np.mean(self.x_plus) + sd1_xrot],
                    [np.mean(self.x_minus), np.mean(self.x_minus) + sd1_yrot],
                    color = "blue", label = 'SD1:%.2f' %(m['sd1']))
            self.dx.plot([np.mean(self.x_plus), np.mean(self.x_plus) - sd2_xrot],
                    [np.mean(self.x_minus), np.mean(self.x_minus) + sd2_yrot],
                    color = "red", label =  'SD2:%.2f' %(m['sd2']))

            #plot ellipse
            xmn = np.mean(self.x_plus)
            ymn = np.mean(self.x_minus)
            el = Ellipse((xmn, ymn), width = self.sd2 * 2, height = self.sd1 * 2, angle = 45.0)
            self.dx.add_artist(el)
            el.set_edgecolor((0,0,0))
            el.fill = False

            self.dx.set_xlabel('RRi_n (ms)')
            self.dx.set_ylabel('RRi_n+1 (ms)')
            self.dx.legend(loc=4,fontsize=12,framealpha=0.5)

          


        for key in m.keys():
            print('%s: %f' %(key, m[key]))
          

        #自动排列避免重叠
        self.fig.tight_layout() 
        self.PoincareGraph.tight_layout() 
        
        self.fig.canvas.draw()  # 这里注意是画布重绘，self.figs.canvas
        self.fig.canvas.flush_events()  # 画布刷新self.figs.canvas

        self.PoincareGraph.canvas.draw()
        self.PoincareGraph.canvas.flush_events()



    def rotate_vec(self,x, y, angle):

        theta = np.radians(angle)

        cs = np.cos(theta)
        sn = np.sin(theta)

        x_rot = (x * cs) - (y * sn)
        y_rot = (x * sn) + (y * cs)

        return x_rot, y_rot

    #输入事件
    def inputsampling(self):
        self.ppgsampling = int(self.performanceLabel1.text())
        print(self.ppgsampling)
       

    #鼠标处理    
    def call_back(self,event):
        axtemp=event.inaxes
        x_min, x_max = axtemp.get_xlim()
        fanwei = (x_max - x_min) / 10
        if event.button == 'up':
            axtemp.set(xlim=(x_min + fanwei, x_max - fanwei))
            print('up')
        elif event.button == 'down':
            axtemp.set(xlim=(x_min - fanwei, x_max + fanwei))
            print('down')
        self.fig.canvas.draw_idle()  # 绘图动作实时反映在图像上

    def call_back1(self,event):
        axtemp=event.inaxes
        x_min, x_max = axtemp.get_xlim()
        fanwei = (x_max - x_min) / 10
        if event.button == 'up':
            axtemp.set(xlim=(x_min + fanwei, x_max - fanwei))
            print('up')
        elif event.button == 'down':
            axtemp.set(xlim=(x_min - fanwei, x_max + fanwei))
            print('down')
        self.PoincareGraph.canvas.draw_idle()  # 绘图动作实时反映在图像上

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
            self.timer.start(0.04)
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

            # while(True):
                await self.client.start_notify(self.noticeuuid,self.notification_handler)
     
                

                

 
 
    def get_time_stamp(self):
        ct = time.time()
        local_time = time.localtime(ct)
        data_head = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
        data_secs = (ct - int(ct)) * 1000
        time_stamp = "%s.%03d" % (data_head, data_secs)
        print(time_stamp)


    def notification_handler(self,sender,data):
        self.get_time_stamp()
        dataList=[]


        for x in data:
            tmp = ('{:02x}'.format(x))
            dataList.append(tmp)


        if(len(dataList) !=51 ):
            return

        
        dataList.append(dataList[0])
        del(dataList[0])
        
        self.hr = dataList[50]

        for i in range(25):
            #struct.unpack用于拼接解析 参数为'<H'为拼接成无符号short 但数据必须是bytes  用bytes.fromhex将数据转换成bytes，"".join用于生成字符串
            self.gs301ppg = struct.unpack('<H', bytes.fromhex("".join([str(x) for x in dataList[i*2:i*2+2]])))[0] 
            # self.PPG.put(self.gs301ppg)
            self.ppgalgodata.append(self.gs301ppg)
            if(len(self.normalizedorig) >=100):
                del(self.normalizedorig[0])
                self.normalizedorig.append(self.gs301ppg)
            else:
                self.normalizedorig.append(self.gs301ppg)
                
            self.PPG.put(self.normalized(self.gs301ppg,self.normalizedorig))
            # print(self.gs301ppg)


        
    def normalized(self,currentdata,olddata):
        # Min = np.min(olddata)
        # Max = np.max(olddata)
        Min = 0
        Max = 66000
        currentdata = (currentdata - Min) / (Max - Min)
        print(currentdata)
        return currentdata
        
    #创建断开协程
    def BLE_dis_handle(self):
        self.timer_start(0.001,self.dis_handle)

        
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
            
            self.data1[:-1] = self.data1[1:]
            self.data1[-1] = self.PPG.get()
            # 数据填充到绘制曲线中
            self.curve2.setData(self.data1)
            # x 轴记录点
            self.ptr1 += 1
            # 重新设定 x 相关的坐标原点
            self.curve2.setPos(self.ptr1,0)

            srtr = ''.join(self.hex2dec(self.hr))
            self.plot_plt.setTitle("心率:" + srtr)



    def Count(self):
        if(len(self.ppgalgodata) >= 250):
            self.ppgalgo()
            self.ppgalgodata.clear()
        self.timer_start(0.04,self.Count)
        # print("数据")
        # print(self.ppgalgodata)

    #通用线程定时器
    def timer_start(self,time,call):
        t = Timer(time,call)
        t.start()


    def messageDialog(self,txt):
        msg_box = QMessageBox(QMessageBox.Warning,'警告',txt)
        msg_box.exec_()





if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    gui = MainUi()
    gui.show()
    sys.exit(app.exec_())
 