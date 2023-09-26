# Basic Imports

from machine import I2C, Pin
from servo import Servos
from pca9685 import PCA9685
import utime

############# Servo Code #################################
MaxTotalServos = 16     # Sync this number in Animator Preferences
ServosPerPCA = 16

_pca9685s = [None]*20       # Allow for up to 20 PCA chips (320 servos)
_servoblocks = [None]*20    # Allow for up to 20 PCA chips (320 servos)
_i2c = None

def setServo(index=-1, cycletime=0):
    global _pca9685s, _servoblocks, _i2c

    if index < 0 or index > MaxTotalServos: return

    pcaIndex = int(index/ServosPerPCA)
    pcaAddress = 0x40 + pcaIndex        # Use board 0 for servos 0-15, board 1 for 16-31, ...
    index = index % ServosPerPCA        # Mod index to be within range of board
    if _pca9685s[pcaIndex] is None or _servoblocks[pcaIndex] is None:
        # Must initialize this PCA and block of servos
        if _i2c is None:
            sda = Pin(0)
            scl = Pin(1)
            id = 0
            _i2c = I2C(id=id, sda=sda, scl=scl)
        _pca9685s[pcaIndex] = PCA9685(i2c=_i2c, address=pcaAddress)
        _servoblocks[pcaIndex] = Servos(i2c=_i2c, address=pcaAddress)

    # Now actually set the servo
    _servoblocks[pcaIndex].position(index=index, duty=int(cycletime*4095))

def releaseServo(index=-1):
    if index < 0 or index > MaxTotalServos: return

    pcaIndex = int(index/ServosPerPCA)
    pcaAddress = 0x40 + pcaIndex        # Use board 0 for servos 0-15, board 1 for 16-31, ...
    index = index % ServosPerPCA        # Mod index to be within range of board
    if _pca9685s[pcaIndex] is None or _servoblocks[pcaIndex] is None or _i2c is None: return

    _servoblocks[pcaIndex].release(index=index)

def releaseAllServos():
    for index in range(MaxTotalServos):
        releaseServo(index)

############# Digital Code #################################
MaxTotalDigitalIOs = 8      # Sync this number in Animator Preferences
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

AudioBlockSize = 8192

class WavePlayer:
    def __init__(self, wavefilename):
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
                ibuf=AudioBlockSize)  #  * self.file.getsampwidth() * self.file.getnchannels())

    def scaleAudio(self, inbuf):
        # Bad - Can we even do this - should we?
        if self.file.getsampwidth() == 1:
            fmt = '<b'
        elif self.file.getsampwidth() == 2:
            fmt = '<h'
        coder = struct.Struct(fmt)
        tbuff = struct.unpack(fmt, inbuf)

    def play(self):
        if self.file is None: return
        # Play until done or stopped
        self.stopflag = False
        self.audio_out.irq(self.callback)

        # Read in the first block of audio data
        #print('Ready to read buffer:', self.currbuffer)
        #startTicks = utime.ticks_us()
        self.audiodata[self.currbuffer] = self.file.readframes(int(512/self.file.getsampwidth()/self.file.getnchannels()))
        while len(self.audiodata[self.currbuffer]) < AudioBlockSize:
            self.audiodata[self.currbuffer] += self.file.readframes(int(512/self.file.getsampwidth()/self.file.getnchannels()))
        #print('Time to read block of size:', AudioBlockSize, 'is:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usec')

        # Kick off playback
        self.callback(False)

    def callback(self, junk):
        #print('Entered callback')
        # Check to see if we are stopped
        if self.stopflag: return

        # Fill the other buffer in a separate thread
        self.loadbuffer(1 - self.currbuffer)
        #_thread.start_new_thread(self.loadbuffer, (1 - self.currbuffer,))

        #startTicks = utime.ticks_us()
        # Play one block of audio data from current ping-pong buffer
        #print('Playing block of size:', len(self.audiodata[self.currbuffer]))
        self.audio_out.write(self.audiodata[self.currbuffer])
        #print('Ticks to play block:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usec')
        #self.audiodata[self.currbuffer] = None

        # Read in the next block of audio while the current one is playing
        self.currbuffer = 1 - self.currbuffer   # Read into other ping-pong buffer
        pass

    def loadbuffer(self, buffer):
        #print('Entered thread')
        startTicks = utime.ticks_us()
        tbuff = self.file.readframes(int(512/self.file.getsampwidth()/self.file.getnchannels()))
        self.audiodata[buffer] = tbuff
        while len(tbuff) > 0 and len(self.audiodata[buffer]) < AudioBlockSize:
            tbuff = self.file.readframes(int(512/self.file.getsampwidth()/self.file.getnchannels()))
            self.audiodata[buffer] += tbuff
        if len(self.audiodata[buffer]) == 0:
            self.stopflag = True
            #print('Got no bytes from audio file so stopping')
        print('Ticks to read block:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usec')

    def stop(self):
        # Stop playing
        self.stopflag = True
        pass

    def rewind(self):
        if self.file is None: return
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


############# SD Card Code #################################
import machine
import uos
import sdcard

def mountSDCard(mountpoint='/sd'):
    # Assign chip select (CS) pin (and start it high)
    cs = machine.Pin(17, machine.Pin.OUT)

    # Initialize SPI peripheral (start with 1 MHz)
    spi = machine.SPI(0,
                      baudrate=10000000,
                      polarity=0,
                      phase=0,
                      bits=8,
                      firstbit=machine.SPI.MSB,
                      sck=machine.Pin(18, machine.Pin.OUT),
                      mosi=machine.Pin(19, machine.Pin.OUT),
                      miso=machine.Pin(16, machine.Pin.OUT))

    # Initialize SD card
    sd = sdcard.SDCard(spi, cs)

    # Mount filesystem
    vfs = uos.VfsFat(sd)
    uos.mount(vfs, mountpoint)

def testSDCard(filename):
    file = open(filename, 'rb')
    bytesize = 1
    while bytesize < 300:
        print('Trying to read', bytesize, 'bytes from file:', filename)
        startTicks = utime.ticks_us()
        data = file.read(bytesize)
        print('Actually read:', len(data), 'in:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usec')
        bytesize = bytesize * 2
    while len(data) > 0:
        print('Trying to read', bytesize, 'bytes from file:', filename)
        startTicks = utime.ticks_us()
        data = file.read(bytesize)
        print('Actually read:', len(data), 'in:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usec')
    file.close()

    file = open(filename, 'rb')
    bytesize = 256
    data = file.read(bytesize)
    startTicks = utime.ticks_us()
    while len(data) > 0:
        data = file.read(bytesize)
    print('Actually read data in:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usec')
    file.close()

    file = open(filename, 'rb')
    bytesize = 512
    data = file.read(bytesize)
    startTicks = utime.ticks_us()
    while len(data) > 0:
        data = file.read(bytesize)
    print('Actually read data in:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usec')
    file.close()

