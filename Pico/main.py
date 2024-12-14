'''
This software is made available for use under the GNU General Public License (GPL).
A copy of this license is available within the repository for this software and is
included herein by reference.
'''

import machine
import utime

import os
import sys
import random
import helpers
import gc

# Constants for port types
DIGITAL = 1
PWM = 2

# Constants for control data file format
CSV = 5
HEX = 6     # No longer used
BIN = 7

firstTime = True    # Flag to prevent idle animation running until started

verbose=False
                # Analysis of memory usage severely affects timing data so keep that in mind
memuse = 0      # 0 = no memory usage stats, 1 = garbage collection count, 2 = debug memuse printing

# LED specifications
# Use the on board LED for status
led_onboard = machine.Pin(25, machine.Pin.OUT)
# Use the off board LED for status too
led_offboard = machine.Pin(26, machine.Pin.OUT)

# Button specifications
# Pin 24 is the onboard USR button on some Pico clones - Do Not Use
# Pin 27 is the opto-isolated Trigger 2 for external stimuli
trigger2 = machine.Pin(27, machine.Pin.IN, machine.Pin.PULL_UP)
trigger2_laststate = True   # True indicates NOT pressed

def opto_button_pressed():
    global trigger2_laststate
    if trigger2.value() != trigger2_laststate:
        utime.sleep_ms(50)    # Debounce switch
        if trigger2.value() != trigger2_laststate:
            trigger2_laststate = trigger2.value()
    return not trigger2_laststate

# Pin 28 is the Trigger 1 button connected to external jumper connector
trigger1 = machine.Pin(28, machine.Pin.IN, machine.Pin.PULL_UP)
trigger1_laststate = True   # True indicates NOT pressed

def button_pressed():
    global trigger1_laststate
    if trigger1.value() != trigger1_laststate:
        utime.sleep_ms(50)    # Debounce switch
        if trigger1.value() != trigger1_laststate:
            trigger1_laststate = trigger1.value()
    return not trigger1_laststate

def toggle_LEDs():
    led_onboard.toggle()
    led_offboard.toggle()

def on_LEDs():
    led_onboard.on()
    led_offboard.on()

def do_the_thing(animList, idleanimation=None, randomize=False, continuous=False, skip=False, doOnce=False):
    global firstTime

    helpers.setAllDigital(0)    # All digital channels off
    helpers.releaseAllServos()  # All servos relaxed

    # Don't bother with anything if list of animations is empty
    playIndex = 0
    msecPerBlink = 1000    # We will flash at 0.5Hz if we have animations available and 5 Hz if not
    if len(animList) > 0:
        if randomize: playIndex = random.randint(0, len(animList)-1)
    else:
        msecPerBlink = 100
    if verbose: print(animList)

    # Swallow strange initially pressed state
    while button_pressed() or opto_button_pressed():
        utime.sleep_ms(100)

    # Turn off all our status LEDs so they are always synced
    led_onboard.off()
    led_offboard.off()

    # if skip is True then immediately begin execution
    # if continuous is True then execute continuously until interrupted
    # Else Blink at 0.5Hz until button is pressed
    while True:
        # Toggle LED every second until button pressed
        if not continuous and not skip:
            while not button_pressed() and not opto_button_pressed():
                if idleanimation is not None and not firstTime:
                    play_one_anim(idleanimation[0], idleanimation[1])
                code = 0
                toggle_LEDs()
                for i in range(msecPerBlink):
                    if helpers.isThereInput():
                        code = helpers.handleInput()
                        if code == 1: break
                    else:
                        utime.sleep_ms(1)
                    if button_pressed():
                        break
                    if opto_button_pressed():
                        break
                if code == 1: break

            # Wait up to 5 seconds for button to be released
            on_LEDs()
            for i in range(100):
                utime.sleep_ms(50)
                if not button_pressed():
                    break

        # If button is STILL pressed, go into continuous loop mode
        if button_pressed():
            # Blink LED at 10 Hz until button released
            while True:
                toggle_LEDs()
                utime.sleep_ms(100)
                if not button_pressed():
                    break
            continuous = True

        if playIndex < len(animList):
            firstTime = False
            # Get next animation to play
            if verbose: print('Print playing animation:', playIndex,'named:',animList[playIndex][0])
            # Play it
            play_one_anim(animList[playIndex][0], animList[playIndex][1])

        # Revert to normal operations
        skip = False

        if doOnce: break

        # Check to see if button is pressed and quit if so
        if button_pressed():
            if verbose: print('Caught Stop button')
            # Stop running continuous mode on button press also
            continuous = False
            # Wait for button release
            while button_pressed():
                utime.sleep_ms(100)

        if len(animList) > 0:
            # Go to next anim in list
            playIndex += 1
            if playIndex >= len(animList): playIndex = 0
            if randomize: playIndex = random.randint(0, len(animList)-1)

        if(verbose): print('At end of loop')

    # Currently no way to get here
    if(verbose): print('At end of do_the_thing()')

