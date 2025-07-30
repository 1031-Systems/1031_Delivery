#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#**********************************
# Program tables.py
# Created by john
# Created Wed Jun 19 10:57:40 AM PDT 2024
#*********************************/
'''
This software is made available for use under the GNU General Public License (GPL).
A copy of this license is available within the repository for this software and is
included herein by reference.
'''

#/* Import block */
import os
import gc
import sys
import servo
import pca9685
import maestro
import time
import struct
from machine import Pin, I2C, PWM

#/* Define block */
verbosity = False
PreferBinary = False

class TableServos(servo.Servos):
    """
        The TableServos class extends the Servos based on their use in this table
    structure.  Of primary importance is the range of bytes in a binary block that
    correspond to the on/off values for the associated pca9685 board.
    """
    def __init__(self, i2c, address=0x40, firstport=0, numports=16):
        servo.Servos.__init__(self, i2c, address)

        self.firstport = firstport
        self.numbytes = numports * 4

    def jambytes(self, thebytes, start=-1):
        if start < 0:
            start = self.firstport
        if self.pca9685 is not None:
            self.pca9685.jambytes(thebytes, start)

    def address(self):
        if self.pca9685 is not None:
            return self.pca9685.address
        else:
            return None

class TableMaestros():
    '''
        The TableMaestros class copies the structure and methods of TableServos
    so they can be interchanged for binary mode operation.  One of these is created
    by each call to configureMaestroPWM and corresponds to a contiguous block of
    channels on a Maestro that controls servos.
    '''
    def __init__(self, address=0x0c, firstport=0, numports=6):
        self.firstport = firstport
        self.numbytes = numports * 2
        self.address = address

    def jambytes(self, thebytes, start=0):
        '''
            The jambytes method takes a block of bytes representing PWM values and
        streams them out to a Maestro board.

        What's the format?
            Could be 6 bytes containing entire command.
            Could be 4 bytes containing command, channel, and value
            Could be 2 bytes containing just value
            Assume just 2 for now
        '''
        makePControl()
        if pControl is not None:
            pControl.setBoard(self.address)
            cmds = []
            for indx in range(0,len(thebytes),2):
                cmds.append(chr(0x04) + chr(start) + chr(int.from_bytes(thebytes[indx+1])) + chr(int.from_bytes(thebytes[indx])))
                start += 1
            pControl.sendCmds(cmds)

    def address(self):
        return self.address


# Servo/PWM functions

# PWM Definitions
_i2c = None
_PWMBoards = {}         # Dictionary of Servos objects, one for each pca9685 board
_PWMGPIOs = {}          # Dictionary of GPIO pins set up for direct PWM control

# Maestro definitions
pControl = None

def dogpio(porttableentry, value, push=False):
    # Handle a PWM signal via a Pico GPIO pin
    if verbosity: print('Doing dogpio with porttableentry:', porttableentry, 'and value:', value)
    if 'pin' not in porttableentry:
        if verbosity: print('Whoops - Wrong port table entry for dogpio')
        return False

    shift = porttableentry['shift']
    pin = porttableentry['pin']
    if pin not in _PWMGPIOs:
        _PWMGPIOs[pin] = PWM(Pin(pin, Pin.OUT))

    value = value>>shift    # Normally should be a shift of 0 for GPIO pins
    _PWMGPIOs[pin].freq(50)
    _PWMGPIOs[pin].duty_u16(value)

def dosomething(port, valuebytes):
    # Accept any set PWM but only process GPIO ones, if any
    try:
        porttableentry = PWMPortTable[port]
        if porttableentry['func'] == dogpio:
            value = int.from_bytes(valuebytes, 'little')
            porttableentry['func'](porttableentry, value)
    except:
        pass

