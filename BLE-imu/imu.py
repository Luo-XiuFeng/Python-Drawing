# -*- coding: utf-8 -*-
import asyncio
from bleak import BleakClient
from bleak import discover
import logging
import numpy as np
import struct
import array
import pyqtgraph as pg
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
# from mcush import WitMotion, AppUtils
from scipy.spatial.transform import Rotation as R
import time
import pyqtgraph as pg
from queue import Queue
from ctypes import *
import datetime as dt
import serial
import threading
from threading import Timer
from PyQt5.QtGui import *
from PyQt5.QtCore import *

import multiprocessing
threads= []
WIDTH, HEIGHT = 600, 600

accUnitConvert = 0.001 * 9.81
gyroUnitConvert = 0.001 * np.pi/180

devices_dict = {}
devices_list = []

name = "IMU-Step"
address = 0

VIEW = [-1.0, 1.0, -1.0, 1.0, 1.0, 10.0]  
EYE  = [1.0, 1.0, 1.0]
AIM  = [0.0, 0.0, 0.0]
UP   = [0.0, 0.0, 1.0]
angle_x, angle_y, angle_z = 0, 0, 0

def draw():
    global angle_x, angle_y, angle_z
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glFrustum(VIEW[0], VIEW[1], VIEW[2], VIEW[3], VIEW[4], VIEW[5])
    gluLookAt( EYE[0], EYE[1], EYE[2], AIM[0], AIM[1], AIM[2], UP[0], UP[1], UP[2] )
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    glBegin(GL_LINES)

    # 画红色X轴
    glColor4f(1.0, 0.0, 0.0, 0.5)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(1.0, 0.0, 0.0)
    # 画绿色Y轴
    glColor4f(0.0, 1.0, 0.0, 0.5)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(0.0, 1.0, 0.0)
    # 画蓝色Z轴
    glColor4f(0.0, 0.0, 1.0, 0.5)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(0.0, 0.0, 1.0)
    glEnd()
    
    glRotatef(angle_x, 1,0,0 )
    glRotatef(angle_y, 0,1,0 )
    glRotatef(angle_z, 0,0,1 )
    glutWireTeapot(0.5)

    glutSwapBuffers()
    # glFlush()                            # 清空缓冲区，将指令送往硬件立即执行


def testlog():
    global angle_x, angle_y, angle_z
    angle_x= angle_x+1
    glutPostRedisplay()

def Ble_Link():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(scan())

def notification_handler(sender, data):
    global angle_x, angle_y, angle_z,Xaxis,dataupdate
    dataList=[]
    val = []
    for x in data:
        tmp = ('{:02x}'.format(x))
        dataList.append(tmp)

    if len(dataList) != 32:
        return


    accx = struct.unpack('<f', bytes.fromhex("".join([str(x) for x in dataList[0:4]])))[0] /1000
    accy = struct.unpack('<f', bytes.fromhex("".join([str(x) for x in dataList[4:8]])))[0] /1000
    accz = struct.unpack('<f', bytes.fromhex("".join([str(x) for x in dataList[8:12]])))[0] /1000

    Xaxis.put(accx)
    Yaxis.put(accy)
    Zaxis.put(accz)

    val.append(accx)
    val.append(accy)
    val.append(accz)
    val.append(1)
    print(val)

    

    angle_x, angle_y, angle_z = R.from_quat(val).as_euler('zxy',degrees=True)
    # print( angle_x, angle_y, angle_z )
    

    # draw()
    glutPostRedisplay()
    

    # if(giuflag):
    #     plotData()

    # gyrox = struct.unpack('<f', bytes.fromhex("".join([str(x) for x in dataList[12:16]])))[0] * gyroUnitConvert
    # gyroy = struct.unpack('<f', bytes.fromhex("".join([str(x) for x in dataList[16:20]])))[0] * gyroUnitConvert
    # gyroz = struct.unpack('<f', bytes.fromhex("".join([str(x) for x in dataList[20:24]])))[0] * gyroUnitConvert



async def run(debug=0):
    global address
    log = logging.getLogger(__name__)
    if debug:   
        import sys

        log.setLevel(logging.DEBUG)
        h = logging.StreamHandler(sys.stdout)
        h.setLevel(logging.DEBUG)
        log.addHandler(h)

    async with BleakClient(address) as client:
        x = await client.is_connected()
        log.info("Connected: {0}".format(x))

        keyuu = '6e'
        for service in client.services:

            if keyuu not in service.uuid:
                continue

            log.info("[Service] {0}: {1}".format(service.uuid, service.description))
            for char in service.characteristics:


                if 'notify' not in char.properties:
                    continue
                else:
                    CHARACTERISTIC_UUID = char.uuid
                    try:
                        value = bytes(await client.read_gatt_char(char.uuid))
                    except Exception as e:
                        value = str(e).encode()

                log.info(
                    "\t[Characteristic] {0}: (Handle: {1}) ({2}) | Name: {3}, Value: {4} ".format(
                        char.uuid,
                        char.handle,
                        ",".join(char.properties),
                        char.description,
                        value,
                        ';lkj74'
                    )
                )
                for descriptor in char.descriptors:
                    value = await client.read_gatt_descriptor(descriptor.handle)
                    log.info(
                        "\t\t[Descriptor] {0}: (Handle: {1}) | Value: {2} ".format(
                            descriptor.uuid, descriptor.handle, bytes(value)
                        )
                    )

              


                # await asyncio.sleep(1)
                #await client.stop_notify(CHARACTERISTIC_UUID)
        while(True):
            await client.start_notify(CHARACTERISTIC_UUID, notification_handler)


