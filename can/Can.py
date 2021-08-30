import struct
import pyqtgraph as pg
import array
import serial
import threading
import numpy as np
from queue import Queue
from ctypes import *
import datetime as dt
import time





k = 0
i = 0
Server = Queue(maxsize=0)
Client = Queue(maxsize=0)
Pos = Queue(maxsize=0)
vel = Queue(maxsize=0)


threads= []
ptr = 0
ptr1 = 0
ptr2 = 0
ptr3 = 0
temp = []
temp1 = []
data = []


def get_time_stamp():
    ct = time.time()
    local_time = time.localtime(ct)
    data_head = time.strftime("%H:%M:%S", local_time)
    data_secs = (ct - int(ct)) * 1000
    time_stamp = "%s.%03d" % (data_head, data_secs)
    #print(time_stamp)


class _VCI_INIT_CONFIG(Structure):
    _fields_ = [('AccCode', c_ulong),
                ('AccMask', c_ulong),
                ('Reserved', c_ulong),
                ('Filter', c_ubyte),
                ('Timing0', c_ubyte),
                ('Timing1', c_ubyte),
                ('Mode', c_ubyte)]

class _VCI_CAN_OBJ(Structure):
    _fields_ = [('ID', c_uint),
                ('TimeStamp', c_uint),
                ('TimeFlag', c_byte),
                ('SendType', c_byte),
                ('RemoteFlag', c_byte),
                ('ExternFlag', c_byte),
                ('DataLen', c_byte),
                ('Data', c_byte*8),
                ('Reserved', c_byte*3)]

class _RX_CAN_OBJ(Structure):
    _fields_ = [('ID', c_uint),
                ('TimeStamp', c_uint),
                ('TimeFlag', c_byte),
                ('SendType', c_byte),
                ('RemoteFlag', c_byte),
                ('ExternFlag', c_byte),
                ('DataLen', c_byte),
                ('Data', c_byte *8),
                ('Reserved', c_byte*3)]


RXDATA = [_RX_CAN_OBJ(),_RX_CAN_OBJ(),_RX_CAN_OBJ(),_RX_CAN_OBJ(),_RX_CAN_OBJ(),_RX_CAN_OBJ(),_RX_CAN_OBJ(),_RX_CAN_OBJ(),_RX_CAN_OBJ(),_RX_CAN_OBJ(),_RX_CAN_OBJ()]

# RXDATA[0].ID = 0x1
# RXDATA[1].ID = 0x2

# print(RXDATA[0].ID)
# print(RXDATA[1].ID)

vic = _VCI_INIT_CONFIG()
vic.AccCode = 0x00000000
vic.AccMask = 0xffffffff
vic.Filter =1
vic.Timing0 = 0x00
vic.Timing1 = 0x1c
vic.Mode = 0

vco = _VCI_CAN_OBJ()
vco.ID = 0x18ff3010
vco.SendType = 0
vco.RemoteFlag = 0
vco.ExternFlag = 1
vco.DataLen = 8
vco.Data = (5, 2, 3, 4, 5, 6, 7, 8)

MproFlag = 0
SproFlag = 0

Savedata =0
Savedata1 = 0

f =0
g=0
m=0
gg =  [] 
gg = np.random.normal()

rxlen = 0
countx = 0
def rxconte():
    global rxlen,countx,ptr,ptr1
    #print(ptr,ptr1)
    ptr=0
    ptr1=0