tickcounter = 0
def dopca9685(porttableentry, value, push=False):
    # Handle a PWM signal via I2C and an external pca9685 board
    global _i2c
    global _PWMBoards
    global tickcounter

    if verbosity: print('Doing dopca9685 with port:', porttableentry)
    if True: #try:
        ticks = time.ticks_us()
        board = porttableentry['board']
        pwmout = porttableentry['pwmout']
        shift = porttableentry['shift']
        #print('Ticks to look up board, pwmout, and shift in dict:', time.ticks_diff(time.ticks_us(), ticks))
        if board not in _PWMBoards:
            ticks = time.ticks_us()
            if verbosity: print('Whoops - PWMBoard id:', board, 'not in initialized list:', _PWMBoards)
            if _i2c is None:
                sda = Pin(0, Pin.OUT, pull=Pin.PULL_UP)
                scl = Pin(1, Pin.OUT, pull=Pin.PULL_UP)
                id = 0
                _i2c = I2C(id=id, sda=sda, scl=scl, freq=1048576)   # Use 1MHz as that is max for pca9685
            _PWMBoards[board] = servo.TableServos(i2c=_i2c, address=0x40+board)
            #print('Ticks to nstantiate board if needed:', time.ticks_diff(time.ticks_us(), ticks))

        # Normally should be a shift of 4 for pca9685
        if verbosity: print('Pushing value:', value, 'to pwm board:',board,'port:',pwmout,'push:',push)
        ticks = time.ticks_us()
        # Normally should be a shift of 4 for pca9685
        #_PWMBoards[board].position(pwmout, duty=value>>shift, push=push)
        _PWMBoards[board].duty(pwmout, value>>shift)
        #print('Ticks to set servo value:', time.ticks_diff(time.ticks_us(), ticks))
        tickcounter += time.ticks_diff(time.ticks_us(), ticks)
    else: #except:
        if verbosity: print('Whoops - Wrong port table entry for dopca9685')
        return False

def setPWM(port, value, push=False):
    # Handle a PWM signal to the specified port via the configured method
    #if port in PWMPortTable and 'func' in PWMPortTable[port]:
    try:
        PWMPortTable[port]['func'](PWMPortTable[port], value, push)
    except:
        pass

def intToPWM(value):
    port = 0
    while port <= max(PWMPortTable):
        pwmvalue = value & 0xFFFF
        setPWM(port, pwmvalue)
        value >>= 16
        port += 1

import gc
def intsToPWM(values):
    #gc.collect()
    global tickcounter
    tickcounter = 0
    for port in range(len(values)):
        setPWM(port, values[port])
    #print('Ticks to set 9685 PWMs:', tickcounter, 'usec')

def getPWMstructformat():
    format = '<'
    for port in range(max(PWMPortTable)+1):
        format += 'H'
    return format

def getBinarysizes():
    # Returns the number of bytes that a single record should hold
    # 4 for integer time in milliseconds
    # 1 for each block of 8 digital bit ports from 0 to max
    # 4 bytes (2 bytes onval and 2 bytes offval) for each PWM port from 0 to max
    if len(PWMPortTable) > 0:
        numPWMs = max(PWMPortTable)+1
    else:
        numPWMs = 0
    if len(DigitalPortTable) > 0:
        numDigs = max(DigitalPortTable)+1
    else:
        numDigs = 0
    numBytes = (numDigs + 7) >> 3
    return(4 + numBytes + numPWMs*4, 4, numBytes, numPWMs*4)

def getHexsize():
    # Returns the number of hex digits that a single record should hold
    # 8 for integer time in milliseconds
    # 16 for up to 64 digital bits
    # 4 bytes for each PWM port from 0 to max
    numPWMs = max(PWMPortTable)+1
    return(8 + 16 + numPWMs*4)

def releasePWM(port):
    # Release tension on a PWM
    setPWM(port, 0)

def releaseAllPWMs():
    # Release any PWMs on pca boards
    for board in _PWMBoards:
        _PWMBoards[board].releaseAll()
    # Release any PWMs on GPIO pins
    for pin in _PWMGPIOs:
        _PWMGPIOs[pin].duty_u16(0)

def pushPWMs():
    # Push any PWMvalues to pca boards
    for board in _PWMBoards:
        _PWMBoards[board].pushValues()
    # Now push any saved values to Maestro boards
    makePControl()
    if pControl:
        pControl.sendCmds()
    # Don't need to push to GPIO pins??

