#!/usr/bin/python

import time
import sys
import psutil
import socket
import fcntl
import struct
import uptime

from mates.controller import MatesController
from mates.constants import *

# When using the GPIO, ROCK SBC requires 'sudo'
def initResetPin(pin, mode: str):
    with open("/sys/class/gpio/export", "w") as f:
        f.write(str(pin))
    with open("/sys/class/gpio/gpio" + str(pin) + "/direction", "w") as m:
        m.write(str(mode))

# When using the GPIO, ROCK SBC requires 'sudo'
def setPin(pin, value):
    with open("/sys/class/gpio/gpio" + str(pin) + "/value", "w") as f:
        f.write(str(value))


# When resetting the module, ROCK SBC requires 'sudo'
def resetModule():
    initResetPin(75, "out")
    time.sleep(0.01)
    setPin(75, 0)
    time.sleep(0.01)
    setPin(75, 1)
    time.sleep(0.01)


def up():
    t = uptime.uptime()
    days = 0
    hours = 0
    min = 0
    out = ""

    while t > 86400:
        t -= 86400
        days += 1

    while t > 3600:
        t -= 3600
        hours += 1

    while t > 60:
        t -= 60
        min += 1

    out += str(days) + "d"
    out += str(hours) + "h"
    out += str(min) + "m"

    return out


def getTemp(sensor: str, multiplier: int = 1):
    temp = psutil.sensors_temperatures()[sensor][0]
    return round(temp.current * multiplier)


def get_interface_ipaddress(network):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        return socket.inet_ntoa(
            fcntl.ioctl(
                s.fileno(), 0x8915, struct.pack("256s", network[:15].encode("utf-8"))
            )[20:24]
        )
    except OSError:
        return "0.0.0.0"


if __name__ == "__main__":

    # When resetting the module, ROCK SBC requires 'sudo'
    # mates = MatesController('/dev/ttyS2', resetFunction=resetModule)
    mates = MatesController("/dev/ttyS2")

    mates.begin(115200)

    lastCpuUse = 0
    lastCpuTempG = 0
    lastCpuTempL = 0
    lastGpuTemp = 0
    lastRamUse = 0
    lastWIPaddr = 0
    lastEIPaddr = 0
    IPinterval = 0

    gtime = up()
    cpu_use = round(psutil.cpu_percent())               # CPU usage
    cpu_tempG = getTemp("cpu_thermal")                  # CPU temperature for gauge value
    cpu_tempL = getTemp("cpu_thermal", 10)              # CPU temperature for leddigits
    ram_use = round(psutil.virtual_memory().percent)    # RAM usage

    mates.updateTextArea(5, gtime, True)

    while True:

        cpu_tempG = getTemp("cpu_thermal")
        cpu_tempL = getTemp("cpu_thermal", 10)
        cpu_use = round(psutil.cpu_percent())
        ram_use = round(psutil.virtual_memory().percent)

        if cpu_use < lastCpuUse:
            lastCpuUse = lastCpuUse - (1 + (lastCpuUse - cpu_use > 9))
        if cpu_use > lastCpuUse:
            lastCpuUse = lastCpuUse + 1 + (cpu_use - lastCpuUse > 9)
        if cpu_tempL < lastCpuTempL:
            lastCpuTempL = lastCpuTempL - 1
        if cpu_tempL > lastCpuTempL:
            if (cpu_tempL - lastCpuTempL) > 10:
                lastCpuTempL = lastCpuTempL + 10
            else:
                lastCpuTempL = lastCpuTempL + 1

        if cpu_tempG < lastCpuTempG:
            lastCpuTempG = lastCpuTempG - (1 + (lastCpuTempG - cpu_tempG > 9))
        if cpu_tempG > lastCpuTempG:
            lastCpuTempG = lastCpuTempG + 1 + (cpu_tempG - lastCpuTempG > 9)
        if ram_use < lastRamUse:
            lastRamUse = lastRamUse - (1 + (lastRamUse - ram_use) > 9)
        if ram_use > lastRamUse:
            lastRamUse = lastRamUse + 1 + (ram_use - lastRamUse > 9)

        # CPU Temperature
        if cpu_tempG != lastCpuTempG:
            mates.setWidgetValueByIndex(
                MatesWidget.MATES_MEDIA_GAUGE_B, 0, lastCpuTempG
            )
        if cpu_tempL != lastCpuTempL:
            mates.setLedDigitsShortValue(0, lastCpuTempL)

        # Percentage of used CPU
        if cpu_use != lastCpuUse:
            mates.setWidgetValueByIndex(MatesWidget.MATES_MEDIA_GAUGE_B, 1, lastCpuUse)
            mates.setLedDigitsShortValue(1, lastCpuUse)

        # Percentage of used RAM
        if ram_use != lastRamUse:
            mates.setWidgetValueByIndex(MatesWidget.MATES_MEDIA_GAUGE_B, 2, lastRamUse)
            mates.setLedDigitsShortValue(2, lastRamUse)

        if IPinterval > 20:
            tempIPaddr = get_interface_ipaddress("eth0")
            if tempIPaddr != lastEIPaddr:
                mates.updateTextArea(1, tempIPaddr, True)
                lastEIPaddr = tempIPaddr

            tempIPaddr = get_interface_ipaddress("wlan0")
            if tempIPaddr != lastWIPaddr:
                mates.updateTextArea(3, tempIPaddr, True)
                lastWIPaddr = tempIPaddr

            IPinterval = 0

        IPinterval = IPinterval + 1
        time.sleep(0.060)

        tempTime = up()
        if tempTime != gtime:
            mates.updateTextArea(5, tempTime, True)
            gtime = tempTime
        time.sleep(0.04)