class LocalSource:
    def __init__(self, filename=None, binblocksize=0, readlock=None):
        self.file = None
        self.binblocksize = binblocksize
        self.readlock = readlock
        if self.readlock: self.readlock.acquire()
        if binblocksize > 0:
            self.file = open(filename, 'rb')
        else:
            self.file = open(filename, 'r')
        if self.readlock: self.readlock.release()

    def readline(self, returnblock=None):
        BLOCKSIZE = 512  # Don't read more than 512 bytes per read
        if self.file is None: return ''
        if self.readlock: self.readlock.acquire()
        if self.binblocksize > 0:
            if returnblock is None:
                returnblock = bytearray(self.binblocksize)
            mv = memoryview(returnblock)
            bytes_read = 0
            n = self.binblocksize
            for i in range(0, n - BLOCKSIZE, BLOCKSIZE):
                bytes_read += self.file.readinto(mv[i:i + BLOCKSIZE])
            if bytes_read < n:
                bytes_read += self.file.readinto(mv[bytes_read:n])
            if bytes_read == 0:
                # At end of file
                return ''
        else:
            returnblock = self.file.readline()
        if self.readlock: self.readlock.release()
        return returnblock

    def close(self):
        if self.file is not None:
            self.file.close()
            self.file = None


def play_one_anim(csvfile, wavefile, idle=False):
    # Initially assume ascii file format
    binblocksize = 0

    # Get expected binary file block sizes just in case
    blockSizes = helpers.tables.getBinarysizes()

    boardlist = helpers.tables.boardList()
    if verbose:
        for board in boardlist:
            print('Board ID:', board.pca9685.address, 'First port:', board.firstport, 'First byte:', board.firstport+blockSizes[1]+blockSizes[2])

    # Get the list of PWMs on GPIO pins
    pwmlist = helpers.tables.pwmList()
    if verbose:
        for port in pwmlist:
            print('PWM Port:', port, 'is on a GPIO pin')

    # Sample the control file to see what format it is in
    try:
        with open(csvfile, 'rb') as source:
            testbyte = source.read(1)
            if testbyte == b'T':
                # Ascii CSV file
                csvformat = CSV
                pass
            elif testbyte == b'0':
                # ASCII hex-encoded file
                csvformat = HEX
                print('Whoops - HEX format no longer supported!!')
                pass
            elif testbyte == b'\x00':
                # Binary encoded file
                csvformat = BIN
                binblocksize = blockSizes[0]
                pass
            else:
                # bad
                if verbose: print('Whoops - Unrecognized control file format:', csvfile)
                return
    except:
        if verbose: print('Whoops - Unable to open and read control file:', csvfile)
        # Continue on for case of csvfile is None
        csvfile = None

    # Create the player
    player = None   # Set player to None so later we know if it exists
    if helpers.isfile(wavefile):
        player = helpers.WavePlayer(wavefile, csvfilename=csvfile, binblocksize=binblocksize, verbose=(0 if not verbose else 1))


    # Open the default CSV file if there is no player
    source = None
    if helpers.isfile(csvfile):
        if player is None:
            source = LocalSource(csvfile, binblocksize)
        else:
            source = player

    if source is not None:
        if verbose: print('Playing animation file:', csvfile)
        if csvformat == CSV:
            # Read the first line to get ports
            hdr = source.readline()
            if verbose: print('Processing header:', hdr)
            titles = hdr.split(',')
            ports = [None]      # No port for frame column
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
        elif csvformat == BIN:
            # Get information from tables
            pass


    # Initialize stats for optional display
    setTicks = 0
    digTicks = 0
    servoTicks = 0
    servoCount = 0
    lockTicks = 0
    skips = 0
    readTicks = 0
    splitTicks = 0
    dataTicks = 0
    servodataTicks = 0
    buttonTicks = 0
    garbageTicks = 0
    LEDTicks = 0
    maxCycleTicks = 0

    # Temporary ticks
    ticks1 = 0
    ticks2 = 0
    ticks3 = 0
    ticks4 = 0
    ticks5 = 0

    if memuse > 0:
        memused = gc.mem_alloc()

    # Start the audio playing whether there is a CSV file or not
    if verbose: print('Playing file:', wavefile)
    if player is not None: player.play()

    if source:
        # Get the current time
        startTicks = utime.ticks_ms()

        # Gather waittime stats
        waitTime = 0

        # Get first line of real data
        if csvformat == CSV:
            line = source.readline()
        elif csvformat == BIN:
            line = source.readline()

        # Run animatronics until done or button is pressed
        # Parse the line
        ticks1 = utime.ticks_us()
        if csvformat == CSV:
            values = line.split(',')   # Initial split
            nextTicks = int(values[0])
        elif csvformat == BIN:
            nextTicks = int.from_bytes(line[0:4], 'little')
        splitTicks += utime.ticks_diff(utime.ticks_us(), ticks1)

        collectioncount = 0
        loopTicks = utime.ticks_us()
        while len(line) > 0:
            #if verbose: print('Processing line:', line)
            if memuse > 1:
                print('At loop start, memory use:', gc.mem_alloc())
            cycleTicks = utime.ticks_us()
            # Wait until it is 20msec before time to go to next state
            while(utime.ticks_diff(utime.ticks_ms(), startTicks) < nextTicks - 20):
                utime.sleep_ms(1)
                waitTime += 1
            if memuse > 1:
                print('After loop wait, memory use:', gc.mem_alloc())

            # Send all values in the row to the Pins
            #if verbose: print('Sending data at time:',utime.ticks_diff(utime.ticks_ms(), startTicks), 'which should be:', nextTicks)
            ticks1 = utime.ticks_us()
            if csvformat == BIN:
                boardstart = blockSizes[1] + blockSizes[2]
                for board in boardlist:
                    board.pca9685.jambytes(line[board.firstport*4+boardstart:board.firstport*4+boardstart+board.numbytes])
                if memuse > 1:
                    print('After jambytes, memory use:', gc.mem_alloc())
                # Now process all the PWMs on GPIO pins
                for port in pwmlist:
                    addr = port*4 + blockSizes[1] + blockSizes[2]
                    helpers.tables.dosomething(port, line[addr+2:addr+4])
                servodataTicks += utime.ticks_diff(utime.ticks_us(), ticks1)
                if memuse > 1:
                    print('After servos, memory use:', gc.mem_alloc())
                bits = int.from_bytes(line[blockSizes[1]:blockSizes[1] + blockSizes[2]], 'little')
                helpers.tables.intToDigital(bits)
                if memuse > 1:
                    print('After intToDigital, memory use:', gc.mem_alloc())
                helpers.tables.outputDigital()
                if memuse > 1:
                    print('After outputDigital, memory use:', gc.mem_alloc())
                setTicks += utime.ticks_diff(utime.ticks_us(), ticks1)
                servoCount += 1
                pass
            else:
                for i in range(1,len(titles)):
                    if porttypes[i] is not None:
                        if porttypes[i] == DIGITAL:
                            # Must be a digital channel
                            #if verbose: print('Channel', ports[i],'is DIGITAL')
                            if csvformat == CSV:
                                value = int(values[i])
                            if ports[i] >= 0:
                                # Nonnegative ports go directly to that port
                                ticks2 = utime.ticks_us()
                                helpers.setDigital(ports[i], value)
                                dataTicks += utime.ticks_diff(utime.ticks_us(), ticks2)
                                #if verbose: print('Setting digital port:', ports[i], 'to:', value)
                            else:
                                # Negative port indicates compacted controls in a single value
                                ticks2 = utime.ticks_us()
                                helpers.tables.intToDigital(value)
                                dataTicks += utime.ticks_diff(utime.ticks_us(), ticks2)
                        elif porttypes[i] == PWM:
                            #if verbose: print('Channel', ports[i],'is PWM')
                            if ports[i] >= 0:
                                value = int(values[i])
                                # Nonnegative ports go directly to that port
                                ticks2 = utime.ticks_us()
                                helpers.setServo(ports[i], value, push=False)
                                servodataTicks += utime.ticks_diff(utime.ticks_us(), ticks2)
                            else:
                                # Negative port indicates compacted controls in a single value
                                ticks2 = utime.ticks_us()
                                if csvformat == CSV:
                                    value = int(values[i])
                                    vals = []
                                    port = 0
                                    for port in range(32):
                                        vals.append(value & 0xFFFF)
                                        value >>= 16
                                    helpers.tables.intsToPWM(vals)
                                servodataTicks += utime.ticks_diff(utime.ticks_us(), ticks2)
                setTicks += utime.ticks_diff(utime.ticks_us(), ticks1)

                # Make sure all the digital channels are output
                ticks1 = utime.ticks_us()
                helpers.outputDigital()
                digTicks += utime.ticks_us() - ticks1

                # Push out all the servo values as well
                ticks1 = utime.ticks_us()
                helpers.pushServos()
                servoTicks += utime.ticks_us() - ticks1
                servoCount += 1

            # Check to see if button is pressed and quit if so
            ticks1 = utime.ticks_us()
            if button_pressed():
                if verbose: print('Caught Stop button')
                break
            if idle and opto_button_pressed():
                if verbose: print('Caught Trigger 2 so interrupting idle animation')
                break
            buttonTicks += utime.ticks_us() - ticks1

            # Toggle LED to let us know something is happening
            ticks1 = utime.ticks_us()
            toggle_LEDs()
            LEDTicks += utime.ticks_us() - ticks1

            # Read another line from CSV file
            ticks1 = utime.ticks_us()
            if csvformat == CSV:
                line = source.readline()
            elif csvformat == BIN:
                line = source.readline(line)
            # If our time is already past the next time, continue reading
            while len(line) > 0:
                ticks2 = utime.ticks_us()
                if csvformat == CSV:
                    values = line.split(',')
                    nextTicks = int(values[0])
                    splitTicks += utime.ticks_diff(utime.ticks_us(), ticks2)
                elif csvformat == BIN:
                    nextTicks = int.from_bytes(line[0:4], 'little')
                    splitTicks += utime.ticks_diff(utime.ticks_us(), ticks2)
                if nextTicks >= utime.ticks_diff(utime.ticks_ms(), startTicks): break
                skips += 1
                if csvformat == CSV:
                    line = source.readline()
                elif csvformat == BIN:
                    line = source.readline(line)
            readTicks += utime.ticks_diff(utime.ticks_us(), ticks1)

            if memuse > 0:
                memnow = gc.mem_alloc()
                if memused > memnow:
                    memused = memnow
                    collectioncount += 1
            if memuse > 1:
                ticks1 = utime.ticks_us()
                print('At time:', nextTicks, 'Memory use:', gc.mem_alloc())
                #gc.collect()
                garbageTicks += utime.ticks_diff(utime.ticks_us(), ticks1)

            cycleTicks = utime.ticks_diff(utime.ticks_us(), cycleTicks)
            if cycleTicks > maxCycleTicks: maxCycleTicks = cycleTicks

        # Compute how much time it took to perform the entire animation
        loopTime = utime.ticks_diff(utime.ticks_us(), loopTicks)

        # If source is a local file then close it but not if it is the audio player
        if source != player: source.close()

        if(verbose): print('At end of read file loop')

        # Optionally report stats
        if(verbose):
            print('-------------------------------------------------------------------')
            print('General statistics')
            print('Total time:', utime.ticks_diff(utime.ticks_ms(), startTicks), 'msec')
            print('Wait time :', waitTime, 'msec')
            print('Duration  :', nextTicks, 'msec')
            print('Wait frac :', waitTime/nextTicks)
            print('Read time :', readTicks, 'usec')
            print('Cycles    :', servoCount+skips)
            print('Skip count:', skips)
            print('Processed :', servoCount)
            print('-------------------------------------------------------------------')

            print('Detailed statistics')
            if memuse > 0:
                print('Garbage collection was run about:', collectioncount, 'times')
            if memuse > 1:
                print('Used', garbageTicks, 'usec for garbage collection', servoCount+skips, 'times')
                print('For an average of', garbageTicks/(servoCount+skips), 'usec per cycle')
            print('    Processing performed for all', servoCount+skips, 'lines in control file:')
            print('Used', readTicks, 'usec to input the line for an average of', readTicks/(servoCount+skips), 'usec per cycle')
            print('Used', splitTicks, 'usec to split the line for an average of', splitTicks/(servoCount+skips), 'usec per cycle')
            print('Used', buttonTicks, 'usec to read stop button for an average of', buttonTicks/(servoCount+skips),'usec per cycle')
            print('Used', LEDTicks, 'usec to toggle LEDs for an average of', LEDTicks/(servoCount+skips),'usec per cycle')
            print('    Processing performed for', servoCount, 'unskipped lines in control file:')
            print('Used', setTicks, 'usec to read and interpret control values for an average of', setTicks/servoCount,'usec per cycle')
            print('Used', dataTicks, 'usec to save the digital data for an average of', dataTicks/servoCount, 'usec per cycle')
            print('Used', servodataTicks, 'usec to save the servo data for an average of', servodataTicks/servoCount, 'usec per cycle')
            print('Used', servoTicks, 'usec to push to servos for an average of', servoTicks/servoCount, 'usec per cycle')
            print('Used', digTicks, 'usec to shift out digital values for an average of', digTicks/servoCount,'usec per cycle')
            print('-------------------------------------------------------------------')
            print('Key Timing')
            print('Used', loopTime, 'usec to run', (servoCount), 'processed cycles')
            print('For an average of', (loopTime-waitTime*1000)/(servoCount)/1000,'msec per cycle')
            print('Maximum cycle duration:', maxCycleTicks/1000, 'msec')

            #print('Time spent waiting for lock:', lockTicks, 'usec')
            print('-------------------------------------------------------------------')
            print('')


    if player is not None:
        while player.playing():
            # If button is pressed, abort playback
            if button_pressed():
                if verbose: print('Caught Stop button')
                player.stop()
            # Waiting a bit to see if audio is done
            utime.sleep_ms(1)

    # Let all the servos relax
    helpers.releaseAllServos()


def main():
    # Turn on all our status LEDs so they are always synced
    # And to let us know that main actually started
    on_LEDs()

    animList = []
    idler = None
    try:
        animList,idler= helpers.findAnimFiles(dir='/sd/anims')
    except:
        pass

    if len(animList) == 0:
        animList,idler = helpers.findAnimFiles()

    do_the_thing(animList, idleanimation=idler)


if __name__ == "__main__":
    main()
