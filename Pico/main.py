import machine
try:
    import utime
except:
    import time as utime

import os
import sys
import random
import ustruct
import helpers
import gc

# Constants for port types
DIGITAL = 1
PWM = 2

# Constants for control data file format
CSV = 5
HEX = 6     # No longer used
BIN = 7


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
    # Initially assume ascii file format
    binblocksize = 0

    # Get expected binary file block sizes just in case
    blockSizes = helpers.tables.getBinarysizes()
    print('blockSizes:', blockSizes)

    boardlist = helpers.tables.boardList()
    if verbose:
        for board in boardlist:
            print('Board ID:', board.pca9685.address, 'First port:', board.firstport, 'First byte:', board.firstport+blockSizes[1]+blockSizes[2])

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
        # bad
        if verbose: print('Whoops - Unable to open and read control file:', csvfile)
        return

    # Create the player
    player = None   # Set player to None so later we know if it exists
    if helpers.isfile(wavefile):
        player = helpers.WavePlayer(wavefile, csvfilename=csvfile, binblocksize=binblocksize, verbose=(0 if not verbose else 1))


    # Open the default CSV file if there is no player
    source = None
    if helpers.isfile(csvfile):
        if player is None:
            source = open(csvfile, 'r')
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
        elif csvformat == HEX:
            # Assumed column titles and order
            titles = ['Time', 'D-1', 'S-1']
            ports = [None, -1, -1]
            porttypes = [None, DIGITAL, PWM]
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

    # Temporary ticks
    ticks1 = 0
    ticks2 = 0
    ticks3 = 0
    ticks4 = 0
    ticks5 = 0

    # Get the struct unpacking format for the known range of port IDs
    theformat = helpers.tables.getPWMstructformat()
    if verbose: print('PWM Struct format:', theformat, 'of length:', len(theformat))

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
        elif csvformat == HEX:
            tval = bytes.fromhex(line[0:16])
            nextTicks = ustruct.unpack('<Q', tval)[0]
        elif csvformat == BIN:
            nextTicks = ustruct.unpack('<Q', line[0:8])[0]
        splitTicks += utime.ticks_diff(utime.ticks_us(), ticks1)

        loopTicks = utime.ticks_us()
        while len(line) > 0:
            #if verbose: print('Processing line:', line)
            # Wait until it is time to go to next state
            while(utime.ticks_diff(utime.ticks_ms(), startTicks) < nextTicks):
                utime.sleep_ms(1)
                waitTime += 1

            # Send all values in the row to the Pins
            #if verbose: print('Sending data at time:',utime.ticks_diff(utime.ticks_ms(), startTicks), 'which should be:', nextTicks)
            ticks1 = utime.ticks_us()
            if csvformat == BIN:
                ticks1 = utime.ticks_us()
                boardstart = blockSizes[1] + blockSizes[2]
                for board in boardlist:
                    board.pca9685.jambytes(line[board.firstport*4+boardstart:board.firstport*4+boardstart+board.numbytes])
                # Now process all the PWMs on GPIO pins
                for indx in range(0, blockSizes[3] >> 2):
                    addr = indx*4 + blockSizes[1] + blockSizes[2]
                    helpers.tables.dosomething(indx, line[addr+2:addr+4])
                servodataTicks += utime.ticks_diff(utime.ticks_us(), ticks1)
                bits = int.from_bytes(line[blockSizes[1]:blockSizes[1] + blockSizes[2]], 'little')
                helpers.tables.intToDigital(bits)
                helpers.tables.outputDigital()
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
                            elif csvformat == HEX:
                                tval = bytes.fromhex(line[16:32])
                                value = ustruct.unpack('<Q', tval)[0]
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
                                elif csvformat == HEX:
                                    poop = utime.ticks_us()
                                    thebytes = bytes.fromhex(line[32:-1])
                                    #print('usec to convert from hex:', utime.ticks_diff(utime.ticks_us(), poop ))
                                    poop = utime.ticks_us()
                                    vals = ustruct.unpack(theformat, thebytes)
                                    #print('usec to unpack:', utime.ticks_diff(utime.ticks_us(), poop ))
                                    poop = utime.ticks_us()
                                    helpers.tables.intsToPWM(vals)
                                    #print('usec to run intsToPWM:', utime.ticks_diff(utime.ticks_us(), poop ))
                                    #poop = utime.ticks_us()
                                    #helpers.tables._PWMBoards[0].pca9685.jambytes(thebytes)
                                    #print('usec to run jambytes:', utime.ticks_diff(utime.ticks_us(), poop ))
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
                utime.sleep_ms(50)    # Debounce switch
                if button_pressed():
                    if verbose: print('Caught Stop button')
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
                elif csvformat == HEX:
                    tval = bytes.fromhex(line[0:16])
                    nextTicks = ustruct.unpack('<Q', tval)[0]
                    splitTicks += utime.ticks_diff(utime.ticks_us(), ticks2)
                elif csvformat == BIN:
                    nextTicks = ustruct.unpack('<Q', line[0:8])[0]
                    splitTicks += utime.ticks_diff(utime.ticks_us(), ticks2)
                if nextTicks >= utime.ticks_diff(utime.ticks_ms(), startTicks) - 10: break
                skips += 1
                if csvformat == CSV:
                    line = source.readline()
                elif csvformat == BIN:
                    line = source.readline(line)
            readTicks += utime.ticks_diff(utime.ticks_us(), ticks1)

            ticks1 = utime.ticks_us()
            #gc.collect()
            garbageTicks += utime.ticks_diff(utime.ticks_us(), ticks1)

        # Compute how much time it took to perform the entire animation
        loopTime = utime.ticks_diff(utime.ticks_us(), loopTicks)

        if(verbose): print('At end of read file loop')
        if player is not None:
            while player.playing():
                # Waiting a bit to see if audio is done
                utime.sleep_ms(1)
        source.close()

        # Optionally report stats
        if(verbose):
            print('Total time:', utime.ticks_diff(utime.ticks_ms(), startTicks), 'msec')
            print('Wait time :', waitTime, 'msec')
            print('Duration  :', nextTicks, 'msec')
            print('Wait frac :', waitTime/nextTicks)
            print('Read time :', readTicks, 'usec')
            print('Skip count:', skips)

            print('Used', garbageTicks, 'usec for garbage collection', servoCount+skips, 'times')
            print('For an average of', garbageTicks/(servoCount+skips), 'usec per cycle')
            print('Used', readTicks, 'usec to input the line', servoCount+skips, 'times')
            print('For an average of', readTicks/(servoCount+skips), 'usec per cycle')
            print('Used', splitTicks, 'usec to split the line', servoCount+skips, 'times')
            print('For an average of', splitTicks/(servoCount+skips), 'usec per cycle')
            print('Used', dataTicks, 'usec to save the digital data', servoCount, 'times')
            print('For an average of', dataTicks/servoCount, 'usec per cycle')
            print('Used', servodataTicks, 'usec to save the servo data', servoCount, 'times')
            print('For an average of', servodataTicks/servoCount, 'usec per cycle')
            print('Used', servoTicks, 'usec to push to servos', servoCount, 'times')
            print('For an average of', servoTicks/servoCount, 'usec per cycle')
            print('Used', digTicks, 'usec to shift out digital values', servoCount, 'times')
            print('For an average of', digTicks/servoCount,'usec per cycle')
            print('Used', setTicks, 'usec to read and interpret ascii values', servoCount, 'times')
            print('For an average of', setTicks/servoCount,'usec per cycle')
            print('Used', buttonTicks, 'usec to read read stop button', (servoCount+skips), 'times')
            print('For an average of', buttonTicks/(servoCount+skips),'usec per cycle')
            print('Used', LEDTicks, 'usec to toggle LEDs', (servoCount+skips), 'times')
            print('For an average of', LEDTicks/(servoCount+skips),'usec per cycle')
            print('Used', loopTime, 'usec to run', (servoCount), 'cycles')
            print('For an average of', (loopTime-waitTime*1000)/(servoCount),'usec per cycle')

            print('Time spent waiting for lock:', lockTicks, 'usec')

        # Let all the servos relax
        helpers.releaseAllServos()


if __name__ == "__main__":
    animList = []
    try:
        animList = helpers.findAnimFiles(dir='/sd/anims')
    except:
        pass

    if len(animList) == 0:
        animList = helpers.findAnimFiles()

    do_the_thing(animList)