def configurepca9685(firstport=0, boardid=0):
    # Configure a single external pca9685 board
    global PWMPortTable
    global _i2c
    global _PWMBoards

    # Generate 16 PWM entries per pca9685 board
    for i in range(16):
        PWMPortTable[firstport+i] = {'func':dopca9685, 'board':boardid, 'pwmout':i, 'shift':4}

    # Explicitly create the TableServos object and put in list
    if boardid not in _PWMBoards:
        if verbosity: print('Whoops - PWMBoard id:', boardid, 'not in initialized list:', _PWMBoards)
        if _i2c is None:
            sda = Pin(0, Pin.OUT, pull=Pin.PULL_UP)
            scl = Pin(1, Pin.OUT, pull=Pin.PULL_UP)
            id = 0
            _i2c = I2C(id=id, sda=sda, scl=scl, freq=1048576)   # Use 1MHz as that is max for pca9685
        _PWMBoards[boardid] = TableServos(i2c=_i2c, address=0x40+boardid, firstport=firstport)


    global _ExpectedPWMPorts
    _ExpectedPWMPorts += 16

def domaestroPWM(porttableentry, value, push=False):
    # Handle a PWM signal via Maestro board
    makePControl()

    if verbosity: print('Doing domaestroPWM with port:', porttableentry)
    try:
        board = porttableentry['board']
        pwmout = porttableentry['pwmout']
        mult = porttableentry['multiplier']

        # Normally should be a multiply of 1.22 for Maestros
        if verbosity: print('Pushing value:', value, 'to pwm board:',board,'port:',pwmout,'multiplier:',mult)
        value = int(value * mult)
        if pControl is not None:
            pControl.setBoard(board)
            pControl.setTarget(pwmout, value)
            if push: pControl.sendCmds()
    except:
        if verbosity: print('Whoops - Wrong port table entry for domaestroPWM')
        return False

def makePControl(TxPin=None):
    global pControl
    if pControl is None:
        if TxPin is None:
            pControl = maestro.Controller()
        else:
            pControl = maestro.Controller(TxPin=TxPin)

def configureMaestroUART(TxPin=None):
    if TxPin is not None:
        makePControl(TxPin=TxPin)

def configureMaestroPWM(firstport=0, boardid=0, count=1, firstchannel=0):
    global PWMPortTable

    # Generate count PWM entries for this Maestro board
    for i in range(count):
        PWMPortTable[firstport+i] = {'func':domaestroPWM, 'board':boardid, 'pwmout':i+firstchannel, 'multiplier':1.2207}

    global _ExpectedPWMPorts
    _ExpectedPWMPorts += count


def boardList():
    theList = []
    for boardid in _PWMBoards:
        theList.append(_PWMBoards[boardid])
    return theList

def pwmList():
    theList = []
    for port in PWMPortTable:
        if PWMPortTable[port]['func'] == dogpio:
            theList.append(port)
    return theList

def addPWMPortTableEntry(port, entry):
    global PWMPortTable
    global _ExpectedPWMPorts

    if 'shift' not in entry:
        entry['shift'] = 0

    PWMPortTable[port] = entry
    _ExpectedPWMPorts += 1

########################################################
# PWM Port Definitions
PWMPortTable = { }

# Field used for consistency checking
_ExpectedPWMPorts = 0

##############################################################################################
# Digital IO Functions

def doMaestroDigital(porttableentry, value, push=False):
    # Handle a Digital signal via Maestro board
    makePControl()

    if verbosity: print('Doing doMaestroDigital with port:', porttableentry)
    try:
        board = porttableentry['board']
        pwmout = porttableentry['pwmout']

        if verbosity: print('Pushing value:', value, 'to pwm board:',board,'port:',pwmout)
        value = int(value * 7000)
        if pControl is not None:
            pControl.setBoard(board)
            pControl.setTarget(pwmout, value)
            if push: pControl.sendCmds()
    except:
        if verbosity: print('Whoops - Wrong port table entry for domaestroPWM')
        return False

def configureMaestroDigital(boardid=12, firstport=0, firstchannel=0, count=1):
    # Configure a block of count ports supported by a Maestro
    global DigitalPortTable

    # Populate the port table
    for indx in range(count):
        DigitalPortTable[indx+firstport] = { 'func':doMaestroDigital, 'board':boardid, 'pwmout':indx+firstchannel }

    global _ExpectedDigitalPorts
    _ExpectedDigitalPorts += count



# Digital Definitions
_DigitalGPIOs = {}          # Dictionary of GPIO pins set up for Digital control
_digitalCurrentState = None # Array of values prior to being shifted out to 595s
_DataPin = None
_ClockPin = None
_RclkPin = None
_ClearPin = None

