'''
This software is made available for use under the GNU General Public License (GPL).
A copy of this license is available within the repository for this software and is
included herein by reference.
'''

import select
import sys

inpoll = select.poll()
inpoll.register(sys.stdin.buffer, select.POLLIN)

# This is a stub version of the Pico machine library
class Pin:
    IN = 1
    OUT = 2
    PULL_DOWN = 21
    PULL_UP = 22

    pinID = -1  # ID of last pin to be set

    def __init__(self, pinNum, inorout, pull=None):
    
        self.pinNumber = int(pinNum)
        self.inorout = inorout
        self.pull = pull
        self.state = False

    def toggle(self):
        self.state = not self.state
        print('Pin', self.pinNumber, 'State is now:', self.state)

    def off(self):
        self.state = False
        print('Pin', self.pinNumber, 'State is now:', self.state)

    def on(self):
        self.state = True
        print('Pin', self.pinNumber, 'State is now:', self.state)

    def value(self, value=None):
        if value is not None:
            print('Setting Pin ', self.pinNumber, 'to state of:', value)
            self.state = value
            return(self.state)
        else:
            # Check for keyboard input as to which pin is activated
            result = inpoll.poll(0)
            if len(result) > 0:
                line = input()
                if len(line) > 1:
                    Pin.pinID = int(line)
                else:
                    Pin.pinID = 0
            if self.pinNumber == Pin.pinID:
                print('Matches pinNumber:', self.pinNumber)
                return False
            else:
                return True

class PWM:
    def __init__(self, inPin):
        self._pin = inPin
        self._hz = 0
        self._duty = 0

    def freq(self, hz):
        if hz is not None:
            self._hz = hz
        return self._hz

    def duty_u16(self, duty):
        if duty is not None:
            self._duty = duty
        return self._duty

    def deinit(self):
        pass

class I2S:
    TX = 1
    MONO = 1
    STEREO = 2

    def __init__(self, in1, sck=1, sd=1, ws=1, mode=TX, bits=16,
        format=MONO, rate=44100, ibuf=512):
        pass

    def write(buffer):
        pass

class I2C:
    def __init__(self, id, *, scl, sda, freq=400000, timeout=50000):
        pass

    def writeto_mem(self, address, add2, data):
        pass

    def readfrom_mem(self, address, add2, count):
        return [0]*count

class UART:
    def __init__(self, id, baudrate=115200, tx=None, rx=None):
        pass
