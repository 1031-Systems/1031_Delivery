####################################################################
# onboard.py is a version of the animatronics helpers that uses only
# the Pico pins for control rather than external chips or boards.  It
# also does not use an external SD card but stores all animation data
# in the flash memory.
####################################################################
# Basic Imports

from machine import Pin, PWM
import utime
import binascii

############# Servo Code #################################
MaxTotalServos = 8     # Sync this number in Animator Preferences

servoPWMs = [
    PWM(Pin(17, Pin.OUT)),
    PWM(Pin(18, Pin.OUT)),
    PWM(Pin(19, Pin.OUT)),
    PWM(Pin(20, Pin.OUT)),
    PWM(Pin(21, Pin.OUT)),
    PWM(Pin(22, Pin.OUT)),
    PWM(Pin(26, Pin.OUT)),
    PWM(Pin(27, Pin.OUT)),
    ]

def setServo(index=-1, cycletime=0):
    global _pca9685s, _servoblocks, _i2c

    if index < 0 or index >= MaxTotalServos: return

    servoPWMs[index].freq(50)
    servoPWMs[index].duty_u16(cycletime)

def releaseServo(index=-1):
    if index < 0 or index >= MaxTotalServos: return

    servoPWMs[index].duty_u16(0)

def releaseAllServos():
    for index in range(MaxTotalServos):
        releaseServo(index)

############# Digital Code #################################
MaxTotalDigitalIOs = 12      # Sync this number in Animator Preferences

digitalPins = [
    Pin(0, Pin.OUT),
    Pin(1, Pin.OUT),
    Pin(2, Pin.OUT),
    Pin(3, Pin.OUT),
    Pin(4, Pin.OUT),
    Pin(6, Pin.OUT),
    Pin(8, Pin.OUT),
    Pin(12, Pin.OUT),
    Pin(13, Pin.OUT),
    Pin(14, Pin.OUT),
    Pin(15, Pin.OUT),
    Pin(16, Pin.OUT),
    ]

_digitalCurrentState = [0]*MaxTotalDigitalIOs

def setDigital(index=-1, value=0, show=False):
    if index < 0 or index >= MaxTotalDigitalIOs: return

    _digitalCurrentState[index] = value

    if show:    # Immediately set output
        outputDigital()

def outputDigital():
    for i in range(MaxTotalDigitalIOs):
        if _digitalCurrentState[i] > 0:
            digitalPins[i].on()
        else:
            digitalPins[i].off()

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
                ibuf=AudioBlockSize)

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
        if self.verbose: print('Running play() in thread', _thread.get_ident())
        # Play until done or stopped
        self.stopflag = False
        # Kick off playback in a new thread
        _thread.start_new_thread(self.threadplay, (False,))

    def playing(self):
        return not self.stopflag

    def threadplay(self, dummy):
        # Initialize statistics
        self.startTicks = utime.ticks_us()
        self.sumuploadticks = 0
        self.sumreadfileticks = 0
        self.suspendedticks = 0
        self.blocksplayed = 0
        # Play until end of data or stopped
        while not self.stopflag: self.playblock(False)

    def playblock(self, junk):
        #print('Entered playblock')
        # Check to see if we are stopped
        if self.stopflag: return
        if self.verbose: print('Running playblock() in thread', _thread.get_ident())

        # Fill the buffer prior to playing
        startTicks = utime.ticks_us()
        self.loadbuffer(self.currbuffer)
        self.sumreadfileticks += utime.ticks_diff(utime.ticks_us(), startTicks)

        # Play one block of audio data from current ping-pong buffer
        startTicks = utime.ticks_us()
        self.audio_out.write(self.audiodata[self.currbuffer])
        totaluploadticks = utime.ticks_diff(utime.ticks_us(), startTicks)
        if self.firstuploadticks == 0:
            self.firstuploadticks = totaluploadticks
        self.sumuploadticks += totaluploadticks
        totaluploadticks -= self.firstuploadticks
        self.suspendedticks += totaluploadticks
        self.blocksplayed += 1


    def loadbuffer(self, buffer):
        #print('Entered thread')
        startTicks = utime.ticks_us()
        tbuff = self.file.readframes(self.blockframes)
        self.audiodata[buffer] = tbuff
        while len(tbuff) > 0 and len(self.audiodata[buffer]) < AudioBlockSize:
            tbuff = self.file.readframes(self.blockframes)
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


################ USB data transfer code ###############################################
import select
import sys

# Create object for communicating over USB
inpoll = select.poll()
inpoll.register(sys.stdin.buffer, select.POLLIN)

def logstring(instring):
    return  # Disabled
    logfile = open('/log', 'a')
    count = logfile.write(instring + '\n')
    logfile.close()

def isThereInput():
    result = inpoll.poll(0)
    return len(result) > 0

def handleInput():
    inline = sys.stdin.buffer.readline().decode('utf-8')
    logstring('Received:' + inline)
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
            setServo(channel, value)
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
            #logstring('Received:' + str(len(line)) + ' bytes of ' + str(fsize) + ' remaining')
            #logstring(str(fsize))
            while fsize > 0:
                bwritten = file.write(binascii.unhexlify(line))
                fsize -= len(line)
                if fsize > 0: line = sys.stdin.buffer.read(min(fsize, 512))
                #logstring(str(fsize))
            logstring('Closing file')
            file.close()
        except:
            # sys.stderr.write('\nWhoops - Unable to write file %d\n' % filename)
            pass
    return 0


