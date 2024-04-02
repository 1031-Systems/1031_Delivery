# Basic Imports

from machine import I2C, Pin
from servo import Servos
from pca9685 import PCA9685
import utime
import binascii

############# Servo Code #################################
MaxTotalServos = 32     # Sync this number in Animator Preferences
ServosPerPCA = 16       # Must be power of 2

servoShift = 4          # log2 of ServosPerPCA
servoMod = ServosPerPCA - 1

_servoblocks = [None]*20    # Allow for up to 20 PCA chips (320 servos)
_i2c = None

def setServo(index=-1, cycletime=0, push=True):
    global _servoblocks, _i2c

    if index < 0 or index > MaxTotalServos: return

    pcaIndex = index >> servoShift
    pcaAddress = 0x40 + pcaIndex        # Use board 0 for servos 0-15, board 1 for 16-31, ...
    index = index & servoMod            # Mod index to be within range of board
    if _servoblocks[pcaIndex] is None:
        # Must initialize this PCA and block of servos
        if _i2c is None:
            sda = Pin(0, pull=Pin.PULL_UP)
            scl = Pin(1, pull=Pin.PULL_UP)
            id = 0
            _i2c = I2C(id=id, sda=sda, scl=scl, freq=1048576)   # Use 1MHz as that is max for pca9685
        _servoblocks[pcaIndex] = Servos(i2c=_i2c, address=pcaAddress)

    # Now actually set the servo
    _servoblocks[pcaIndex].position(index=index, duty=cycletime, push=push)

def releaseServo(index=-1):
    if index < 0 or index > MaxTotalServos: return

    pcaIndex = index >> servoShift
    pcaAddress = 0x40 + pcaIndex        # Use board 0 for servos 0-15, board 1 for 16-31, ...
    index = index & servoMod            # Mod index to be within range of board
    if _servoblocks[pcaIndex] is None or _i2c is None: return

    _servoblocks[pcaIndex].release(index=index)

def releaseAllServos():
    for index in range(MaxTotalServos):
        releaseServo(index)

def pushServos():
    for i in range(20):
        if _servoblocks[i] is not None: _servoblocks[i].pushValues()

############# Digital Code #################################
MaxTotalDigitalIOs = 24      # Sync this number in Animator Preferences
DigitalIOsPer595 = 8
DigitalDataPin = 26
DigitalClockPin = 27
DigitalRclkPin = 21
DigitalClearPin = 20

_digitalCurrentState = [0]*MaxTotalDigitalIOs

def setDigital(index=-1, value=0, show=False):
    if index < 0 or index >= MaxTotalDigitalIOs: return

    _digitalCurrentState[index] = value

    if show:    # Immediately set output
        outputDigital()

def outputDigital():
    # Define the pins
    dataPin = Pin(DigitalDataPin, Pin.OUT)
    clockPin = Pin(DigitalRclkPin, Pin.OUT)
    shiftPin = Pin(DigitalClockPin, Pin.OUT)
    clearPin = Pin(DigitalClearPin, Pin.OUT)
    clearPin.on() # No want clearing here

    # Cycle the digital state thru all the 74HC595 chips
    for i in range(MaxTotalDigitalIOs):
        # Put the value on the data pin, msb first
        value = _digitalCurrentState[MaxTotalDigitalIOs - i - 1]
        if value > 0.5:
            dataPin.on()
        else:
            dataPin.off()
        shiftPin.on()
        shiftPin.off()

    # Clock all the bits to the outputs
    clockPin.on()
    clockPin.off()

def setAllDigital(invalue):
    for i in range(MaxTotalDigitalIOs):
        _digitalCurrentState[i] = invalue
    outputDigital()

############# Wave File Player ################################
import wave
from machine import I2S
import _thread

I2SDataPin = 9
I2SBitClockPin = 10
I2SChannelPin = 11
PicoAudioEnablePin = 22

AudioBlockSize = 1024

