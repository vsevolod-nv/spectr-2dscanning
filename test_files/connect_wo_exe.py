import ftd2xx as ft

devs = ft.listDevices()
print("FTDI Devices:", devs)

if devs:
    dev = ft.open(0)
    dev.setTimeouts(1000, 1000)
    
    dev.close()