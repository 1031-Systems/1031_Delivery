import machine
try:
    import utime
except:
    import time as utime

import os
import sys
import random
import helpers

# Constants for port types
DIGITAL = 1
SERVO = 2

verbose=False

# Use the on board LED for status
led_onboard = machine.Pin(25, machine.Pin.OUT)
# Use the off board LED for status too
led_offboard = machine.Pin(26, machine.Pin.OUT)

# Pin 24 is the onboard USR button on some Pico clones
button = machine.Pin(24, machine.Pin.IN, machine.Pin.PULL_UP)
# Pin 28 is the RUN button connected to external jumper connector
runbutton = machine.Pin(28, machine.Pin.IN, machine.Pin.PULL_UP)

def button_pressed():
    return (not button.value()) or (not runbutton.value())

def toggle_LEDs():
    led_onboard.toggle()
    led_offboard.toggle()

def on_LEDs():
    led_onboard.on()
    led_offboard.on()

def isfile(testfile):
    try:
        size = os.stat(testfile)[6]
        return size > 0
    except:
        return False

def findAnimFiles(dir='/anims'):
    # Find animation files
    # Create empty list of csv/audio file pairs
    animList = []
    # Force directory to have '/' at the end
    if dir[-1] != '/': dir += '/'

    # Check for an existing list of files
    if isfile(dir + 'animlist'):
        infile = open(dir + 'animlist', 'r')
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
                if isfile(names[0] + '.csv'):
                    tpair.append(names[0] + '.csv')
                elif isfile(dir + names[0] + '.csv'):
                    tpair.append(dir + names[0] + '.csv')
                else:
                    tpair.append(None)
                if isfile(names[0] + '.wav'):
                    tpair.append(names[0] + '.wav')
                elif isfile(dir + names[0] + '.wav'):
                    tpair.append(dir + names[0] + '.wav')
                else:
                    tpair.append(None)
                animList.append(tpair)
            line = infile.readline()
    else:
        # Check for matching filename pairs
        if isfile(dir):
            filelist = os.listdir(dir)
            for filename in filelist:
                tpair = []
                if filename[-4:] == '.csv':
                    tpair.append(dir + filename)
                    tname = filename[:-4] + '.wav'
                    if tname in filelist:
                        tpair.append(dir + tname)
                        animList.append(tpair)
            # May want nonmatching filenames as well


    if len(animList) == 0:
        # Try looking for data.csv and data.wav
        # Attempt to mount an SD card if not done in boot.py (preferred)
        try:
            helpers.mountSDCard()       # Mount SD card for all data files
        except:
            # Ignore errors
            pass

        if isfile('/sd/data.csv'):
            datafile = '/sd/data.csv'
        elif isfile('/data.csv'):
            datafile = '/data.csv'
        else:
            datafile = None

        # Find the preferred audio file on the SD card or in flash
        if isfile('/sd/data.wav'):
            wavefile = '/sd/data.wav'
        elif isfile('/data.wav'):
            wavefile = '/data.wav'
        else:
            wavefile = None

        if datafile is not None or wavefile is not None:
            animList.append([datafile, wavefile])

    return animList