def configure595s(firstport=0, portcount=24, datapin=26, clockpin=27, rclkpin=21, clearpin=20):
    # Configure a block of portcount ports supported by 595s at 8 ports per board
    global _digitalCurrentState
    global _DataPin
    global _ClockPin
    global _RclkPin
    global _ClearPin
    global DigitalPortTable

    # Set up buffer for values prior to shifting them out to the 595s
    _digitalCurrentState = [0]*portcount

    # Save the pin specs
    _DataPin = datapin
    _ClockPin = clockpin
    _RclkPin = rclkpin
    _ClearPin = clearpin

    # Populate the port table
    for indx in range(portcount):
        DigitalPortTable[indx+firstport] = { 'func':do595, 'index':indx }

    global _ExpectedDigitalPorts
    _ExpectedDigitalPorts += portcount

def addDigitalPortTableEntry(port, entry):
    global DigitalPortTable
    global _ExpectedDigitalPorts

    DigitalPortTable[port] = entry
    _ExpectedDigitalPorts += 1

def output595s():
    if _DataPin is None or _RclkPin is None or _ClockPin is None or _ClearPin is None: return
    # Define the pins
    dataPin = Pin(_DataPin, Pin.OUT)
    clockPin = Pin(_RclkPin, Pin.OUT)
    shiftPin = Pin(_ClockPin, Pin.OUT)
    clearPin = Pin(_ClearPin, Pin.OUT)
    clearPin.on() # No want clearing here

    # Cycle the digital state thru all the 74HC595 chips
    for i in range(len(_digitalCurrentState)):
        # Put the value on the data pin, msb first
        value = _digitalCurrentState[len(_digitalCurrentState) - i - 1]
        dataPin.value(value)
        shiftPin.on()
        shiftPin.off()

    # Clock all the bits to the outputs
    clockPin.on()
    clockPin.off()

def fast595s(bytes, count):
    if _DataPin is None or _RclkPin is None or _ClockPin is None or _ClearPin is None: return
    # Define the pins
    dataPin = Pin(_DataPin, Pin.OUT)
    clockPin = Pin(_RclkPin, Pin.OUT)
    shiftPin = Pin(_ClockPin, Pin.OUT)
    clearPin = Pin(_ClearPin, Pin.OUT)
    clearPin.on() # No want clearing here

    valuebits = int.from_bytes(bytes, 'little')

    # Cycle the digital state thru all the 74HC595 chips
    for i in range(count):
        # Put the value on the data pin, msb first (input value LSB is 595 MSB)
        dataPin.value(valuebits & 1)
        shiftPin.on()
        shiftPin.off()
        valuebits >>= 1

    # Clock all the bits to the outputs
    clockPin.on()
    clockPin.off()


def do595(porttableentry, value):
    if verbosity: print('Doing do595 with porttableentry:', porttableentry)
    if 'index' not in porttableentry:
        if verbosity: print('Whoops - Wrong port table entry for do595')
        return False
    index = porttableentry['index']
    _digitalCurrentState[index] = value

def dogpiodigital(porttableentry, value):
    if verbosity: print('Doing dogpiodigital with porttableentry:', porttableentry)
    if 'pin' not in porttableentry:
        if verbosity: print('Whoops - Wrong port table entry for dogpiodigital')
        return False
    pin = porttableentry['pin']
    pin = Pin(pin, Pin.OUT)
    if value > 0.5:
        pin.on()
    else:
        pin.off()

def setDigital(port, value, push=False):
    if port in DigitalPortTable and 'func' in DigitalPortTable[port]:
        DigitalPortTable[port]['func'](DigitalPortTable[port], value)
    if push: outputDigital()

def clearAllDigital():
    # Set all digital pins to OFF (0)
    # Using clear pin for speed
    if _DataPin is None or _RclkPin is None or _ClockPin is None or _ClearPin is None: return
    # Define the pins
    dataPin = Pin(_DataPin, Pin.OUT)
    clockPin = Pin(_RclkPin, Pin.OUT)
    shiftPin = Pin(_ClockPin, Pin.OUT)
    clearPin = Pin(_ClearPin, Pin.OUT)

    # Clear all the registers
    clearPin.on() # Make sure initially not clearing, then cycle bit
    clearPin.off()
    clearPin.on()

    # Clock all the cleared bits to the outputs
    clockPin.off() # Make sure initially not outputting, then cycle bit
    clockPin.on()
    clockPin.off()

    # This quickly clears the 595 digital outputs but not GPIO digital outputs
    # So do the whole thing again to make sure everything is zero
    setAllDigital(0)

