# Basic Imports

from machine import Pin
import os
import utime
import binascii
import tables

############# Servo Code #################################
def setServo(index=-1, cycletime=0, push=True):
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

############# Wave File Player ################################
import wave
from machine import I2S
import _thread

I2SDataPin = 9
I2SBitClockPin = 10
I2SChannelPin = 11

AudioBlockSize = 1024
CSVAsciiBlockSize = 512

class WavePlayer:
    def __init__(self, wavefilename, csvfilename=None, binblocksize=0, verbose=0):
        self.verbose = verbose
        self.filename = wavefilename
        try:
            self.file = wave.open(self.filename)
        except:
            self.file = None
            return
        self._volume = 0.5

        # Open the csvfile if specified
        self.fullqueue = []
        self.emptyqueue = []
        self.queuesize = 0
        self.binblocksize = 0

        # Set up for binary or ascii control file I/O
        if binblocksize > 0:
            # Use binary file format with fixed size records
            try:
                self.csvfile = open(csvfilename, 'rb')
                # If opening is successful, set up data queue
                self.binblocksize = binblocksize
                # Create a semaphore lock for threads to coordinate getting and putting data in queue
                self.queuelock = _thread.allocate_lock()
                # Fill the queue initially
                self.queuesize = 5
                # initially fill the empty queue
                for i in range(self.queuesize):
                    self.emptyqueue.append(bytearray(binblocksize))
                # Read in the first two blocks of binary data
                self.bfillqueue()
            except:
                pass    # Ignore any errors including filename is None
        else:
            # Use ASCII file format with variable size records
            try:
                self.csvfile = open(csvfilename, 'r')
                # If opening is successful, set up data queue
                # Create a semaphore lock for threads to coordinate getting and putting data in queue
                self.queuelock = _thread.allocate_lock()
                # Fill the queue initially
                self.queuesize = 5
                # initially fill the queue
                self.fillqueue()
            except:
                pass    # Ignore any errors including filename is None

        # Set up ping-pong audio buffers
        self.audiodata = [None] * 2
        self.currbuffer = 0
        self.audiodata[0] = bytearray(AudioBlockSize)
        self.audiodata[1] = bytearray(AudioBlockSize)

        # Initialize stats
        self.startTicks = 0
        self.sumuploadticks = 0
        self.sumreadfilemsec = 0
        self.suspendedusec = 0
        self.blocksplayed = 0
        self.csvfiletime = 0

        # Compute number of frames in a 512-byte block
        self.blockframes = int(512/self.file.getsampwidth()/self.file.getnchannels())

        # Stop Flag set to not play initially
        self.stopflag = True
        self.controlstop = True

        # Set semaphore to indicate that we need to write again
        self.emptyflag = True

        # Set up pins for I2S
        datapin = Pin(I2SDataPin, Pin.OUT)
        bitclockpin = Pin(I2SBitClockPin, Pin.OUT)
        channelpin = Pin(I2SChannelPin, Pin.OUT)

        # Create the audio out channel over I2S
        self.audio_out = I2S(1,
                sck=bitclockpin, ws=channelpin, sd=datapin,
                mode=I2S.TX,
                bits=self.file.getsampwidth() * 8,
                format=(I2S.MONO if self.file.getnchannels() == 1 else I2S.STEREO),
                rate=self.file.getframerate(),
                ibuf=AudioBlockSize*4)

        # Create a semaphore lock for outside reads to avoid interfering with reads in this thread
        self.readLock = _thread.allocate_lock()

        # Read in first buffer so we are ready to play
        self.loadbuffer(self.currbuffer)
        self.stopflag = False
        self.controlstop = False

    def fillqueue(self):
        startTicks = utime.ticks_us()
        while len(self.fullqueue) < self.queuesize:
            line = self.csvfile.readline()
            self.queuelock.acquire()
            self.fullqueue.append(line)
            self.queuelock.release()
        self.csvfiletime += utime.ticks_diff(utime.ticks_us(), startTicks)

    def bfillqueue(self):
        while len(self.emptyqueue) > 0:
            # Pop empty buffer off of empty queue
            self.queuelock.acquire()
            buffer = self.emptyqueue.pop(0)
            self.queuelock.release()
            # Fill it up
            BLOCKSIZE = 512  # Don't read more than 512 bytes per read
            f = self.csvfile
            n = self.binblocksize
            mv = memoryview(buffer)
            bytes_read = 0
            for i in range(0, n - BLOCKSIZE, BLOCKSIZE):
                bytes_read += f.readinto(mv[i:i + BLOCKSIZE])
            if bytes_read < n:
                bytes_read += f.readinto(mv[bytes_read:n])
            # Push it onto full queue
            if bytes_read == 0: buffer = b''    # Klugey way to tell it the file is empty so it will stop??
            self.queuelock.acquire()
            self.fullqueue.append(buffer)
            self.queuelock.release()

    def readline(self, emptybuf=None):
        # Must be called from another thread to prevent locking
        if self.controlstop:
            return('')
        if emptybuf is not None and self.binblocksize > 0:
            self.emptyqueue.append(emptybuf)
        while len(self.fullqueue) < 1:
            self.suspendedusec += 20
            utime.sleep_us(20)
        self.queuelock.acquire()
        outline = self.fullqueue.pop(0)
        self.queuelock.release()
        self.controlstop = len(outline) == 0
        return outline

    def close(self):
        # Just to make it look like a file
        pass

    def irq(self, arg):
        self.emptyflag = True
        if self.verbose > 1: print('In irq arg:', arg)

    def play(self):
        if self.file is None: return
        if self.verbose > 0: print('Running play() in thread', _thread.get_ident())
        # Play until done or stopped
        self.stopflag = False
        self.controlstop = False
        # Kick off playback in a new thread
        _thread.start_new_thread(self.threadplay, (False,))

    def threadplay(self, dummy):
        if self.verbose > 0: print('Running threadplay() in thread', _thread.get_ident())
        # Initialize statistics
        self.startTicks = utime.ticks_us()
        self.sumuploadticks = 0
        self.sumreadfileticks = 0
        self.suspendedusec = 0
        self.blocksplayed = 0
        self.csvfiletime = 0

        # Set interrupt service routine to make write non-blocking
        self.audio_out.irq(self.irq)

        # Play until end of data or stopped
        while not self.stopflag or not self.controlstop: self.playblock(False)

        # Try to more explicitly kill the thread
        _thread.exit()

    def playblock(self, junk):
        #print('Entered playblock')
        # Make sure data queue is full
        if not self.controlstop:
            if self.binblocksize > 0:
                self.bfillqueue()
            else:
                self.fillqueue()

        # Check to see if we are stopped
        if not self.stopflag:
            #if self.verbose > 1: print('Running playblock() in thread', _thread.get_ident())

            if self.emptyflag:
                self.emptyflag = False
                # Play one block of audio data from current ping-pong buffer
                startTicks = utime.ticks_us()
                self.audio_out.write(self.audiodata[self.currbuffer])
                totaluploadticks = utime.ticks_diff(utime.ticks_us(), startTicks)
                if self.verbose > 1: print('Ticks to write block to i2s', totaluploadticks)
                self.sumuploadticks += totaluploadticks
                self.blocksplayed += 1
    
                # Fill the buffer while playing previous buffer
                # Switch to other buffer
                self.currbuffer = 1 - self.currbuffer
                startTicks = utime.ticks_us()
                self.loadbuffer(self.currbuffer)
                self.sumreadfileticks += utime.ticks_diff(utime.ticks_us(), startTicks)


    def loadbuffer(self, buffer):
        startTicks = utime.ticks_us()
        self.readLock.acquire()
        size = self.file.readframes(AudioBlockSize, databuf=self.audiodata[buffer])
        if size == 0: self.stopflag = True
        self.readLock.release()
        if self.verbose > 1: print('Ticks to read block:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usec')

    def stop(self):
        # Stop playing
        self.stopflag = True
        self.controlstop = True
        # Dump statistics
        if self.verbose > 0:
            print('Total time spent reading csv file  :', self.csvfiletime, 'usec')
            print('Total time spent reading audio data:', self.sumreadfileticks, 'usec')
            print('Total time spent uploading data    :', self.sumuploadticks, 'usec')
            print('Total estimated time queue waiting :', self.suspendedusec, 'usec')
            print('Total time                         :', utime.ticks_diff(utime.ticks_us(), self.startTicks), 'usec')
            print('Total audio played                 :', self.blocksplayed * self.blockframes * 1000000 * AudioBlockSize / 512 / self.file.getframerate(), 'usec')
        pass

    def rewind(self):
        if self.file is None: return
        if not self.stopflag or not self.controlstop: self.stop()
        # Get ready to start from the top
        self.file.close()
        try:
            self.file = wave.open(self.filename)
        except:
            self.file = None

    def volume(self, newVolume=None):
        if newVolume is None:
            return self._volume
        else:
            self._volume = newVolume

    def playing(self):
        return not self.stopflag or not self.controlstop