def do_the_thing(animList, randomize=False, continuous=False, skip=False, doOnce=False):

    helpers.setAllDigital(0)    # All digital channels off
    helpers.releaseAllServos()  # All servos relaxed

    # Don't bother with anything if list of animations is empty
    playIndex = 0
    if len(animList) > 0:
        if randomize: playIndex = random.randint(0, len(animList)-1)
    else:
        return
    if verbose: print(animList)

    # Swallow strange initially pressed state
    while button_pressed():
        utime.sleep_ms(1000)
        button_pressed()

    # Turn off all our status LEDs so they are always synced
    led_onboard.off()
    led_offboard.off()

    # if skip is True then immediately begin execution
    # if continuous is True then execute continuously until interrupted
    # Else Blink at 0.5Hz until button is pressed
    while True:
        # Toggle LED every second until button pressed
        if not continuous and not skip:
            while not button_pressed():
                code = 0
                toggle_LEDs()
                for i in range(100):
                    if helpers.isThereInput():
                        code = helpers.handleInput()
                        if code == 1: break
                    utime.sleep_ms(10)
                    if button_pressed():
                        utime.sleep_ms(50)  # Debounce switch
                        if button_pressed(): break
                if code == 1: break

            # Wait up to 5 seconds for button to be released
            on_LEDs()
            for i in range(100):
                utime.sleep_ms(50)
                if not button_pressed():
                    utime.sleep_ms(50)    # Debounce switch
                    if not button_pressed(): break

        # If button is STILL pressed, go into continuous loop mode
        if button_pressed():
            # Blink LED at 10 Hz until button released
            while True:
                toggle_LEDs()
                utime.sleep_ms(100)
                if not button_pressed():
                    utime.sleep_ms(50)    # Debounce switch
                    if not button_pressed(): break
            continuous = True

        if playIndex < len(animList):
            # Get next animation to play
            if verbose: print('Print playing animation:', playIndex,'named:',animList[playIndex][0])
            # Play it
            play_one_anim(animList[playIndex][0], animList[playIndex][1])

        # Revert to normal operations
        skip = False

        if doOnce: break

        # Check to see if button is pressed and quit if so
        if button_pressed():
            utime.sleep_ms(50)    # Debounce switch
            if button_pressed():
                if verbose: print('Caught Stop button')
                # Stop running continuous mode on button press also
                continuous = False
                # break     # If we break here we terminate everything
                # Wait for button release
                while button_pressed():
                    utime.sleep_ms(50)    # Debounce switch
                    if not button_pressed(): break

        if len(animList) > 0:
            # Go to next anim in list
            playIndex += 1
            if playIndex >= len(animList): playIndex = 0
            if randomize: playIndex = random.randint(0, len(animList)-1)

        if(verbose): print('At end of loop')

    if(verbose): print('At end of do_the_thing()')

    # Reset the machine to clear out other thread and allow easier rshell access
    machine.reset()