def setAllDigital(value):
    for port in DigitalPortTable:
        setDigital(port, value)
    outputDigital()

def outputDigital():
    output595s()
    pushPWMs()      # Flushes out all the commands to the Maestros
    # Don't need to output GPIOs

def intToDigital(bits):
    """
    intToDigital accepts a single integer of any length and extracts the digital
    bit values from it and sets things appropriately.  The assumption is that the
    LSB of the int corresponds to port 0, the next to port 1, ...  If a port is
    unassigned, that bit is skipped.
    """
    for port in range(max(DigitalPortTable) + 1):
        if port in DigitalPortTable and 'func' in DigitalPortTable[port]:
            DigitalPortTable[port]['func'](DigitalPortTable[port], bits & 1)
        bits >>= 1

########################################################

# Digital Port Definitions
DigitalPortTable = { }

# Field used for consistency checking
_ExpectedDigitalPorts = 0

########################################################

# Digital Input Functions
def configureMaestroTriggerInput(boardid=None, firstchannel=None):
    global _ExpectedDigitalinputPorts
    global TriggerInputPort
    if boardid is not None and firstchannel is not None:
        TriggerInputPort = {'boardid':boardid, 'firstchannel':firstchannel, 'func':getMaestroTriggerInput}
        _ExpectedDigitalinputPorts += 1

def configureMaestroRunInput(boardid=None, firstchannel=None):
    global _ExpectedDigitalinputPorts
    global RunInputPort
    if boardid is not None and firstchannel is not None:
        RunInputPort = {'boardid':boardid, 'firstchannel':firstchannel, 'func':getMaestroRunInput}
        _ExpectedDigitalinputPorts += 1

def configureMaestroOptoInput(boardid=None, firstchannel=None):
    global _ExpectedDigitalinputPorts
    global OptoInputPort
    if boardid is not None and firstchannel is not None:
        OptoInputPort = {'boardid':boardid, 'firstchannel':firstchannel, 'func':getMaestroOptoInput}
        _ExpectedDigitalinputPorts += 1

def configureMaestroDigitalInputs(boardid=None, firstchannel=None, firstindex=None, count=0):
    global _ExpectedDigitalinputPorts
    global DigitalInputPortTable
    if boardid is not None and firstchannel is not None and firstindex is not None:
        for indx in range(count):
            DigitalInputPortTable[firstindex+indx] = {'boardid':boardid, 'channel':firstchannel+indx, 'func':getMaestroInput}
        _ExpectedDigitalinputPorts += count

def getMaestroInput(InputPort=None):
    if InputPort is None:
        return False
    makePControl()
    pControl.setBoard(InputPort['boardid'])
    return pControl.getPosition(InputPort['channel']) < 512

def getMaestroRunInput(RunInputPort=None):
    if RunInputPort is None:
        return False
    makePControl()
    pControl.setBoard(RunInputPort['boardid'])
    return pControl.getPosition(RunInputPort['firstchannel']) < 512

def getMaestroTriggerInput(TriggerInputPort=None):
    if TriggerInputPort is None:
        return False
    makePControl()
    pControl.setBoard(TriggerInputPort['boardid'])
    return pControl.getPosition(TriggerInputPort['firstchannel']) < 512

def getMaestroOptoInput(OptoInputPort=None):
    if OptoInputPort is None:
        return False
    makePControl()
    pControl.setBoard(OptoInputPort['boardid'])
    return pControl.getPosition(OptoInputPort['firstchannel']) < 512


# Generic Input functions
def getRunInput():
    if RunInputPort is None or 'func' not in RunInputPort:
        return None
    return RunInputPort['func'](RunInputPort)

def getTriggerInput():
    if TriggerInputPort is None or 'func' not in TriggerInputPort:
        return None
    return TriggerInputPort['func'](TriggerInputPort)

def getOptoInput():
    if OptoInputPort is None or 'func' not in OptoInputPort:
        return None
    return OptoInputPort['func'](OptoInputPort)

