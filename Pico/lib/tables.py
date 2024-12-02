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

# Servo/PWM functions

# PWM Definitions
_i2c = None
_PWMBoards = {}         # Dictionary of Servos objects, one for each pca9685 board
_PWMGPIOs = {}          # Dictionary of GPIO pins set up for direct PWM control

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
            print('Ticks to nstantiate board if needed:', time.ticks_diff(time.ticks_us(), ticks))

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
    numPWMs = max(PWMPortTable)+1
    numDigs = max(DigitalPortTable)+1
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

# Digital Definitions
_DigitalGPIOs = {}          # Dictionary of GPIO pins set up for Digital control
_digitalCurrentState = None # Array of values prior to being shifted out to 595s
_DataPin = None
_ClockPin = None
_RclkPin = None
_ClearPin = None

def configure595s(firstport=0, portcount=24, datapin=26, clockpin=27, rclkpin=21, clearpin=20):
    # Configure a block of portcount ports supproted by 595s at 8 ports per board
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

def setAllDigital(value):
    for port in DigitalPortTable:
        setDigital(port, value)
    outputDigital()

def outputDigital():
    output595s()
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
                    exec(line)
                    line = f.readline()
            break   # Quit if we successfully found and processed the file

        except:
            pass

    if len(DigitalPortTable) == 0 and len(PWMPortTable) == 0:
        print('Whoops - Unable to find and process tabledefs file\n\n')

# Check for and read file automagically upon import
parsefile()

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

    except:
        if verbosity:
            print('Whoops - Trouble in csvToBin')
            print('Message:', message)
        # Just do nothing if file does not exist or other problems arise
        pass
        
    # Clean up memory before going back to our regular programming
    gc.collect()
            

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

    ### Check the Digital Port Table
    lastfunc = None
    currfunc = None
    lastport = None
    dgports = 0
    d5ports = 0
    if regular and min(DigitalPortTable) != 0:
        print('  Alert >>> Regularity test fails due to not starting with Digital port 0')
    for port in sorted(DigitalPortTable):
        if 'func' not in DigitalPortTable[port]:
            print('Whoops - Digital port %d is not configured correctly' % port)
        elif DigitalPortTable[port]['func'] == do595:
            d5ports += 1
            if verbosity:
                print('Digital Port %2d via 595 index %3d' %
                    (port, DigitalPortTable[port]['index']))
            if regular:
                if lastport is not None and port != lastport+1:
                    print('  Alert >>> Regularity test fails for noncontiguous ports %d and %d' % (lastport, port))
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
                    if verbosity:
                        for i in range(lastport+1, port):
                            print('    Missing digital port %2d' % i)
        else:
            print('Whoops - Digital port %d is not configured correctly' % port)
        lastport = port
    print('\nConfiguration has %d 595 ports and %d GPIO ports configured for digital signals\n' % (d5ports, dgports))

    # Run overwrite tests
    if _ExpectedDigitalPorts != len(DigitalPortTable):
        print('  WARNING - Length of DigitalPortTable is %d and not the expected %d' % 
            (len(DigitalPortTable),_ExpectedDigitalPorts))
        print('    Likely overwriting of ports\n')

    ### Check the PWM Port Table
    lastport = None
    dgports = 0
    d5ports = 0
    if regular and min(PWMPortTable) != 0:
        print('Alert >>> Regularity test fails due to not starting with PWM port 0')
    for port in sorted(PWMPortTable):
        if 'func' not in PWMPortTable[port]:
            print('Whoops - PWM port %d is not configured correctly' % port)
        elif PWMPortTable[port]['func'] == dopca9685:
            d5ports += 1
            if verbosity:
                print('PWM Port %2d via pca9685 board %2d output %d' %
                    (port, PWMPortTable[port]['board'], PWMPortTable[port]['pwmout']))
            if regular:
                if lastport is not None and port != lastport+1:
                    print('  Alert >>> Regularity test fails for noncontiguous ports %d and %d' % (lastport, port))
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
                    if verbosity:
                        for i in range(lastport+1, port):
                            print('    Missing PWM port %2d' % i)
        else:
            print('Whoops - PWM port %d is not configured correctly' % port)
        lastport = port
    print('\nConfiguration has %d pca9685 ports and %d GPIO ports configured for PWM signals\n' % (d5ports, dgports))

    # Run overwrite tests
    if _ExpectedPWMPorts != len(PWMPortTable):
        print('  WARNING - Length of PWMPortTable is %d and not the expected %d' % (len(PWMPortTable),_ExpectedPWMPorts))
        print('    Likely overwriting of ports\n')

    # Run bad pin tests
    goodpins = [2,3,4,5,6,7,8,12,13,14,15,20,21,22]
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


if __name__ == "__main__":
    self_test()
