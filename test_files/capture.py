import toupcam
import ctypes
import numpy as np
from PIL import Image
import time

def event_cb(n_event, ctx):
    pass

def capture():
    hcam = toupcam.Toupcam.Open(None)
    if not hcam:
        return

    w, h = hcam.get_Size()

    hcam.put_AutoExpoEnable(0)
    hcam.put_ExpoTime(10000)      
    hcam.put_ExpoAGain(100)      

    hcam.StartPullModeWithCallback(event_cb, None)
    hcam.Snap(0)
    time.sleep(0.3)

    buf = ctypes.create_string_buffer(w * h * 3)
    hcam.PullStillImageV2(buf, 24, None)

    arr = np.frombuffer(buf, dtype=np.uint8).reshape((h, w, 3))
    Image.fromarray(arr, mode='RGB').save('capture.png')

    hcam.Close()

capture()