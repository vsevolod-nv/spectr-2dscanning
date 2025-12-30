import time
import libximc.highlevel as ximc

device_uri = r"xi-com:\\.\COM10"
device_uri_2 = r"xi-com:\\.\COM11"
axis = ximc.Axis(device_uri)
axis_2 = ximc.Axis(device_uri_2)
axis.open_device()
axis_2.open_device()

print("Launch movement...")
axis.command_left()
axis_2.command_left()
time.sleep(3)

print("Stop movement")
axis_2.command_stop()
axis.command_stop()

axis.close_device()
axis_2.close_device()
print("Done")