def getInputs():
    # Returns a list of all port numbers that are currently triggered
    if len(DigitalInputPortTable) == 0:
        return None
    inputs = []
    for port in DigitalInputPortTable:
        InputPort = DigitalInputPortTable[port]
        if 'func' in InputPort:
            if InputPort['func'](InputPort):
                inputs.append(port)
    return inputs

def getInput(portid):
    if portid in DigitalInputPortTable:
        InputPort = DigitalInputPortTable[portid]
        if 'func' in InputPort:
            return InputPort['func'](InputPort)

########################################################

# Digital Input Definitions
DigitalInputPortTable = { }
RunInputPort = None
TriggerInputPort = None
OptoInputPort = None

# Field used for consistency checking
_ExpectedDigitalinputPorts = 0

############## Method to process an external file for table definition #################

def setPreferBinary(flag):
    global PreferBinary
    PreferBinary = flag

def parsefile():
    # Look for the table definition file in PYTHONPATH
    for path in sys.path:
        if verbosity: print('Looking for tabledefs in:', path)
        try:
            with open(path + '/tabledefs', 'r') as f:
                line = f.readline()
                while len(line) > 0:
                    if verbosity: print('Executing line:', line)
                    exec(line)
                    line = f.readline()
            break   # Quit if we successfully found and processed the file

        except:
            pass

    if len(DigitalPortTable) == 0 and len(PWMPortTable) == 0:
        print('Whoops - Unable to find and process tabledefs file\n\n')
        return(True)

    return(False)

# Check for and read file automagically upon import
_parseStatus = parsefile()

########################################################################################
def csvToBin(fname):
    # Define constants
    DIGITAL = 1
    PWM = 2

    # Make sure filename ends in .csv
    if fname[-4:] != '.csv': return

    # See if input file exists
    try:
        message = 'Trying to open input file'
        with open(fname, 'r') as f:
            # Read the header line
            hdr = f.readline()
            titles = hdr.split(',')
            ports = [None]      # No port for time column
            porttypes = [None]  # List of port types
            for i in range(1,len(titles)):
                ports.append(None)
                porttypes.append(None)
                indicator = titles[i][0]
                ports[i] = int(titles[i][1:])
                # Skip all channels with port number < 0 meaning unassigned
                if indicator == 'D':
                    porttypes[i] = DIGITAL
                elif indicator == 'S':
                    porttypes[i] = PWM

            # Open output file with .bin extension instead of .csv
            message = 'Trying to open output file'
            ofname = fname[:-4] + '.bin'
            of = open(ofname, 'wb')

            # Allocate a bytearray for the PWM values
            pwmlength = max(PWMPortTable)+1
            pwmvalues = bytearray(0x00 for i in range((max(PWMPortTable)+1)*4))

            # Determine how many bytes are needed for digital bits
            bitlength = max(DigitalPortTable) + 1
            bytelength = (bitlength + 7) >> 3

            # Process all the lines in the input file
            message = 'Processing input file'
            line = f.readline()
            while len(line) > 0:
                values = line.split(',')
                # Time, in msec, is first 4 bytes
                linebytes = bytearray(struct.pack('<L', int(values[0])))

                # Put all the values into the output byte arrays
                digint = 0
                for indx in range(1,len(values)):
                    if porttypes[indx] == PWM and ports[indx] < pwmlength:
                        onval = 0
                        offval = int(values[indx]) >> PWMPortTable[ports[indx]]['shift']
                        pwmvalues[ports[indx]*4:ports[indx]*4+4] = struct.pack('<HH', onval, offval)
                    elif porttypes[indx] == DIGITAL:
                        if int(values[indx]) != 0 and ports[indx] < bitlength:
                            mask = 1 << ports[indx]
                            digint |= mask

                # Concatenate bytes for output
                linebytes.extend(digint.to_bytes(bytelength, 'little'))
                linebytes.extend(pwmvalues)

                # Write bytes to output file
                of.write(linebytes)

                line = f.readline()

            of.close()

            # Return the name of the file created or None if a problem occurred
            return ofname

    except:
        if verbosity:
            print('Whoops - Trouble in csvToBin')
            print('Message:', message)
        # Just do nothing if file does not exist or other problems arise
        pass

    # Clean up memory before going back to our regular programming
    gc.collect()

    return None

