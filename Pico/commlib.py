
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

#################### Library functions ########################
##### File Transfers
def xferFileToController(filename, dest=''):
    if os.path.isfile(filename):
        # Use rshell to transfer file
        command = 'rshell cp %s %s' % (filename, dest)
        command = ['rshell', 'cp', filename, dest]
        print('Running command:', command)

        # Get the size of the file to estimate transfer time
        tf = open(filename, 'r')
        fd = tf.fileno()
        filesize = os.fstat(fd).st_size
        tf.close()
        timeout = int(filesize /16000 + 5)  # About 16kb per sec + rshell setup time

        # Do the transfer
        try:
            status = subprocess.run(command, timeout=timeout)
            # Check return code
            if status.returncode < 0:
                sys.stderr.write('Whoops - Failure to write file %s to Pico\n' % filename)
            return status.returncode
        except:
            # Probably timed out so return error code
            return -1

    else:
        sys.stderr.write('Whoops - Unable to find transfer file %s\n' % filename)
        return -1

def xferFileFromController(filename, dest=''):
    # Use rshell to transfer file
    command = ['rshell', 'cp', filename, dest]
    code = subprocess.call(command, shell=True)
    # Check return code
    if code < 0:  # I think rshell ALWAYS returns 0, even on error
        sys.stderr.write('Whoops - Failure to read file from Pico\n' % filename)
    return code

def xferFileToSD(filename, dest='/'):
    sys.stderr.write('Whoops - Accessing SD in not yet implemented\n')
    pass

def xferFileFromSD(filename, dest='/'):
    sys.stderr.write('Whoops - Accessing SD in not yet implemented\n')
    pass

def startMain():
    command = ['rshell',
                'repl',
                '~',
                'import main',
                '~',
                'main.do_the_thing()',
                '~']
    subprocess.run(command)
    

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
    command = ['rshell',
                'repl',
                '~',
                'from machine import Pin, PWM',
                '~',
                'pwm = PWM(Pin(%d))' % self.port,
                '~',
                'pwm.freq(50)',
                '~',
                'pwm.duty_ns(%d)' % angleToDutyCycle(angle),
                '~']
    print('with:', command)
    # code = subprocess.run(command)
    pass

def _releaseServoOnPico(channel):
    pass

def _setServoViaPCA9685(channel, cyclefrac):
    cyclefrac = cyclefrac/180.0*0.09+0.03
    command = ['rshell',
                'repl',
                '~',
                'import helpers',
                '~',
                'helpers.setServo(%d,%f)' % (channel,cyclefrac),
                '~']
    print('with:', command)
    code = subprocess.run(command)
    pass

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

