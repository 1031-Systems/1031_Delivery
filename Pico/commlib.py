
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

################# Serial Comm Code #########################
def openPort():
    portRoot = '/dev/ttyACM'

    try:
        ser = serial.Serial(portRoot + '0', 115200, timeout=15)
    except:
        try:
            ser = serial.Serial(portRoot + '1', 115200, timeout=15)
        except:
            sys.stderr.write('\nWhoops - Unable to open ' + portRoot + '0 or ' + portRoot + '1 for serial communications\n')
            return None
    return ser

def toPico(ser, instring):
    bytescount = ser.write(instring.encode('utf-8'))
    return bytescount

def stringToPico(instring):
    ser = openPort()
    if ser is not None:
        bytescount = toPico(ser, instring)
        ser.close()

#################### Library functions ########################
##### File Transfers
def xferFileToController(filename, dest=''):
    ser = openPort()
    if ser is None:
        return -1

    if os.path.isfile(filename):
        tf = open(filename, 'rb')
        fd = tf.fileno()
        fsize = os.fstat(fd).st_size * 2    # Two hex characters per byte
        toPico(ser, 'b %s %d\n' % (dest, fsize))
        td = tf.read(512)
        while len(td) > 0:
            fsize -= len(td)
            ser.write(binascii.hexlify(td))
            td = tf.read(512)
        tf.close()

    ser.close()
    return 0

def xferFileFromController(filename, dest=''):
    # Use rshell to transfer file
    command = ['rshell', 'cp', filename, dest]
    code = subprocess.call(command, shell=True)
    # Check return code
    if code < 0:  # I think rshell ALWAYS returns 0, even on error
        sys.stderr.write('Whoops - Failure to read file from Pico\n' % filename)

def xferBinaryFileFromController(filename, dest='/'):
    sys.stderr.write('Whoops - Accessing SD in not yet implemented\n')
    pass

def startMain():
    stringToPico('x\n')

##### Control
def angleToDutyCycle(angle, servotype=None):
    return 1500000  # FIXME - hardcoded to 90 deg for PG90
    if servotype is not None and servotype in ServoTypes:
        # Find servo type in master list
        # Extract factors to convert with and convert
        return 1000000 + int(1000000 * angle / 180.0)   # FIXME Hardcoded to pG90 servo
    else:
        return None
    
def _setServoOnPico(channel, angle):
    # Send the value, appropriately formatted, to hardware controller
    print('Sending to controller port %d value %d' % (self.port, value))
    outstring = 's %d %d\n' % (self.port, value)
    stringToPico(outstring)
    return
    pass

def _releaseServoOnPico(channel):
    pass

def _setServoViaPCA9685(channel, cyclefrac):
    outstring = 's %d %d\n' % (channel, cyclefrac)
    stringToPico(outstring)
    return

def _releaseServoViaPCA9685(channel):
    pass

def setServo(channel, cyclefrac):
    # Call setLocalServo or setServoViaPCA9685 depending
    _setServoViaPCA9685(channel, cyclefrac)
    pass
    
def releaseServo(channel, angle):
    # Call releaseLocalServo or releaseServoViaPCA9685 depending
    pass

def setDigitalChannel(channel, value):
    # Call setDigitalOnPico or setDigitalVia74HC595
    pass

def setDigitalOnPico(channel, value):
    pass

def setDigitalVia74HC595(channel, value):
    pass


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