class WavePlayer:
    def __init__(self, wavefilename, verbose=False):
        self.verbose = verbose
        self.filename = wavefilename
        try:
            self.file = wave.open(self.filename)
        except:
            self.file = None
            return
        self._volume = 0.5

        # Set up ping-pong audio buffers
        self.audiodata = [None] * 2
        self.currbuffer = 0

        # Initialize stats
        self.firstuploadticks = 0
        self.startTicks = 0
        self.sumuploadticks = 0
        self.sumreadfileticks = 0
        self.suspendedticks = 0
        self.blocksplayed = 0

        # Compute number of frames in a 512-byte block
        self.blockframes = int(512/self.file.getsampwidth()/self.file.getnchannels())

        # Stop Flag set to not play initially
        self.stopflag = True

        # Set up pins for I2S
        datapin = Pin(I2SDataPin, Pin.OUT)
        bitclockpin = Pin(I2SBitClockPin, Pin.OUT)
        channelpin = Pin(I2SChannelPin, Pin.OUT)
        unmutepin = Pin(PicoAudioEnablePin, Pin.OUT)

        # Turn the player on
        unmutepin.on()

        # Create the audio out channel over I2S
        self.audio_out = I2S(1,
                sck=bitclockpin, ws=channelpin, sd=datapin,
                mode=I2S.TX,
                bits=self.file.getsampwidth() * 8,
                format=(I2S.MONO if self.file.getnchannels() == 1 else I2S.STEREO),
                rate=self.file.getframerate(),
                ibuf=AudioBlockSize*8)

        # Create a semaphore lock for outside reads to avoid interfering with reads in this thread
        self.readLock = _thread.allocate_lock()

    def play(self):
        if self.file is None: return
        if self.verbose: print('Running play() in thread', _thread.get_ident())
        # Play until done or stopped
        self.stopflag = False
        # Kick off playback in a new thread
        _thread.start_new_thread(self.threadplay, (False,))

    def threadplay(self, dummy):
        if self.verbose: print('Running threadplay() in thread', _thread.get_ident())
        # Initialize statistics
        self.startTicks = utime.ticks_us()
        self.sumuploadticks = 0
        self.sumreadfileticks = 0
        self.suspendedticks = 0
        self.blocksplayed = 0

        # Read in first buffer so we are ready to play
        self.loadbuffer(self.currbuffer)

        # Play until end of data or stopped
        while not self.stopflag: self.playblock(False)

    def playblock(self, junk):
        #print('Entered playblock')
        # Check to see if we are stopped
        if self.stopflag: return
        #if self.verbose: print('Running playblock() in thread', _thread.get_ident())

        # Play one block of audio data from current ping-pong buffer
        startTicks = utime.ticks_us()
        self.audio_out.write(self.audiodata[self.currbuffer])
        totaluploadticks = utime.ticks_diff(utime.ticks_us(), startTicks)
        if self.verbose: print('Ticks to write block to i2s', totaluploadticks)
        if self.firstuploadticks == 0:
            self.firstuploadticks = totaluploadticks
        self.sumuploadticks += totaluploadticks
        totaluploadticks -= self.firstuploadticks
        self.suspendedticks += totaluploadticks
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
        tbuff = self.file.readframes(self.blockframes)
        self.readLock.release()
        self.audiodata[buffer] = tbuff
        while len(tbuff) > 0 and len(self.audiodata[buffer]) < AudioBlockSize:
            self.readLock.acquire()
            tbuff = self.file.readframes(self.blockframes)
            self.readLock.release()
            self.audiodata[buffer] += tbuff
        if len(self.audiodata[buffer]) == 0:
            self.stop()
            #print('Got no bytes from audio file so stopping')
        if self.verbose: print('Ticks to read block:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usec')

    def stop(self):
        # Stop playing
        self.stopflag = True
        # Dump statistics
        if self.verbose:
            print('Total time spent reading file data:', self.sumreadfileticks, 'usec')
            print('Time spent uploading first block  :', self.firstuploadticks, 'usec')
            print('Total time spent uploading data   :', self.sumuploadticks, 'usec')
            print('Total estimated time suspended    :', self.suspendedticks, 'usec')
            print('Total time                        :', utime.ticks_diff(utime.ticks_us(), self.startTicks), 'usec')
            print('Total audio played                :', self.blocksplayed * self.blockframes * 1000000 * AudioBlockSize / 512 / self.file.getframerate(), 'usec')
        pass

    def rewind(self):
        if self.file is None: return
        if not self.stopflag: self.stop()
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
        return not self.stopflag



############# SD Card Code #################################
import machine
import uos
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
    spi.init(baudrate=40000000)

    # Mount filesystem
    vfs = uos.VfsFat(sd)
    uos.mount(vfs, mountpoint)

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
        except:
            # sys.stderr.write('\nWhoops - Unable to write file %d\n' % filename)
            pass
    return 0

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

