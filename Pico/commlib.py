#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#**********************************
# Program commlib.py
# Created by john
# Created Thu Aug 3 06:29:28 PDT 2023
#*********************************/

#/* Import block */
import os
import sys
import subprocess
import serial
import binascii
import time

# Get path to actual commlib.py file and add path/lib to search path
_Path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(_Path)

# Now import tables from our extended path
import tables
from helpers import filecrc16
# Remove path so other code can't accidentally get to it
sys.path.remove(_Path)


################# Serial Comm Code #########################
portRoot = '/dev/ttyACM'    # Set by Hauntimator prior to comms

def openPort():
    # Try a whole bunch of port options
    for suffix in ['', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
        try:
            ser = serial.Serial(portRoot + suffix, 115200, timeout=5)
            break   # Found a good one
        except:
            if suffix == '9':
                sys.stderr.write('Whoops - Unable to open usb comm port with root:' + portRoot + '\n')
                return None
            pass
    return ser

def toPico(ser, instring):
    bytescount = ser.write(instring.encode('utf-8'))
    return bytescount

def stringToPico(instring):
    ser = openPort()
    if ser is not None:
        bytescount = toPico(ser, instring)
        ser.close()

def lineFromPico():
    line = []
    ser = openPort()
    if ser is not None:
        line = ser.readline().decode('utf-8')
        ser.close()
    return line

#################### Status Request Functions #################
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
    ser = openPort()
    if ser is None:
        return True # It is True that an error has occurred

    if os.path.isfile(filename):
        tf = open(filename, 'rb')
        fd = tf.fileno()
        fsize = os.fstat(fd).st_size * 2    # Two hex characters per byte
        count = 0
        toPico(ser, 'b %s %d\n' % (dest, fsize))
        if progressbar is not None: progressbar.setMaximum(fsize)
        td = tf.read(512)
        while len(td) > 0:
            count += len(td) * 2
            ser.write(binascii.hexlify(td))
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

    # Give some time for receiver to get all the data before closing the port
    time.sleep(2)
    #print('Closing serial port')
    ser.close()
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
    if binarySynced():
        tables.csvToBin(filename)
    else:
        sys.stderr.write('Whoops - Are binary formats synced for csvToBin?\n')

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