######################  Self Test Code  ################################################
#/* Usage method */
def print_usage(name):
    """ Simple method to output usage when needed """
    sys.stderr.write("\nUsage: %s [-/-h/-help] [-v/-verbose] [-r/-regular]\n" % name);
    sys.stderr.write("This tool runs various checks on the configuration tables.\n");
    sys.stderr.write("-/-h/-help        :show this information\n");
    sys.stderr.write("-v/-verbose       :run more verbosely\n");
    sys.stderr.write("-r/-regular       :run regularity check\n");
    sys.stderr.write("-i/-infilename inf:name of csv file to convert to binary\n");
    sys.stderr.write("\n");
    sys.stderr.write("    Regularity is loosely defined as contiguous port numbering,\n");
    sys.stderr.write("order matching between ports and indices, etc.\n");
    sys.stderr.write("\n");
    sys.stderr.write("\n");
    sys.stderr.write("\n");
    sys.stderr.write("\n\n");

#/* Main */
def self_test():
    global verbosity

    regular = False
    infilename = None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '-' or sys.argv[i] == '-h' or sys.argv[i] == '-help':
            print_usage(sys.argv[0]);
            sys.exit(0);
        elif sys.argv[i] == '-v' or sys.argv[i] == '-verbose':
            verbosity = True
        elif sys.argv[i] == '-r' or sys.argv[i] == '-regular':
            regular = True
        elif sys.argv[i] == '-i' or sys.argv[i] == '-infilename':
            i += 1
            if i < len(sys.argv):
                infilename = sys.argv[i]
        else:
            sys.stderr.write("\nWhoops - Unrecognized argument: %s\n" % sys.argv[i]);
            print_usage(sys.argv[0]);
            sys.exit(10);

        i += 1

    # Initialize the check flag to False meaning everything is okay so far
    checkflag = False

    ### Check the Digital Port Table
    lastfunc = None
    currfunc = None
    lastport = None
    dgports = 0
    d5ports = 0
    dmports = 0
    if regular and len(DigitalPortTable) > 0 and min(DigitalPortTable) != 0:
        print('  Alert >>> Regularity test fails due to not starting with Digital port 0')
        checkflag = True
    for port in sorted(DigitalPortTable):
        if 'func' not in DigitalPortTable[port]:
            print('Whoops - Digital port %d is not configured correctly' % port)
            checkflag = True
        elif DigitalPortTable[port]['func'] == doMaestroDigital:
            dmports += 1
            if verbosity:
                print('Digital Port %2d via Maestro board %2d channel %2d' %
                    (port, DigitalPortTable[port]['board'], DigitalPortTable[port]['pwmout']))
            if regular:
                if lastport is not None and port != lastport+1:
                    print('  Alert >>> Regularity test fails for noncontiguous ports %d and %d' % (lastport, port))
                    checkflag = True
                    if verbosity:
                        for i in range(lastport+1, port):
                            print('    Missing digital port %2d' % i)
        elif DigitalPortTable[port]['func'] == do595:
            d5ports += 1
            if verbosity:
                print('Digital Port %2d via 595 index %3d' %
                    (port, DigitalPortTable[port]['index']))
            if regular:
                if lastport is not None and port != lastport+1:
                    print('  Alert >>> Regularity test fails for noncontiguous ports %d and %d' % (lastport, port))
                    checkflag = True
                    if verbosity:
                        for i in range(lastport+1, port):
                            print('    Missing digital port %2d' % i)
        elif DigitalPortTable[port]['func'] == dogpiodigital:
            dgports += 1
            if verbosity:
                print('Digital Port %2d via GPIO pin %2d' %
                    (port, DigitalPortTable[port]['pin']))
            if regular:
                if lastport is not None and port != lastport+1:
                    print('Alert >>> Regularity test fails for noncontiguous ports %d and %d' % (lastport, port))
                    checkflag = True
                    if verbosity:
                        for i in range(lastport+1, port):
                            print('    Missing digital port %2d' % i)
        else:
            print('Whoops - Digital port %d is not configured correctly' % port)
        lastport = port
    print('\nConfiguration has %d 595 ports, %d Maestro ports, and %d GPIO ports configured for digital signals\n' % (d5ports, dmports, dgports))

    # Run overwrite tests
    if _ExpectedDigitalPorts != len(DigitalPortTable):
        print('  WARNING - Length of DigitalPortTable is %d and not the expected %d' % 
            (len(DigitalPortTable),_ExpectedDigitalPorts))
        print('    Likely overwriting of ports\n')
        checkflag = True

    ### Check the PWM Port Table
    lastport = None
    dgports = 0
    d5ports = 0
    dmports = 0
    if regular and len(PWMPortTable) > 0 and min(PWMPortTable) != 0:
        print('Alert >>> Regularity test fails due to not starting with PWM port 0')
        checkflag = True
    for port in sorted(PWMPortTable):
        if 'func' not in PWMPortTable[port]:
            print('Whoops - PWM port %d is not configured correctly' % port)
        elif PWMPortTable[port]['func'] == dopca9685:
            d5ports += 1
            if verbosity:
                print('PWM Port %2d via pca9685 board %2d output %2d' %
                    (port, PWMPortTable[port]['board'], PWMPortTable[port]['pwmout']))
            if regular:
                if lastport is not None and port != lastport+1:
                    print('  Alert >>> Regularity test fails for noncontiguous ports %d and %d' % (lastport, port))
                    checkflag = True
                    if verbosity:
                        for i in range(lastport+1, port):
                            print('    Missing PWM port %2d' % i)
        elif PWMPortTable[port]['func'] == dogpio:
            dgports += 1
            if verbosity:
                print('PWM Port %2d via GPIO pin %2d' %
                    (port, PWMPortTable[port]['pin']))
            if regular:
                if lastport is not None and port != lastport+1:
                    print('  Alert >>> Regularity test fails for noncontiguous ports %d and %d' % (lastport, port))
                    checkflag = True
                    if verbosity:
                        for i in range(lastport+1, port):
                            print('    Missing PWM port %2d' % i)
        elif PWMPortTable[port]['func'] == domaestroPWM:
            dmports += 1
            if verbosity:
                print('PWM Port %2d via Maestro board %2d channel %2d' %
                    (port, PWMPortTable[port]['board'], PWMPortTable[port]['pwmout']))
            if regular:
                if lastport is not None and port != lastport+1:
                    print('  Alert >>> Regularity test fails for noncontiguous ports %d and %d' % (lastport, port))
                    checkflag = True
                    if verbosity:
                        for i in range(lastport+1, port):
                            print('    Missing PWM port %2d' % i)
        else:
            print('Whoops - PWM port %d is not configured correctly' % port)
            checkflag = True
        lastport = port
    print('\nConfiguration has %d pca9685 ports, %d Maestro ports, and %d GPIO ports configured for PWM signals\n' % (d5ports, dmports, dgports))

    # Run input specification tests
    numPorts = len(DigitalInputPortTable)
    if RunInputPort is not None: numPorts += 1
    if TriggerInputPort is not None: numPorts += 1
    if OptoInputPort is not None: numPorts += 1
    if _ExpectedDigitalinputPorts != numPorts:
        print('  WARNING - Number of digital input ports requested (%d) does not match number configured (%d)!' % 
            (_ExpectedDigitalinputPorts, numPorts))

    # Run overwrite tests
    if _ExpectedPWMPorts != len(PWMPortTable):
        print('  WARNING - Length of PWMPortTable is %d and not the expected %d' % (len(PWMPortTable),_ExpectedPWMPorts))
        print('    Likely overwriting of ports\n')
        checkflag = True

    # Run bad pin tests
    goodpins = [6,7,8,12,13,14,15,20,21,22]
    status = False
    for port in DigitalPortTable:
        if 'pin' in DigitalPortTable[port] and DigitalPortTable[port]['pin'] not in goodpins:
            print('Warning - Found Digital pin specification:', DigitalPortTable[port]['pin'], 'for port:', port,'NOT a valid pin')
            status = True

    for port in PWMPortTable:
        if 'pin' in PWMPortTable[port] and PWMPortTable[port]['pin'] not in goodpins:
            print('Warning - Found PWM pin specification:', PWMPortTable[port]['pin'], 'for port:', port,'NOT a valid pin')
            status = True

    if status: print('Valid GPIO pins are:', goodpins)

    if infilename is not None:
        csvToBin(infilename)

    return status or checkflag


if __name__ == "__main__":
    if not _parseStatus:
        flag = self_test()
        if not flag:
            exit(0)
    exit(1)