async def scan():
    global address
    dev = await discover()
    for i in range(0,len(dev)):
        if(dev[i].name == name):
            address = dev[i].address
            print("Address is " + address)




def test():
    global loop
    print("dsadsadsadsad")

    tasks1 = [
        run(),
    ]

    loop.run_until_complete(asyncio.wait(tasks1))

    timer_start(0.01,test)
    



def keydown(key, x, y):
    if key == b'q':  # 按q键退出程序并关闭串口监听任务
        glutLeaveMainLoop() 

Xaxis = Queue(maxsize=0)
Yaxis = Queue(maxsize=0)
Zaxis = Queue(maxsize=0)
ptr = 0
ptr1 =0
ptr2 =0
k = 0
i = 0
f = 0
historyLength = 1000
accx=0


curve1 = 0

dataupdate = 0
def plotData():
    global ptr,ptr1,i,k,f,ptr2,ptr,historyLength,accx,curve1,dataupdate,Yaxis
    
        
    # accx += 1 
    # Xaxis.put(accx)
    # if(accx==5):
    #     accx=0
    if Xaxis.empty() == 0:
        if i < historyLength:
            data1[i] = Xaxis.get()
            i = i+1
        else:
            #剔除最早的1个数据
            data1[:-1] = data1[1:]
            #在尾巴加入1个最新数据
            data1[i-1] = Xaxis.get()
        curve1.setData(data1)
        curve1.setPos(ptr,0)
        ptr  += 1


    if Yaxis.empty() == 0:
        if k < historyLength:
            data2[k] = Yaxis.get()
            k = k+1
        else:
            data2[:-1] = data2[1:]
            data2[k-1] = Yaxis.get()
        curve2.setData(data2)
        curve2.setPos(ptr1,0)
        ptr1 += 1

    if Zaxis.empty()  == 0:
        if f < historyLength:
            data3[f] = Zaxis.get()
            f = f+1
        else:
            data3[:-1] = data3[1:]
            data3[f-1] = Zaxis.get()
        curve3.setData(data3)
        curve3.setPos(ptr2,0)
        ptr2 += 1

loop = 0

def task():
    print("helo")
    t = Timer(1, task)
    t.start()

def task1():
    print("121")
    t = Timer(1, task1)
    t.start()



def timer_start(time,call):
    t = Timer(time,call)
    t.start()



    



def Gui3d():
    glutInit()                           
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_ALPHA)
    glutInitWindowSize(WIDTH, HEIGHT)
    glutCreateWindow('OpenGL')           
    glutDisplayFunc(draw)               
    # glutIdleFunc(test)
    
    glutKeyboardFunc(keydown)
    timer_start(0.001,test)
    glutMainLoop()                       


threads= []


if __name__ == '__main__':
    
    Ble_Link()
    loop = asyncio.get_event_loop()

    timer_start(0.001,Gui3d)

    app = pg.mkQApp()                              # 建立app
    win = pg.GraphicsWindow()                      # 建立窗口
    win.setWindowTitle(u'波形图')
    win.resize(800, 600)                           # 小窗口大小

    data1 = array.array('i')                       # 可动态改变数组的大小,double型数组
    data1 = np.zeros(historyLength).__array__('d') #把数组长度定下来
    data2 = array.array('i')                       # 可动态改变数组的大小,double型数组
    data2 = np.zeros(historyLength).__array__('d') #把数组长度定下来
    data3 = array.array('i')  # 可动态改变数组的大小,double型数组
    data3 = np.zeros(historyLength).__array__('d')#把数组长度定下来


    label = pg.LabelItem(justify = "left")
    win.addItem(label)


    p1 = win.addPlot(row=1,col=0)                     # 把图p加入到窗口中
    p1.showGrid(x=True, y=True)                       # 把X和Y的表格打开
    p1.setRange(yRange=[-5, 5],padding=0)
    labelStyle = {'color': '#DC143C', 'font-size': '16pt'}
    p1.setLabel(axis='left',text='XYZ',**labelStyle)  # 靠左
    # p1.setTitle('力矩',**labelStyle)  # 表格的名字
    curve1 = p1.plot(pen = 'r')                       # 绘制一个图形
    # curve1.setData(data1)
    curve2 = p1.plot(pen = 'b')                       # 绘制一个图形
    curve3 = p1.plot(pen = 'y')                       # 绘制一个图形



    timer = QTimer() #初始化一个定时器
    timer.timeout.connect(plotData) #计时结束调用operate()方法
    timer.start(0.001) #设置计时间隔并启动


    # # 设定定时器
    # timer = QTimer()
    # # 定时器信号绑定 update_data 函数
    # timer.timeout.connect(plotData)
    # # 定时器间隔50ms，可以理解为 50ms 刷新一次数据
    # timer.start(0.001)


    app.exec_()

    


    
    






