import machine
try:
    import utime
except:
    import time as utime

import os
import sys
import random
import helpers

verbose=False

def button_pressed():
    button = machine.Pin(24, machine.Pin.IN, machine.Pin.PULL_UP)
    return not button.value()

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
    # Use the on board LED for status
    led_onboard = machine.Pin(25, machine.Pin.OUT)

    helpers.setAllDigital(0)    # All digital channels off
    helpers.releaseAllServos()  # All servos relaxed

    # Don't bother with anything if list of animations is empty
    playIndex = 0
    if len(animList) > 0:
        if randomize: playIndex = random.randint(0, len(animList)-1)
    if verbose: print(animList)

    # Swallow strange initially pressed state
    while button_pressed():
        utime.sleep_ms(1000)
        button_pressed()

    # if skip is True then immediately begin execution
    # if continuous is True then execute continuously until interrupted
    # Else Blink at 0.5Hz until button is pressed
    while True:
        # Toggle LED every second until button pressed
        if not continuous and not skip:
            while not button_pressed():
                code = 0
                led_onboard.toggle()
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
            led_onboard.on()
            for i in range(100):
                utime.sleep_ms(50)
                if not button_pressed():
                    utime.sleep_ms(50)    # Debounce switch
                    if not button_pressed(): break

        # If button is STILL pressed, go into continuous loop mode
        if button_pressed():
            # Blink LED at 10 Hz until button released
            while True:
                led_onboard.toggle()
                utime.sleep_ms(10)
                if not button_pressed():
                    utime.sleep_ms(50)    # Debounce switch
                    if not button_pressed(): break
            continuous = True

        if playIndex < len(animList):
            # Get next animation to play
            if verbose: print('Print playing animation:', playIndex,'named:',animList[playIndex][0])
            # Play it
            play_one_anim(animList[playIndex][0], animList[playIndex][1], led_onboard)

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

def play_one_anim(csvfile, wavefile, led_onboard):
    # Open the default CSV file
    infile = False
    if isfile(csvfile): infile = open(csvfile, 'r')
    if infile:
        if verbose: print('Playing animation file:', csvfile)
        # Read the first line to get ports
        hdr = infile.readline()
        titles = hdr.split(',')
        ports = [None]      # No port for frame column
        for i in range(1,len(titles)):
            ports.append(None)
            lparen = titles[i].find('(')
            if lparen >= 0:
                rparen = titles[i].find(')')
                if rparen > lparen + 1:
                    ports[i] = int(titles[i][lparen+1:rparen])

        # Get ready to rock-n-roll
        # Read the first line of data
        line = infile.readline()

    # Start the audio playing whether there is a CSV file or not
    if verbose: print('Playing file:', wavefile)
    if isfile(wavefile):
        player = helpers.WavePlayer(wavefile)
        player.play()

    if infile:
        # Get the current time
        startTicks = utime.ticks_ms()

        # Gather waittime stats
        waitTime = 0

        # Run animatronics until done or button is pressed
        while len(line) > 0:
            # Parse the line
            values = line.split(',')
            # Wait until it is time to go to next state
            nextTicks = int(values[0])
            while(utime.ticks_diff(utime.ticks_ms(), startTicks) < nextTicks):
                utime.sleep_ms(1)
                waitTime += 1

            # Send all values in the row to the Pins
            if verbose: print('Sending data at time:',utime.ticks_diff(utime.ticks_ms(), startTicks), 'which should be:', nextTicks)
            for i in range(1,len(titles)):
                if ports[i] is not None:
                    if ports[i] >= helpers.MaxTotalServos:
                        # Must be a digital channel
                        value = int(values[i])
                        helpers.setDigital(ports[i] - helpers.MaxTotalServos, value)
                        if verbose: print('Setting digital port:', ports[i] - helpers.MaxTotalServos, 'to:', value)
                    else:
                        value = int(values[i])
                        helpers.setServo(ports[i], value)

            # Make sure all the digital channels are output
            helpers.outputDigital()

            # Check to see if button is pressed and quit if so
            if button_pressed():
                utime.sleep_ms(50)    # Debounce switch
                if button_pressed():
                    if verbose: print('Caught Stop button')
                    player.stop()
                    break

            # Toggle LED to let us know something is happening
            led_onboard.toggle()

            # Read another line from CSV file
            line = infile.readline()

        if(verbose): print('At end of read file loop')
        infile.close()

        # Optionally report stats
        if(verbose):
            print('Wait time :', waitTime, 'msec')
            print('Total time:', nextTicks, 'msec')
            print('Wait frac :', waitTime/nextTicks)

        # Let all the servos relax
        for i in range(1,len(titles)):
            if ports[i] is not None:
                helpers.releaseServo(ports[i])
                pass

    # Wait for audio player to be done also
    while player.playing():
        utime.sleep_ms(1)


if __name__ == "__main__":
    animList = findAnimFiles()
    do_the_thing(animList)