def plotData():
    global ptr,i,k,f,ptr1,ptr2,ptr3,g,countx
    while(True):
        if Client.empty() == 0:
            if i < historyLength:
                data1[i] = Client.get()
                i = i+1
            else:
                #剔除最早的1个数据
                data1[:-1] = data1[1:]
                #在尾巴加入1个最新数据
                data1[i-1] = Client.get()
            rxlen+1
            curve1.setData(data1)
            curve1.setPos(ptr,0)
            ptr  += 1
        
        if Server.empty() == 0:
            if k < historyLength:
                data2[k] = Server.get()
                k = k+1
            else:
                data2[:-1] = data2[1:]
                data2[k-1] = Server.get()
            countx+=1
            curve2.setData(data2)
            curve2.setPos(ptr1,0)
            ptr1 += 1

        if Pos.empty()  == 0:
            if f < historyLength:
                data4[f] = Pos.get()
                f = f+1
            else:
                data4[:-1] = data4[1:]
                data4[f-1] = Pos.get()
            curve4.setData(data4)
            curve4.setPos(ptr3,0)
            ptr3 += 1

        if vel.empty() == 0:
            if g < historyLength:
                data3[g] = vel.get()
                g = g+1
            else:
                data3[:-1] = data3[1:]
                data3[g-1] = vel.get()
            curve3.setData(data3)
            curve3.setPos(ptr2,0)
            ptr2 += 1
        time.sleep(0.001)

def get_sign32(vx):
    if not vx or vx < 0x80000000:
        return vx
    return vx - 0x100000000

def get_sign8(vx):
    if not vx or vx < 0x80:
        return vx
    return vx - 0x100

def get_sign16(vx):
    if not vx or vx < 0x8000:
        return vx
    return vx - 0x10000
    
initpos =0
ForceRx =0
saveap  =0

def DataRx():
    x=0
    global MproFlag,SproFlag,Savedata,Savedata1,initpos,ForceRx,saveap,rxlen,countx,RXDATA
    while(True):
        ucNum = canLib.VCI_GetReceiveNum(21,0,0)
        # print(ucNum)
        if( ucNum >0 & ucNum<=1):
            canLib.VCI_Receive(21, 0, 0, pointer(RXDATA[0]),1,-1)
            if(RXDATA[0].ID == 0x200):
                temp1 = bytearray(RXDATA[0].Data)
                Client.put((temp1[1]<<8 | temp1[0]) /20)
                if((temp1[1]<<8 | temp1[0]) /20 == 0):
                    print("GG")
            elif(RXDATA[0].ID == 0x181):
                temp1 = bytearray(RXDATA[0].Data)
                #temp = (temp1[1]<<8 | temp1[0]) /20
                #Server.put(temp)
                #if(initpos==0):
                #    initpos = abs(get_sign32(temp1[5] << 24  | temp1[4]<<16 | temp1[3]<<8 | temp1[2]) /10000 *0.5652)
                #temp = abs(get_sign32(temp1[5] << 24  | temp1[4]<<16 | temp1[3]<<8 | temp1[2]) /10000 *0.5652)  - initpos
                temp = abs(get_sign32(temp1[3] << 24  | temp1[2]<<16 | temp1[1]<<8 | temp1[0]) /10000 *0.5652)
                Pos.put(temp)
                #vel.put(get_sign8(((temp - saveap) / 0.005)))
                #saveap = temp
                vel.put(get_sign16(temp1[5] << 24  | temp1[4]<<16))



def mouseMoved(evt):
  mousePoint = p1.vb.mapSceneToView(evt[0])
  label.setText("<span style='font-size: 13pt; color:  Red'> y = %0.2f, <span style='color: white'> x = %0.2f</span>" % (mousePoint.y(),mousePoint.x()))



def gaussian(A, B, x):
  return A * np.exp(-(x/(2. * B))**2.)