############# SD Card Code #################################
import machine
import os
import sdcard

def mountSDCard(mountpoint='/sd'):
    # Assign chip select (CS) pin (and start it high)
    cs = machine.Pin(17, machine.Pin.OUT)

    # Initialize SPI peripheral (start with 1 MHz)
    spi = machine.SPI(0,
                      baudrate=4000000,
                      polarity=0,
                      phase=0,
                      bits=8,
                      firstbit=machine.SPI.MSB,
                      sck=machine.Pin(18, machine.Pin.OUT),
                      mosi=machine.Pin(19, machine.Pin.OUT),
                      miso=machine.Pin(16, machine.Pin.OUT))

    # Initialize SD card
    sd = sdcard.SDCard(spi, cs)

    # Set the speed to fast enough for audio
    # Have to set it here because the SDCard constructor above sets the baudrate back to 1,000,000
    spi.init(baudrate=40000000)

    # Mount filesystem
    vfs = os.VfsFat(sd)
    os.mount(vfs, mountpoint)

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
    if inline[0] == 'a':
        # Trigger one playback
        return 1
    elif inline[0] == 'x':
        # Wait 2 seconds for commlib to close connection
        utime.sleep_ms(2000)
        # Restart everything
        machine.reset()
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
    elif inline[0] == 'b':
        # Upload entire binary file
        try:
            vals = inline.split()
            filename = vals[1]
            fsize = int(vals[2])
            file = open(filename, 'wb')
            line = sys.stdin.buffer.read(min(fsize, 512))
            while fsize > 0:
                bwritten = file.write(binascii.unhexlify(line))
                fsize -= len(line)
                if fsize > 0: line = sys.stdin.buffer.read(min(fsize, 512))
            file.close()
            if tables.PreferBinary:
                # Convert the file to binary format
                tables.csvToBin(filename)
        except:
            # sys.stderr.write('\nWhoops - Unable to write file %d\n' % filename)
            pass
    return 0