def play_one_anim(csvfile, wavefile):
    # Create the player
    player = None   # Set player to None so later we know if it exists
    if isfile(wavefile):
        player = helpers.WavePlayer(wavefile, csvfilename=csvfile, verbose=(0 if not verbose else 1))

    # Open the default CSV file if there is no player
    source = None
    if isfile(csvfile):
        if player is None:
            source = open(csvfile, 'r')
        else:
            source = player

    if source is not None:
        if verbose: print('Playing animation file:', csvfile)
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
                porttypes[i] = SERVO

    # Initialize stats for optional display
    setTicks = 0
    digTicks = 0
    servoTicks = 0
    servoCount = 0
    lockTicks = 0
    skips = 0
    readTicks = 0
    splitTicks = 0

    # Start the audio playing whether there is a CSV file or not
    if verbose: print('Playing file:', wavefile)
    if player is not None: player.play()

    if source:
        # Get the current time
        startTicks = utime.ticks_ms()

        # Gather waittime stats
        waitTime = 0

        # Get first line of real data
        line = source.readline()

        # Run animatronics until done or button is pressed
        loopTicks = utime.ticks_us()
        # Parse the line
        tTicks = utime.ticks_us()
        values = line.split(',')
        splitTicks += utime.ticks_diff(utime.ticks_us(), tTicks)

        while len(line) > 0:
            #if verbose: print('Processing line:', line)
            # Wait until it is time to go to next state
            nextTicks = int(values[0])
            while(utime.ticks_diff(utime.ticks_ms(), startTicks) < nextTicks):
                utime.sleep_ms(1)
                waitTime += 1

            # Send all values in the row to the Pins
            #if verbose: print('Sending data at time:',utime.ticks_diff(utime.ticks_ms(), startTicks), 'which should be:', nextTicks)
            ticks1 = utime.ticks_us()
            for i in range(1,len(titles)):
                if porttypes[i] is not None:
                    if porttypes[i] == DIGITAL:
                        # Must be a digital channel
                        #if verbose: print('Channel', ports[i],'is DIGITAL')
                        value = int(values[i])
                        if ports[i] >= 0:
                            # Nonnegative ports go directly to that port
                            helpers.setDigital(ports[i], value)
                            #if verbose: print('Setting digital port:', ports[i], 'to:', value)
                        else:
                            # Negative port indicates compacted controls in a single value
                            helpers.tables.intToDigital(int(values[i]))
                    elif porttypes[i] == SERVO:
                        #if verbose: print('Channel', ports[i],'is SERVO')
                        value = int(values[i])
                        if ports[i] >= 0:
                            # Nonnegative ports go directly to that port
                            helpers.setServo(ports[i], value, push=False)
                        else:
                            # Negative port indicates compacted controls in a single value
                            helpers.tables.intToPWM(int(values[i]))
            setTicks += utime.ticks_us() - ticks1

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
            if button_pressed():
                utime.sleep_ms(50)    # Debounce switch
                if button_pressed():
                    if verbose: print('Caught Stop button')
                    break

            # Toggle LED to let us know something is happening
            toggle_LEDs()

            # Read another line from CSV file
            startLockTicks = utime.ticks_us()
            line = source.readline()
            # If our time is already past the next time, continue reading
            while len(line) > 0:
                tTicks = utime.ticks_us()
                values = line.split(',')
                splitTicks += utime.ticks_diff(utime.ticks_us(), tTicks)
                nextTicks = int(values[0])
                if nextTicks >= utime.ticks_diff(utime.ticks_ms(), startTicks): break
                skips += 1
                line = source.readline()
            readTicks += utime.ticks_diff(utime.ticks_us(), startLockTicks)
        loopTime = utime.ticks_diff(utime.ticks_us(), loopTicks)

        if(verbose): print('At end of read file loop')
        if player is not None: player.stop()
        source.close()

        # Optionally report stats
        if(verbose):
            print('Total time:', utime.ticks_diff(utime.ticks_ms(), startTicks), 'msec')
            print('Wait time :', waitTime, 'msec')
            print('Duration  :', nextTicks, 'msec')
            print('Wait frac :', waitTime/nextTicks)
            print('Read time :', readTicks, 'usec')
            print('Skip count:', skips)

            print('Used', splitTicks, 'usec to split the line', servoCount+skips, 'times')
            print('For an average of', splitTicks/(servoCount+skips), 'usec per cycle')
            print('Used', servoTicks, 'usec to write to servo', servoCount, 'times')
            print('For an average of', servoTicks/servoCount, 'usec per cycle')
            print('Used', digTicks, 'usec to shift out digital values', servoCount, 'times')
            print('For an average of', digTicks/servoCount,'usec per cycle')
            print('Used', setTicks, 'usec to read and interpret ascii values', servoCount, 'times')
            print('For an average of', setTicks/servoCount,'usec per cycle')
            print('Used', loopTime, 'usec to run', servoCount, 'cycles')
            print('For an average of', loopTime/servoCount,'usec per cycle')

            print('Time spent waiting for lock:', lockTicks, 'usec')

        # Let all the servos relax
        helpers.releaseAllServos()

    # Wait for audio player to be done also
    if player is not None:
        while player.playing(): utime.sleep_ms(1)

    # Optionally report stats
    if(verbose):
        # Run some tests on control functions
        startTicks = utime.ticks_us()
        for j in range(1000):
            helpers.outputDigital()
        print('Time for 1000 outputDigital calls:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usecs')
        startTicks = utime.ticks_us()
        for j in range(100):
            helpers.setServo(8,50)
            helpers.pushServos()
        print('Time for 100 pushServo calls:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usecs')
        startTicks = utime.ticks_us()
        for j in range(1000):
            helpers.setServo(8,450,push=False)
        print('Time for 1000 setServo calls:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usecs')
        startTicks = utime.ticks_us()
        if isfile(csvfile):
            infile = open(csvfile, 'r')
            if infile:
                line = infile.readline()
                while len(line) > 0:
                    line = infile.readline()
            print('Time for 1 csv file read:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usecs')
        startTicks = utime.ticks_us()
        if isfile(csvfile):
            infile = open(csvfile, 'r')
            if infile:
                line = infile.readline()
                line = infile.readline()
                while len(line) > 0:
                    values = line.split(',')
                    for value in values: x = int(value)
                    line = infile.readline()
            print('Time for read and split :', utime.ticks_diff(utime.ticks_us(), startTicks), 'usecs')
        startTicks = utime.ticks_us()
        if isfile(csvfile):
            f = open(csvfile, 'rb')
            bytes = f.read(512)
            while len(bytes) > 0:
                bytes = f.read(512)
            print('Time for 1 wave file read:', utime.ticks_diff(utime.ticks_us(), startTicks), 'usecs')


if __name__ == "__main__":
    animList = findAnimFiles()
    do_the_thing(animList)