if __name__ == "__main__":
    app = pg.mkQApp()  # 建立app
    win = pg.GraphicsWindow()  # 建立窗口
    win.setWindowTitle(u'波形图')
    win.resize(800, 600)  # 小窗口大小
    historyLength = 1500

    data1 = array.array('i')  # 可动态改变数组的大小,double型数组
    data1 = np.zeros(historyLength).__array__('d')#把数组长度定下来
    data2 = array.array('i')  # 可动态改变数组的大小,double型数组
    data2 = np.zeros(historyLength).__array__('d')#把数组长度定下来
    data3 = array.array('i')  # 可动态改变数组的大小,double型数组
    data3 = np.zeros(historyLength).__array__('d')#把数组长度定下来
    data4 = array.array('i')  # 可动态改变数组的大小,double型数组
    data4 = np.zeros(historyLength).__array__('d')#把数组长度定下来


    label = pg.LabelItem(justify = "left")
    win.addItem(label)
    labe2 = pg.LabelItem(justify = "center")
    win.addItem(labe2)
    labe3 = pg.LabelItem(justify = "right")
    win.addItem(labe3)


    p1 = win.addPlot(row=1,col=0)  # 把图p加入到窗口中
    p1.showGrid(x=True, y=True)  # 把X和Y的表格打开
    p1.setRange(yRange=[0, 50],padding=0)
    labelStyle = {'color': '#DC143C', 'font-size': '16pt'}
    p1.setLabel(axis='left',text='力矩KG',**labelStyle)  # 靠左
    # p1.setTitle('力矩',**labelStyle)  # 表格的名字
    curve1 = p1.plot(pen = 'r')  # 绘制一个图形
    # curve1.setData(data1)
    curve2 = p1.plot(pen = 'b')  # 绘制一个图形



    p2 = win.addPlot(row=2,col=0)  # 把图p加入到窗口中
    p2.showGrid(x=True, y=True)  # 把X和Y的表格打开
    p2.setRange(yRange=[-3, 3],padding=0)
    labelStyle = {'color': '#00FF00', 'font-size': '16pt'}
    p2.setLabel(axis='left',text='速度',**labelStyle)  # 靠左
    # p2.setTitle('速度',**labelStyle)  # 表格的名字
    curve3 = p2.plot(pen = 'g')  # 绘制一个图形
    curve3.setData(data3)


    p3 = win.addPlot(row=3,col=0)  # 把图p加入到窗口中
    p3.showGrid(x=True, y=True)  # 把X和Y的表格打开
    p3.setRange(yRange=[0, 50],padding=0)
    labelStyle = {'color': '#FFFF00', 'font-size': '16pt'}
    p3.setLabel(axis='left',text='位置',**labelStyle)  # 靠左
    # p3.setTitle('位置',**labelStyle)  # 表格的名字
    curve4 = p3.plot(pen = 'y')  # 绘制一个图形
    curve4.setData(data4)




    proxy = pg.SignalProxy(p1.scene().sigMouseMoved, rateLimit=60, slot=mouseMoved)


    rxdata=_RX_CAN_OBJ()

    canLib = windll.LoadLibrary(r'D:\CAN分析仪资料20200701\二次开发库文件\x64\ControlCAN.dll')

    print('打开设备: %d' % (canLib.VCI_OpenDevice(21, 0, 0)))
    print('设置波特率: %d' % (canLib.VCI_SetReference(21, 0, 0, 0, pointer(c_int(0x060007)))))
    print('初始化: %d' % (canLib.VCI_InitCAN(21, 0, 0, pointer(vic))))
    print('启动: %d' % (canLib.VCI_StartCAN(21, 0, 0)))
    print('清空缓冲区: %d' % (canLib.VCI_ClearBuffer(21, 0, 0)))


    # timer = pg.QtCore.QTimer()
    # timer.timeout.connect(plotData)   # 定时刷新数据显示
    # timer.start(1000)  # 多少ms调用一次

    # datapro = threading.Thread(target=DataRx)
    # datapro.start()

    threads.append(threading.Thread(target=DataRx))
    threads.append(threading.Thread(target=plotData))

    
    for t in threads:
        print(t)
        t.start()

  

    # gg = pg.QtCore.QTimer()
    # gg.timeout.connect(plotPos)   # 定时刷新数据显示
    # gg.start(1)  # 多少ms调用一次

    # count = pg.QtCore.QTimer()
    # count.timeout.connect(rxconte)   # 定时刷新数据显示
    # count.start(1000)  # 多少ms调用一次


    app.exec_()
    # print('接收: %d' % (canLib.VCI_Receive(3, 0, 0, pointer(rxdata),100,400)))
    


