import struct
import pyqtgraph as pg
import array
import serial
import threading
import numpy as np
from queue import Queue
import time


k = 0
i = 0
q = Queue(maxsize=0)
p = Queue(maxsize=0)

 
def bytesToFloat(h1,h2,h3,h4):
    ba = bytearray()
    ba.append(h1)
    ba.append(h2)
    ba.append(h3)
    ba.append(h4)
    return struct.unpack("!f",ba)[0]


def Serial():
    dat =[0,0,0,0,0,0,0,0]
    global i;
    global q;
    global p;
    while(True):
        n = mSerial.inWaiting()
        if(n):
            for n in range (8):
                dat[n] = int.from_bytes(mSerial.readline(1),byteorder='little')  # 格式转换
            #data = (dat[0]*256*256*256) + (dat[1]*256*256) + (dat[2]*256) + dat[3]
            data1 = bytesToFloat(dat[0],dat[1],dat[2],dat[3])
            data2 = bytesToFloat(dat[4],dat[5],dat[6],dat[7])
            #if(dat>>7):
                #dat =256-dat
                #dat =0-dat
            q.put(float(data1))
            p.put(float(data2))
            print("电机1",float(data1))
            print("电机2",float(data2))

def plotData():
    global i;
    if i < historyLength:
        data1[i] = q.get()
        i = i+1
    else:
        data1[:-1] = data1[1:]
        data1[i-1] = q.get()
    curve1.setData(data1)
    global k;
    if k < historyLength:
        data2[k] = p.get()
        k = k+1
    else:
        data2[:-1] = data2[1:]
        data2[k-1] = p.get()
    curve2.setData(data2)



if __name__ == "__main__":
    app = pg.mkQApp()  # 建立app
    win = pg.GraphicsWindow()  # 建立窗口
    win.setWindowTitle(u'波形图')
    win.resize(800, 600)  # 小窗口大小
    historyLength = 500 # 横坐标长度
  
    data1 = array.array('i')  # 可动态改变数组的大小,double型数组
    data1 = np.zeros(historyLength).__array__('d')#把数组长度定下来
    data2 = array.array('i')  # 可动态改变数组的大小,double型数组
    data2 = np.zeros(historyLength).__array__('d')#把数组长度定下来

    p1 = win.addPlot()  # 把图p加入到窗口中
    p1.showGrid(x=True, y=True)  # 把X和Y的表格打开
    p1.setRange(xRange=[0, historyLength], yRange=[0, 1], padding=0)
    p1.setLabel(axis='left', text='y / V')  # 靠左
    p1.setLabel(axis='bottom', text='x / point')
    p1.setTitle('1')  # 表格的名字

    curve1 = p1.plot(pen = 'y')  # 绘制一个图形
    curve1.setData(data1)
    curve2 = p1.plot(pen = 'r')  # 绘制一个图形
    curve2.setData(data2)

    portx = 'COM9'
    bps = 115200
    # 串口执行到这已经打开 再用open命令会报错
    mSerial = serial.Serial(portx, int(bps))
    if (mSerial.isOpen()):
        dat = 0xff;
        dat >> 2;
        print("open success")
        # 向端口些数据 字符串必须译码
        mSerial.write("hello".encode())
        mSerial.flushInput()  # 清空缓冲区
    else:
        print("open failed")
        serial.close()  # 关闭端口
    th1 = threading.Thread(target=Serial)
    th1.start()
    
    timer = pg.QtCore.QTimer()
    timer.timeout.connect(plotData)   # 定时刷新数据显示
    timer.start(1)  # 多少ms调用一次
    app.exec_()