#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#**********************************
# Program commlib.py
# Created by john
# Created Thu Aug 3 06:29:28 PDT 2023
#*********************************/

#/* Import block */
import os
import stat
import select
import sys
import subprocess
import serial
import binascii
import time

#######################################################################
'''
commlib provides the following set of functions as a layer between the
Hauntimator applications and the controller and hardware:

isReady()
    Returns True if commlib can talk tot he hardware and False otherwise
getPort()
    Returns the name of the port commlib is using to talk to the hardware
    Must be called AFTER isReady()
setDigitalChannel(port, state)
    Sets the specified digital channel to the specified state (1 or 0)
setServo(port, state)
    Sets the specified PWM/servo channel to the specified state
    May be shifted and scaled prior to going to the output
getConfiguredDigitalPorts()
    Returns a list of port numbers that are assigned to digital ports
getConfiguredPWMPorts()
    Returns a list of port numbers that are assigned to PWM/servo ports
playOnce()
    Initiates a animatronics playback on the hardware.  Which animation
    will be played depends on the set available.  If called while a
    playback is running it is queued and run after the previous is done.
csvToBin(fileName)
    Converts the specified file, whose name must end in .csv, to the
    binary format in a file of the same name but an extension of .bin.
xferCSVToController(filename, dest='', progressbar=None)
    If the system wants binary control files, it converts the specified
    csv file to binary form and installs it on the controller.  Else,
    it installs the csv file on the controller.
    dest specifies the destination file and path and must be specified.
xferFileToController(filename, dest='', progressbar=None)
    Transfers a file of any type to the controller with the same name.
    dest specifies the destination file and path and must be specified.

All these functions must be implemented for all hardware types.
'''
######################################################################

# Get path to actual commlib.py file and add path/lib to search path
_Dir = os.path.dirname(os.path.realpath(__file__))
_Path = os.path.join(_Dir, 'lib')
sys.path.append(_Path)
# Now import tables from our extended path
import tables

import transcomm

# Read port id from local cache file
portRoot = '/dev/ttyACM'    # May be set by Hauntimator prior to comms
cachefile = os.path.join(_Dir, '.portid')
if os.path.exists(cachefile):
    with open(cachefile, 'r') as file:
        portRoot = file.read()

# Remove path so other code can't accidentally get to it
sys.path.remove(_Path)

# Name the Pololu controller to be used
controller = None

commdev = transcomm.FIFOComm(
    outputFIFOName = '/tmp/fifo.commtocontrol',
    inputFIFOName = '/tmp/fifo.controltocomm'
)

################# Serial Comm Code #########################

