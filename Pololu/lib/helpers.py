'''
This software is made available for use under the GNU General Public License (GPL).
A copy of this license is available within the repository for this software and is
included herein by reference.
'''

# Basic Imports

import os
import time
import binascii
import tables

def flush():
    tables.pushPWMs()

############# Servo Code #################################
def setServo(index=-1, cycletime=0, push=False):
    tables.setPWM(index, cycletime, push)

def releaseServo(index=-1):
    tables.releasePWM(index)

def releaseAllServos():
    tables.releaseAllPWMs()

def pushServos():
    tables.pushPWMs()

############# Digital Code #################################
def setDigital(index=-1, value=0, show=False):
    tables.setDigital(index, value, push=show)

def outputDigital():
    tables.outputDigital()

def setAllDigital(invalue):
    tables.setAllDigital(invalue)

def clearAllDigital():
    tables.clearAllDigital()

################ USB data transfer code ###############################################
import select
import sys

# Create object for communicating over USB
inpoll = select.poll()
inpoll.register(sys.stdin.buffer, select.POLLIN)

def isThereInput():
    result = inpoll.poll(0)
    return len(result) > 0

def handleInput():
    inline = sys.stdin.buffer.readline().decode('utf-8')
    if len(inline) > 6 and inline[0:6] == 'status':
        # Handle status request
        if inline[6] == 'b':
            # Wants block sizes
            blockSizes = tables.getBinarysizes()
            print(tables.PreferBinary)
            print(blockSizes[0], blockSizes[1], blockSizes[2], blockSizes[3])
    elif inline[0] == 'a':
        # Trigger one playback
        return 1
    elif inline[0] == 'x':
        # Wait 2 seconds for commlib to close connection
        time.sleep(2.000)
    elif inline[0] == 'd':
        # Set an individual digital port
        try:
            vals = inline.split()
            channel = int(vals[1]) # - MaxTotalServos # Move down
            value = int(vals[2])
            setDigital(channel, value, show=True)
        except:
            pass
    elif inline[0] == 's':
        # Set an individual servo
        try:
            vals = inline.split()
            channel = int(vals[1])
            value = int(vals[2])
            setServo(channel, value, push=True)
        except:
            pass
    return 0

################################### File Utilities ############################
def filecrc16(fname):
    # Computes and returns a 16-bit Cyclic Redundancy Checksum of the specified file
    PRESET = 0xFFFF
    POLYNOMIAL = 0xA001 # bit reverse of 0x8005

    try:
        crc = PRESET
        file = open(fname, 'rb')
        data = file.read(256)
        while len(data) > 0:
            for c in data:
                crc = crc ^ c
                for j in range(8):
                    if crc & 0x01:
                        crc = (crc >> 1) ^ POLYNOMIAL
                    else:
                        crc = crc >> 1
            data = file.read(256)
        file.close()
        return crc
    except:
        return -1


################################### Test Code ########################################

