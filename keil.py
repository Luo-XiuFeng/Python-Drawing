import sys
import os
import matplotlib.pyplot as plt

heat_data = []
HexTable = {'0':0,'1':1,'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'A':10,'B':11,'C':12,'D':13,'E':14,'F':15}
fin = open('shuju', 'r')
hex_dat = fin.read()
fin.close()

p_str = 0   
while p_str < len(hex_dat) :
    if hex_dat[p_str] == ':':
        p_str += 1
        linelen_H = HexTable[hex_dat[p_str]]
        p_str += 1
        linelen_L = HexTable[hex_dat[p_str]]
        linelen = linelen_H * 16 + linelen_L
        p_str += 4
        p_str += 2
        linetype = hex_dat[p_str - 1] + hex_dat[p_str]
        if linetype == '00' :
            for p_dat in range (linelen // 2) :
                p_str+= 4
                dat_tmp3 = hex_dat[p_str - 1]
                dat_tmp2 = hex_dat[p_str]
                dat_tmp1 = hex_dat[p_str - 3]
                dat_tmp0 = hex_dat[p_str - 2]
                dat_tmp = dat_tmp3 + dat_tmp2 + dat_tmp1 + dat_tmp0
                heat_data.append(dat_tmp)
    else :
        p_str += 1

		

heat_temp = []
heat_cnt = []
for i in range(len(heat_data)):
    heat_temp.append(int(heat_data[i],16))
    heat_cnt.append(i)

print ("数据点:",len(heat_cnt))
plt.plot(heat_cnt,heat_temp,c='g')
plt.xlim(0,1000)
plt.show()