def openPort():
    global portRoot
    global controller

    # Try a whole bunch of port options
    for suffix in ['', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
        try:
            ser = serial.Serial(portRoot + suffix, 115200, timeout=5)
            # Save the good port
            portRoot = portRoot + suffix
            break   # Found a good one
        except:
            if suffix == '9':
                sys.stderr.write('Whoops - Unable to open usb comm port with root:' + portRoot + '\n')
                return None
            pass
    return ser

def getPort():
    # Return the last found working port
    return portRoot

def toPico(ser, instring):
    bytescount = ser.write(instring.encode('utf-8'))
    return bytescount

def stringToPico(instring):
    if verbosity: print('Sending instring:', instring)
    if commdev.isReady():
        commdev.writeline(instring)
    return

def lineFromPico():
    line = []
    ser = openPort()
    if ser is not None:
        line = ser.readline().decode('utf-8')
        ser.close()
    return line

#################### Status Request Functions #################
def isReady():
    return commdev.isReady()

def cleanup():
    commdev.cleanup()

def getBinarySizes():
    line = ''
    # Status requires round trip so port cannot be closed in between
    binaryflag = False
    ser = openPort()
    if ser is not None:
        toPico(ser, 'statusb\n')
        binaryflag = ser.readline().decode('utf-8')[0:4] == 'True'
        line = ser.readline().decode('utf-8')
        ser.close()

    values = line.split()
    for i in range(len(values)):
        values[i] = int(values[i])
    return binaryflag, values

def getFileChecksum(filename):
    line = ''
    # Status requires round trip so port cannot be closed in between
    ser = openPort()
    if ser is not None:
        toPico(ser, 'c %s\n' % filename)
        line = ser.readline().decode('utf-8')
        ser.close()

    checksum = line.strip()
    if len(checksum) > 0:
        checksum = int(checksum)
    else:
        checksum = -1
    return checksum

# Set to True if the local copies of tables.py and tabledefs
# exactly match those installed on the Pico.
I_Solemnly_Swear_That_The_Tables_Are_Synced_With_The_Pico = True

def binarySynced():
    # Avoid checking board status over USB and assume we know everything
    return I_Solemnly_Swear_That_The_Tables_Are_Synced_With_The_Pico
    picoBinaryFlag, picoBlockSizes = getBinarySizes()
    localBlockSizes = list(tables.getBinarysizes())
    localBinaryFlag = tables.PreferBinary
    return picoBinaryFlag == localBinaryFlag and picoBlockSizes == localBlockSizes

def portCounts():
    if binarySynced() and len(tables.PWMPortTable) > 0 and len(tables.DigitalPortTable) > 0:
        return min(tables.PWMPortTable), max(tables.PWMPortTable)+1, min(tables.DigitalPortTable), max(tables.DigitalPortTable)+1
    else:
        return None

def getConfiguredPWMPorts():
    if binarySynced() and len(tables.PWMPortTable) > 0:
        ports = []
        for indx in range(min(tables.PWMPortTable), max(tables.PWMPortTable)+1):
            if indx in tables.PWMPortTable:
                ports.append(indx)
        return ports
    else:
        return None

def getConfiguredDigitalPorts():
    if binarySynced() and len(tables.DigitalPortTable) > 0:
        ports = []
        for indx in range(min(tables.DigitalPortTable), max(tables.DigitalPortTable)+1):
            if indx in tables.DigitalPortTable:
                ports.append(indx)
        return ports
    else:
        return None


#################### Library functions ########################
##### File Transfers
def xferFileToController(filename, dest='', progressbar=None):
    # Transfer any type of file to the Pico
    ser = commdev
    if ser is None:
        return True # It is True that an error has occurred

    if os.path.isfile(filename):
        tf = open(filename, 'rb')
        fd = tf.fileno()
        fsize = os.fstat(fd).st_size
        count = 0
        print('Opening dest file:', dest, 'in directory:', _Dir)
        of = open(_Dir + dest, 'wb')
        if progressbar is not None: progressbar.setMaximum(fsize)
        td = tf.read(512)
        while len(td) > 0:
            count += len(td)
            of.write(td)
            td = tf.read(512)
            if progressbar is not None:
                if fsize > 20000:
                    # If worth showing progress bar
                    progressbar.setValue(count)
                    if progressbar.wasCanceled():
                        break
                else:
                    # Don't bother progress bar if not much data
                    progressbar.setVisible(False)    # Never show progress bar

        tf.close()
        of.close()

    startMain()

    return False

def xferCSVToController(filename, dest='', progressbar=None):
    '''
    This method converts CSV control files to binary form prior to shipping them
    over to the Pico.  Since the Pico takes quite awhile to do the conversion, we
    do it here where it is still Pico dependent but on the desktop for speed.
    Return Codes:
         0: Uploaded what the Pico wanted (binary or csv)
         1: Uploaded csv because we don't know what the Pico wants or binarizing failed
        -1: Actual upload failed for whatever reason
    '''
    # Add error handling!!!
    ofname = None
    picoBinaryFlag = binarySynced()
    if picoBinaryFlag and tables.PreferBinary:
        # Pico and local match and Pico wants binary
        ofname = tables.csvToBin(filename)
        if ofname is not None:
            statusflag = 0
            # Change dest extension to .bin
            if len(dest) > 4: dest = dest[:-4] + '.bin'
            if xferFileToController(ofname, dest=dest, progressbar=progressbar):
                os.remove(ofname)
                statusflag = -1
        else:
            # Error binarizing the CSV file so send the CSV file as is
            statusflag = 1
            if xferFileToController(filename, dest=dest, progressbar=progressbar):
                statusflag = -1
    elif picoBinaryFlag and not tables.PreferBinary:
        # Pico and local match and Pico wants CSV
        statusflag = 0
        if xferFileToController(filename, dest=dest, progressbar=progressbar):
            statusflag = -1
    else:
        # We don't know what Pico wants so send CSV
        statusflag = 1
        if xferFileToController(filename, dest=dest, progressbar=progressbar):
            statusflag = -1

    return statusflag

def xferFileFromController(filename, dest=''):
    sys.stderr.write('Whoops - Accessing files is not yet implemented\n')

def xferBinaryFileFromController(filename, dest='/'):
    sys.stderr.write('Whoops - Accessing binary files is not yet implemented\n')

def csvToBin(filename):
    # Converts an existing CSV control file to binary format
    pass

##### Control
def startMain():
    # Reboots the Pico
    stringToPico('x\n')

def playOnce():
    # Simulates 1 trigger press
    stringToPico('a\n')

def setServo(channel, cyclefrac):
    outstring = 's %d %d\n' % (channel, cyclefrac)
    stringToPico(outstring)

def releaseServo(channel):
    outstring = 's %d %d\n' % (channel, 0)
    stringToPico(outstring)

def setDigitalChannel(channel, value):
    outstring = 'd %d %d\n' % (channel, value)
    stringToPico(outstring)


#/* Define block */
verbosity = False

#/* Usage method */
def print_usage(name):
    """ Simple method to output usage when needed """
    sys.stderr.write("\nUsage: %s [-/-h/-help] [-v/-verbose]\n" % name);
    sys.stderr.write("Runs unit tests on this communication library.\n");
    sys.stderr.write("-/-h/-help  :show this information\n");
    sys.stderr.write("-v/-verbose :run more verbosely (Default silent on success)\n");
    sys.stderr.write("\n\n");

#/* Main */
def main():
    global verbosity

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '-' or sys.argv[i] == '-h' or sys.argv[i] == '-help':
            print_usage(sys.argv[0]);
            sys.exit(0);
        elif sys.argv[i] == '-v' or sys.argv[i] == '-verbose':
            verbosity = True
        else:
            sys.stderr.write("\nWhoops - Unrecognized argument: %s\n" % sys.argv[i]);
            print_usage(sys.argv[0]);
            sys.exit(10);

        i += 1

    if(verbosity): print('Creating temporary file')
    tfile = open('abcdef', 'w')
    tfile.write('This is a test of file transfers to the Pico\n')
    tfile.close()
    if(verbosity): print('Transferring temporary file')
    xferFileToController('abcdef', dest='/')
    if(verbosity): print('Bringing it back')
    xferFileFromController('/abcdef', dest='./123456')
    if(verbosity): print('Checking it')
    status = subprocess.call('cmp abcdef 123456', shell=True)
    if(verbosity): print('Status:', status)
    if status == 0:
        if(verbosity): print('It worked')
    else:
        print('Failed miserably')
        sys.exit(10)

if __name__ == "__main__":
    main()