################################### Animation File Finder ############################
def isfile(testfile):
    try:
        size = os.stat(testfile)[6]
        return size > 0
    except:
        return False

def pathjoin(path, fname):
    if path is not None:
        if path[-1] != '/':
            path += '/'
        fname = path + fname
    return fname

def findAnimFiles(dir='/anims'):
    # Find animation files
    # Create empty list of csv/audio file pairs
    animList = []

    # Look for binary or ascii files?
    if tables.PreferBinary:
        ext = '.bin'
    else:
        ext = '.csv'

    # Check for an existing list of files
    testfile = pathjoin(dir, 'animlist')
    if isfile(testfile):
        with open(testfile, 'r') as infile:
            line = infile.readline()
            while len(line) > 0:
                names = line.split()
                if len(names) == 2:
                    # Should be both a csv filename and an audio filename
                    # Not checking for existence yet
                    animList.append(names)
                elif len(names) == 1:
                    # Should be a fileroot that will be appended with .csv or .wav
                    tpair = []
                    if isfile(names[0] + ext):
                        tpair.append(names[0] + ext)
                    elif isfile(pathjoin(dir, names[0] + ext)):
                        tpair.append(pathjoin(dir, names[0] + ext))
                    else:
                        tpair.append(None)
                    if isfile(names[0] + '.wav'):
                        tpair.append(names[0] + '.wav')
                    elif isfile(pathjoin(dir, names[0] + '.wav')):
                        tpair.append(pathjoin(dir, names[0] + '.wav'))
                    else:
                        tpair.append(None)
                    animList.append(tpair)
                line = infile.readline()
    else:
        # Check for matching filename pairs
        try:
            filelist = os.listdir(dir)
            for filename in filelist:
                tpair = []
                if filename[-4:] == ext:
                    tpair.append(pathjoin(dir, filename))
                    tname = filename[:-4] + '.wav'
                    if tname in filelist:
                        tpair.append(pathjoin(dir, tname))
                        animList.append(tpair)
        except:
            # Ignore problems
            pass

    return animList

################################### Test Code ########################################
def testSDCard(filename, verbosity=False):
    file = open(filename, 'rb')
    bytesize = 1
    while bytesize < 300:
        if verbosity: print('Trying to read', bytesize, 'bytes from file:', filename)
        startTicks = utime.ticks_us()
        data = file.read(bytesize)
        if verbosity: print('Actually read:', len(data), 'in:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usec')
        bytesize = bytesize * 2
    while len(data) > 0:
        if verbosity: print('Trying to read', bytesize, 'bytes from file:', filename)
        startTicks = utime.ticks_us()
        data = file.read(bytesize)
        if verbosity: print('Actually read:', len(data), 'in:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usec')
    file.close()

    file = open(filename, 'rb')
    bytesize = 256
    readsize = 0
    startTicks = utime.ticks_us()
    data = file.read(bytesize)
    while len(data) > 0:
        readsize += len(data)
        data = file.read(bytesize)
    print('Actually read', readsize, 'bytes of data in:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usec')
    file.close()

    file = open(filename, 'rb')
    bytesize = 512
    readsize = 0
    startTicks = utime.ticks_us()
    data = file.read(bytesize)
    while len(data) > 0:
        readsize += len(data)
        data = file.read(bytesize)
    print('Actually read', readsize, 'bytes of data in:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usec')
    file.close()

