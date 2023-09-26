import machine
try:
    import utime
except:
    import time as utime

import os
import helpers

def button_pressed():
    button = machine.Pin(7, machine.Pin.IN, machine.Pin.PULL_UP)
    return not button.value()

def do_the_thing(continuous=False, skip=False, doOnce=False):
    # Use the on board LED for status
    led_onboard = machine.Pin(25, machine.Pin.OUT)

    # Set the initial state
    try:
        helpers.mountSDCard()       # Mount SD card for all data files
    except:
        # Ignore errors
        pass

    # Find the preferred channel file on the SD card or in flash
    try:
        os.stat('/sd/data.csv')
        datafile = '/sd/data.csv'
    except:
        try:
            os.stat('/data.csv')
            datafile = '/data.csv'
        except:
            datafile = ''

    # Find the preferred audio file on the SD card or in flash
    try:
        os.stat('/sd/data.wav')
        wavefile = '/sd/data.wav'
    except:
        try:
            os.stat('/data.wav')
            wavefile = '/data.wav'
        except:
            wavefile = ''

    helpers.setAllDigital(0)    # All digital channels off
    helpers.releaseAllServos()  # All servos relaxed

    # if skip is True then immediately begin execution
    # if continuous is True then execute continuously until interrupted
    # Else Blink at 0.5Hz until button is pressed
    while True:
        # Blink LED at 1 Hz until button pressed
        if not continuous and not skip:
            while not button_pressed():
                led_onboard.toggle()
                for i in range(100):
                    utime.sleep(0.01)
                    if button_pressed():
                        utime.sleep(0.05)  # Debounce switch
                        if button_pressed(): break

            # Wait up to 5 seconds for button to be released
            led_onboard.on()
            for i in range(100):
                utime.sleep(0.05)
                if not button_pressed():
                    utime.sleep(0.05)    # Debounce switch
                    if not button_pressed(): break
            
        # If button is STILL pressed, go into continuous loop mode
        if button_pressed():
            # Blink LED at 10 Hz until button released
            while True:
                led_onboard.toggle()
                utime.sleep(0.1)
                if not button_pressed():
                    utime.sleep(0.05)    # Debounce switch
                    if not button_pressed(): break
            continuous = True

        # Open the default CSV file
        infile = open(datafile, 'r')
        if infile:
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

            # Start the audio playing
            player = helpers.WavePlayer(wavefile)
            utime.sleep(0.05)   # Delay a bit before playing audio
            player.play()

            # Get the current time
            startTicks = utime.ticks_ms()

            # Gather waittime stats
            waitTime = 0

            # Run animatronics until done or button is pressed
            while len(line) > 0:
                # Parse the line
                values = line.split(',')
                # Wait until it is time to go to next state
                nextTicks = int(float(values[0]) * 1000)
                while(utime.ticks_diff(utime.ticks_ms(), startTicks) < nextTicks):
                    utime.sleep_ms(1)
                    waitTime += 1

                # Send all values in the row to the Pins
                for i in range(1,len(titles)):
                    if ports[i] is not None:
                        if ports[i] >= helpers.MaxTotalServos:
                            # Must be a digital channel
                            value = float(values[i])
                            helpers.setDigital(ports[i] - helpers.MaxTotalServos, value)
                        else:
                            value = float(values[i])
                            if value < 0.03 or value > 0.12:
                                print('Value out of range:', value)
                            else:
                                helpers.setServo(ports[i], value)
                            pass

                # Make sure all the digital channels are output
                helpers.outputDigital()

                # Check to see if button is pressed and quit if so
                if button_pressed():
                    utime.sleep(0.05)    # Debounce switch
                    if button_pressed():
                        # Stop running continuous mode on button press also
                        continuous = False
                        player.stop()
                        break

                # Toggle LED to let us know something is happening
                led_onboard.toggle()

                # Read another line from CSV file
                line = infile.readline()

            infile.close()

            # Let all the servos relax
            for i in range(1,len(titles)):
                if ports[i] is not None:
                    helpers.releaseServo(ports[i])
                    pass

            # Revert to normal operations
            skip = False

            if doOnce: break
                
            # Now wait until button is released to go to top of loop
            while True:
                if not button_pressed():
                    utime.sleep(0.05)    # Debounce switch
                    if not button_pressed(): break

if __name__ == "__main__":
    do_the_thing()
