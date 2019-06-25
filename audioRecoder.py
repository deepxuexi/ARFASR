#coding=utf-8
import time,sys,struct
from ctypes import *
from win32com.directsound import directsound
import pywintypes
import win32event
import threading
import requests
from io import BytesIO
class AudioRecord():
    def __init__(self,nchnl=1,sps=16000,bps=16,t=0.1):
        dsc = directsound.DirectSoundCaptureCreate(None, None)#创建设备对象
        cdesc = directsound.DSCBUFFERDESC()#创建DSCBUFFERDESC结构对象
        self.bSize=int(sps*nchnl*bps/8*t)
        cdesc.dwBufferBytes =self.bSize #缓存大小
        cdesc.lpwfxFormat = pywintypes.WAVEFORMATEX()#DirectSound数据块格式
        cdesc.lpwfxFormat.wFormatTag = pywintypes.WAVE_FORMAT_PCM
        cdesc.lpwfxFormat.nChannels = nchnl
        cdesc.lpwfxFormat.nSamplesPerSec = sps
        cdesc.lpwfxFormat.nAvgBytesPerSec = int(sps*nchnl*bps/8)
        cdesc.lpwfxFormat.nBlockAlign = int(nchnl*bps/8)
        cdesc.lpwfxFormat.wBitsPerSample = bps
        self.buffer = dsc.CreateCaptureBuffer(cdesc)#创建缓冲区对象
        self.evt=[]
        for i in range(2):
            self.evt.append(win32event.CreateEvent(None, 0, 0, None))#创建两个事件通知
        Notify=self.buffer.QueryInterface(directsound.IID_IDirectSoundNotify)#创建事件通知接口
        Notify.SetNotificationPositions([(int(self.bSize/2)-1,self.evt[0]),(self.bSize-1, self.evt[1])]) #error
        #设置两个通知位置，缓冲区每填充bSize/2个样本即发送一个通知消息
        self.data=b''#用于实时存储捕获的音频数据
        self.STATUS=False#录音状态标志
        self.wfx=cdesc.lpwfxFormat#存储声音格式
    def Record(self):
        self.data=b''  
        self.buffer.Start(directsound.DSCBSTART_LOOPING)#开始录音，动态缓冲模式
        self.STATUS=True#设置录音状态标志
        i=0
        n=int(self.bSize/2)
        while self.STATUS:
            win32event.WaitForSingleObject(self.evt[i],win32event.INFINITE)#win32event.INFINITE)#等待事件通知
            self.data += self.buffer.Update(i*n, n)
            #从缓冲区取音频数据,第1个参数为偏移量,第2个为数据大小。
            i=(i+1)%2
    def Stop(self):
        self.buffer.Stop()#停止录音
        self.STATUS=False#设置录音状态
        wav_head_16000=b'RIFF\xa4o\x1a\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x80o\x1a\x00'
        s1=struct.pack('I',len(self.data)+36)
        s2=struct.pack('I',len(self.data))
        self.data=wav_head_16000[:4]+s1+wav_head_16000[8:-4]+s2+self.data

def recog(buffer):
    start=time.time()
    server = "http://192.168.206.132:5000/recognize"
    buffile=BytesIO(buffer).getvalue()
    files = {"file": buffile}
    r = requests.post(server, files=files)
    print("")
    print("识别结果:")
    ret=r.text
    print(ret)
    print('耗时：',time.time()-start)
    return ret

while 1:
    press_key=input('press enter to start recording , or press q to exit :')
    if press_key=='':
        r=AudioRecord()
        print( 'start recording......')
        threading.Thread(target=r.Record).start() #开始录音
        input('press enter to stop record') #按任意键结束录音
        time.sleep(0.25)
        print( 'record stoped.',r.STATUS)
        r.STATUS=False
        r.Stop()
        print(len(r.data))
        ret=recog(r.data)
        with open('%s.wav'%ret,'wb') as fwav:
            fwav.write(r.data)
    elif press_key=='q':
        print( 'exit')
        sys.exit()
