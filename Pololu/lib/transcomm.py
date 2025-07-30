#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#**********************************
# Module transcomm.py
# Created by john
# Created Wed Jun 14 01:35:29 PM PDT 2025
#*********************************/

#/* Import block */
import os
import stat
import select
import shutil
import glob
import re
import sys
import math
import random
import serial
import binascii
import time

# Get path to actual file and add path/lib to search path
_Dir = os.path.dirname(os.path.realpath(__file__))

# Read port id from local cache file
portRoot = '/dev/ttyACM'
cachefile = os.path.join(_Dir, '.portid')
if os.path.exists(cachefile):
    with open(cachefile, 'r') as file:
        portRoot = file.read()

#/* Define block */
verbosity = False
tclient = False
tserver = False

# Base class
class Communications:
    def __init__(self):
        pass

    def isThereInput(self):
        return False

    def isReady(self):
        return False

    def read(self, numBytes=0):
        return None

    def readline(self):
        return None

    def writeline(self, inString):
        return False

    def write(self, inBytes=None, inLen = 0):
        return False

    def cleanup(self):
        pass

class FIFOComm(Communications):
    def __init__(self, inputFIFOName=None, outputFIFOName=None):
        super().__init__()

        # FIFO Names
        self.inputFIFOName = inputFIFOName
        self.outputFIFOName = outputFIFOName
        self.inputFIFO = None
        self.outputFIFO = None
        self.inpoll = None

        # Create the output FIFO to inform the world that we can talk but don't open it yet cuz that'll hang
        try:
            os.mkfifo(self.outputFIFOName)
        except FileExistsError:
            # Don't worry if it already exists
            pass
        except:
            sys.stderr.write('\nWHOOPS - Unable to create output FIFO %s\n', self.outputFIFOName)

    def isThereInput(self):
        if self.inpoll is not None:
            result = self.inpoll.poll(0)
            return len(result) > 0
        else:
            return False

    def isReady(self):
        '''
        The isReady method first checks to see if another process has created a named pipe
        or FIFO with the correct name that we want to read from.  If so, we open that pipe
        and also open our output pipe with the correct name that we want to write
        to.  Note that opening the output pipe blocks until someone attaches to it to read
        from it.

        Note that isReady should be called inside a loop that checks often as a process that
        wants to talk to us has to create their output pipe first and then check to see if
        this process has created its output pipe.  Once both pipes are created, both processes
        proceed with opening both input and output pipes.
        '''
        if os.path.exists(self.inputFIFOName) and stat.S_ISFIFO(os.lstat(self.inputFIFOName).st_mode):
            if self.inputFIFO is None:
                # Someone created our input fifo and is trying to connect to us so attach to that fifo
                # Create in non-blocking mode so we aren't waiting
                self.inputFIFO = os.fdopen(os.open(self.inputFIFOName, os.O_RDONLY | os.O_NONBLOCK))
                # Then immediately set back to blocking mode
                os.set_blocking(self.inputFIFO.fileno(), True)
                # Create poller to allow checking for input without reading
                self.inpoll = select.poll()
                self.inpoll.register(self.inputFIFO, select.POLLIN)
                # Create the output FIFO for our devoted fan
                self.outputFIFO = open(self.outputFIFOName, 'w')
                print('FIFOs are open')
        else:
            self.closeFIFOs()
        return self.inputFIFO is not None and self.outputFIFO is not None

    def read(self, numBytes=0):
        return self.inputFIFO.read(numBytes)

    def readline(self):
        return self.inputFIFO.readline()

    def writeline(self, inString):
        if len(inString) == 0 or inString[-1] != '\n':
            inString += '\n'
        status = self.outputFIFO.write(inString)
        self.outputFIFO.flush()
        return status

    def write(self, outBytes=None, outLen = 0):
        if outBytes == None:
            return 0
        status = self.outputFIFO.write(outBytes)
        self.outputFIFO.flush()
        return status

    def closeFIFOs(self):
        if True:  #try:
            if self.outputFIFO is not None:
                self.outputFIFO.close()
            self.outputFIFO = None
        else:  #except:
            pass
        if True: #try:
            if self.inputFIFO is not None:
                self.inputFIFO.close()
            self.inpoll = None
            self.inputFIFO = None
        else:  #except:
            pass

    def cleanup(self):
        self.closeFIFOs()
        os.remove(self.outputFIFOName)


def mainEventLoop(comm):
    if comm is None: return

    timing = 0.0
    while(not comm.isReady()):
        time.sleep(0.1)
        timing += 0.1
        sys.stdout.write('\rWaiting:%f' % timing)

    print('Comm is open')

    if tserver:
        while(not comm.isThereInput()):
            time.sleep(0.1)

        print('Data is available')

        line = comm.readline()
        print('Line Received:', line)

        bytes = comm.read(16)
        print('Bytes Received:', bytes)

        comm.writeline('Hello')

        comm.write('ABCDEFGHIJKLMNOP')

    elif tclient:
        comm.writeline('Hello')

        comm.write('ABCDEFGHIJKLMNOP')

        while(not comm.isThereInput()):
            time.sleep(0.1)

        print('Data is available')

        line = comm.readline()
        print('Line Received:', line)

        bytes = comm.read(16)
        print('Bytes Received:', bytes)

    comm.cleanup()

#/* Usage method */
def print_usage(name):
    """ Simple method to output usage when needed """
    sys.stderr.write("\nUsage: %s [-/-h/-help] [-v/-verbose]\n" % name);
    sys.stderr.write("    This tool runs simple tests on the selected comm channel.\n");
    sys.stderr.write("You must run both a server and a client version of this code.\n");
    sys.stderr.write("The first one run will wait for the second, they will handshake,\n");
    sys.stderr.write("and then communicate data back and forth before terminating.\n");
    sys.stderr.write("-/-h/-help        :show this information\n");
    sys.stderr.write("-v/-verbose       :run more verbosely\n");
    sys.stderr.write("-c/-client        :run client side\n");
    sys.stderr.write("-s/-server        :run server side\n");
    sys.stderr.write("\n\n");

#/* Main */
if __name__ == "__main__":

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '-' or sys.argv[i] == '-h' or sys.argv[i] == '-help':
            print_usage(sys.argv[0]);
            sys.exit(0);
        elif sys.argv[i] == '-v' or sys.argv[i] == '-verbose':
            verbosity = True
        elif sys.argv[i] == '-c' or sys.argv[i] == '-client':
            tclient = True
            tserver = False
        elif sys.argv[i] == '-s' or sys.argv[i] == '-server':
            tclient = False
            tserver = True
        else:
            sys.stderr.write("\nWhoops - Unrecognized argument: %s\n" % sys.argv[i]);
            print_usage(sys.argv[0]);
            sys.exit(10);

        i += 1

    # Initialize stuff
    # FIFOs
    if tclient:
        comm = FIFOComm(inputFIFOName = 'fifo.commtocontrol', outputFIFOName = 'fifo.controltocomm')
    elif tserver:
        comm = FIFOComm(inputFIFOName = 'fifo.controltocomm', outputFIFOName = 'fifo.commtocontrol')


    # Start the main loop
    mainEventLoop(comm)


