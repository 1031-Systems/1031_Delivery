#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#**********************************
# Program control_emulator.py
# Created by john
# Created Wed Jun 4 01:35:29 PM PDT 2025
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
import signal
import binascii
import time

# Use pygame for audio playback and control
import pygame

# Import the port mappings and maestro access code
# Get path to actual file and add path/lib to search path
_Dir = os.path.dirname(os.path.realpath(__file__))
_Path = os.path.join(_Dir, 'lib')
sys.path.append(_Path)

# Now import stuff from our extended path
import tables
import transcomm

# Remove path so other code can't accidentally get to it
sys.path.remove(_Path)

# Import local modules
import AnimClasses

#/* Define block */
verbosity = False

animPlayer = None
animList = None
commdev = None
printer = None

# This is a simple class that will help us print to the screen.
# It has nothing to do with the joysticks, just outputting the
# information.
class TextPrint:
    def __init__(self, screen=None):
        self.font = pygame.font.Font(None, 25)
        self.screen = screen
        self.reset()

    def tprint(self, text):
        if self.screen is not None:
            text_bitmap = self.font.render(text, True, (0, 0, 0))
            self.screen.blit(text_bitmap, (self.x, self.y))
            self.y += self.line_height

    def reset(self):
        self.x = 10
        self.y = 10
        self.line_height = 15
        if self.screen is not None:
            self.screen.fill((255, 255, 255))

    def indent(self):
        self.x += 10

    def unindent(self):
        self.x -= 10

    def flip(self):
        if self.screen is not None:
            pygame.display.flip()
            self.reset()


class AnimPlayer():
    StopMode = 0
    PlayMode = 1

    def __init__(self):
        self.currAudio = None
        self.currAnim = None
        self.currAnimFile = None
        self.inline = ''
        self.mode = AnimPlayer.StopMode
        self.digitalMap = {}
        self.pwmMap = {}

    def setAnimation(self, animation):
        self.currAudio = None
        if self.currAnimFile is not None:
            self.currAnimFile.close()
            self.currAnimFile = None
        self.currAnim = None
        self.digitalMap = {}
        self.pwmMap = {}
        self.currAnim = animation[0]
        self.currAudio = animation[1]

    def play(self, animation=None):
        if animation is not None: self.setAnimation(animation)
        self.mode = AnimPlayer.PlayMode
        if self.currAudio is not None:
            # Do this before setState(0.0) so player is busy
            # print('Playing audio file:', self.currAudio)
            pygame.mixer.music.load(self.currAudio)
            pygame.mixer.music.play()
        if self.currAnim is not None:
            # print('Playing animation file:', self.currAnim)
            if os.path.exists(self.currAnim) and os.path.isfile(self.currAnim):
                self.currAnimFile = open(self.currAnim, 'r')
                # Parse the column data from the header line
                header = self.currAnimFile.readline()
                if len(header) < 4 or header[0:4] != 'Time':
                    self.stop()
                else:
                    hdrvalues = header.split(',')
                    for indx in range(1, len(hdrvalues)):
                        val = hdrvalues[indx].strip()
                        if val[0] == 'D':
                            self.digitalMap[indx] = int(val[1:])
                        elif val[0] == 'S':
                            self.pwmMap[indx] = int(val[1:])
                    # Read the first data line to seed time
                    self.inline = self.currAnimFile.readline()
                    # Now set initial state
                    self.setState(0.0)

    def stop(self):
        self.mode = AnimPlayer.StopMode
        pygame.mixer.music.stop()

    def setState(self, animtime):
        if self.mode == AnimPlayer.PlayMode:
            if self.currAnimFile is not None:
                animtime = int(animtime * 1000)     # Convert to milliseconds

                values = self.inline.split(',')
                while len(self.inline) > 1 and int(values[0].strip()) <= animtime:
                    self.inline = self.currAnimFile.readline()
                    values = self.inline.split(',')

                for indx in range(1, len(values)):
                    value = values[indx].strip()
                    if indx in self.digitalMap:
                        tables.setDigital(self.digitalMap[indx], int(value))
                    elif indx in self.pwmMap:
                        tables.setPWM(self.pwmMap[indx], float(value))
                # Push out all the values to the Maestro
                tables.pushPWMs()

            stillrunning = pygame.mixer.music.get_busy() or len(self.inline) > 1
        else:
            stillrunning = False

        return not stillrunning

def setServo(channel, value, push=False):
        tables.setPWM(channel, value, push)

def setDigital(channel, value, push=False):
        tables.setDigital(channel, value, push)

        
def mainEventLoop():
    global animList

    playMode = False        # Indicates we are playing an animation other than idle
    idleMode = False        # Indicates we are playing the idle animation
    continuousMode = False  # Indicates we are playing all nonidle animations continuously
    prevMain = False
    lastMain = False
    lastRun = False
    lastTrigger = False
    lastInput = None

    def getMain():
        '''
        Checks input status of specific input, makes sure it is the same as 1 msec ago for debouncing,
        and returns button state.  Returns False if input has not been configured.
        '''
        nonlocal lastMain
        newMain = tables.getMainInput()
        if newMain is not None:
            retvalue = lastMain
            if newMain != lastMain:
                lastMain = newMain
            return retvalue
        else:
            return False

    def getRun():
        nonlocal lastRun
        newRun = tables.getRunInput()
        if newRun is not None:
            retvalue = lastRun
            if newRun != lastRun:
                lastRun = newRun
            return retvalue
        else:
            return False

    def getTrigger():
        nonlocal lastTrigger
        newTrigger = tables.getTriggerInput()
        if newTrigger is not None:
            retvalue = lastTrigger
            if newTrigger != lastTrigger:
                lastTrigger = newTrigger
            return retvalue
        else:
            return False

    triggerTime = 0.0
    prevTime = 0.0
    startTime = time.monotonic()
    while True:     # 20 msec outer loop
        currTime = time.monotonic() - startTime
        while currTime < prevTime + 0.02:       # 1.0 msec inner loop
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYUP and event.key == pygame.K_q):
                    pygame.quit()
                    commdev.cleanup()
                    sys.exit(0)
                elif (event.type == pygame.KEYDOWN and event.key == pygame.K_m):
                    # Note press of trigger to see if held down for 5 seconds
                    triggerTime = currTime
                    pass
                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_r:
                        # Reset everything
                        playMode = False
                        idleMode = False
                        continuousMode = False
                        lastInput = None
                        triggerTime = 0.0
                        prevTime = 0.0
                        startTime = time.monotonic()
                        animPlayer.stop()
                        animList.refresh()
                    elif event.key == pygame.K_m:
                        # Trigger button
                        lastInput = None
                        continuousMode = (currTime - triggerTime) > 5.0    # Continuous play mode when held 5 seconds
                        # Enter or exit play mode
                        if continuousMode:
                            print('In continuous mode:', continuousMode)
                            playMode = True
                            idleMode = False
                        else:
                            playMode = not playMode
                        animPlayer.stop()
                        if playMode:
                            # Go to next animation and start it
                            startTime = time.monotonic()
                            currTime = time.monotonic() - startTime
                            prevTime = currTime
                            nextAnim = animList.getNextAnim()
                            animPlayer.play(nextAnim)
                        else:
                            # Stop the current animation and maybe go to idle animation
                            nextAnim = animList.getIdleAnim()
                            if nextAnim is not None:
                                idleMode = True
                                animPlayer.play(nextAnim)
                        pass
                    elif event.key == pygame.K_t:
                        # Opto-isolated trigger button
                        if not playMode:
                            playMode = True
                            # Go to next animation and start it
                            startTime = time.monotonic()
                            currTime = time.monotonic() - startTime
                            prevTime = currTime
                            nextAnim = animList.getNextAnim(lastInput)
                            lastInput = None
                            animPlayer.play(nextAnim)
                        pass
                    else:
                        pass
                else:
                    pass

            # Now deal with input from Maestro
            newMain = getMain()
            if newMain != prevMain:
                if prevMain:
                    trigger = pygame.event.Event(pygame.KEYUP, {'key':pygame.K_m})
                    pygame.event.post(trigger)
                else:
                    trigger = pygame.event.Event(pygame.KEYDOWN, {'key':pygame.K_m})
                    pygame.event.post(trigger)
                prevMain = newMain
            if getTrigger():
                trigger = pygame.event.Event(pygame.KEYUP, {'key':pygame.K_t})
                pygame.event.post(trigger)
            for trigger in animList.triggers:
                if tables.getInput(trigger):
                    lastInput = trigger
                    trigger = pygame.event.Event(pygame.KEYUP, {'key':pygame.K_t})
                    pygame.event.post(trigger)
                    break
            if getRun():
                trigger = pygame.event.Event(pygame.KEYUP, {'key':pygame.K_r})
                pygame.event.post(trigger)

            # Now deal with fifo input
            if commdev and commdev.isReady():
                while commdev.isThereInput():
                    inline = commdev.readline()
                    if len(inline) < 2: continue
                    #print('Got line:', inline)
                    if inline[0] == 'a':
                        # Trigger one playback
                        trigger = pygame.event.Event(pygame.KEYDOWN, {'key':pygame.K_m})
                        pygame.event.post(trigger)
                        trigger = pygame.event.Event(pygame.KEYUP, {'key':pygame.K_m})
                        pygame.event.post(trigger)
                    elif inline[0] == 'x':
                        # Reset everything
                        trigger = pygame.event.Event(pygame.KEYUP, {'key':pygame.K_r})
                        pygame.event.post(trigger)
                    elif inline[0] == 'd':
                        # Set an individual digital port
                        try:
                            vals = inline.split()
                            channel = int(vals[1]) # - MaxTotalServos # Move down
                            value = int(vals[2])
                            setDigital(channel, value, push=True)
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
 
            time.sleep(0.001)
            currTime = time.monotonic() - startTime

        prevTime = currTime
        
        # Process an animation frame
        if playMode or idleMode:
            done = animPlayer.setState(currTime)
            if done:
                # print('Done with animation:', animPlayer.currAnim)
                startTime = time.monotonic()
                if continuousMode:
                    # start next animation
                    idleMode = False
                    playMode = True
                    startTime = time.monotonic()
                    currTime = time.monotonic() - startTime
                    prevTime = currTime
                    nextAnim = animList.getNextAnim()
                    animPlayer.play(nextAnim)
                elif animList.getIdleAnim() is not None:
                    playMode = False
                    idleMode = True
                    startTime = time.monotonic()
                    currTime = time.monotonic() - startTime
                    prevTime = currTime
                    nextAnim = animList.getIdleAnim()
                    animPlayer.play(nextAnim)
                else:
                    playMode = False
                    idleMode = False
        if playMode:
            printer.tprint('Mode: Play')
            animtext = 'Animation:'
            if nextAnim[0] is not None: animtext += nextAnim[0]
            audiotext = 'Audio:'
            if nextAnim[1] is not None: audiotext += nextAnim[1]
            printer.tprint(animtext)
            printer.tprint(audiotext)
        elif idleMode:
            printer.tprint('Mode: Idle')
            animtext = 'Animation:'
            if nextAnim[0] is not None: animtext += nextAnim[0]
            audiotext = 'Audio:'
            if nextAnim[1] is not None: audiotext += nextAnim[1]
            printer.tprint(animtext)
            printer.tprint(audiotext)
        else:
            printer.tprint('Mode: Stopped')
            animtext = 'Animation:'
            audiotext = 'Audio:'
            printer.tprint(animtext)
            printer.tprint(audiotext)
        printer.tprint('')
        printer.tprint('R:Reset   M:Main   T:Trigger   Q: Quit')
        printer.flip()

def signal_handler(signum, frame):
    signal.signal(signum, signal.SIG_IGN) # ignore additional signals
    pygame.quit()
    commdev.cleanup()
    sys.stdout.write('\n')
    sys.stdout.flush()
    sys.exit(0)

#/* Usage method */
def print_usage(name):
    """ Simple method to output usage when needed """
    sys.stderr.write("\nUsage: %s [-/-h/-help] [-v/-verbose]\n" % name);
    sys.stderr.write("Enter purpose here.\n");
    sys.stderr.write("-/-h/-help        :show this information\n");
    sys.stderr.write("-v/-verbose       :run more verbosely\n");
    sys.stderr.write("-nohead           :do not open window or accept key commands\n")
    sys.stderr.write("-p/-path dirpath  :specify path to anims and sd/anims directories\n")
    sys.stderr.write("\n\n");

#/* Main */
if __name__ == "__main__":
    # Initial values
    head = True
    path = _Dir

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '-' or sys.argv[i] == '-h' or sys.argv[i] == '-help':
            print_usage(sys.argv[0]);
            sys.exit(0);
        elif sys.argv[i] == '-v' or sys.argv[i] == '-verbose':
            verbosity = True
        elif sys.argv[i] == '-nohead':
            head = False
        elif sys.argv[i] == '-p' or sys.argv[i] == '-path':
            i += 1
            if i < len(sys.argv):
                path = sys.argv[i]
        else:
            sys.stderr.write("\nWhoops - Unrecognized argument: %s\n" % sys.argv[i]);
            print_usage(sys.argv[0]);
            sys.exit(10);

        i += 1

    # Initialize stuff
    # Interrupt handler
    signal.signal(signal.SIGINT, signal_handler)

    # Animations
    animList = AnimClasses.AnimList(inDir=os.path.join(path, 'sd/anims'))
    animList.addAnims(os.path.join(path, 'anims'))
    animPlayer = AnimPlayer()
    if verbosity:
        print('Animation Playlist')
    maxWidth = 400
    for anim in animList.theAnims:
        twidth = len(anim[0]) * 9 + 100
        if twidth > maxWidth: maxWidth = twidth
        twidth = len(anim[1]) * 9 + 100
        if twidth > maxWidth: maxWidth = twidth
        if verbosity:
            print(anim)

    # Pygame
    pygame.init()
    pygame.mixer.init()
    pygame.mixer.music.set_volume(0.5)

    pygame.display.set_caption('Maestro Controller')
    display = None
    if head: display = pygame.display.set_mode((maxWidth, 100))
    printer = TextPrint(display)

    # FIFOs
    commdev = transcomm.FIFOComm(
        inputFIFOName = '/tmp/fifo.commtocontrol',
        outputFIFOName = '/tmp/fifo.controltocomm'
    )

    # Maestro

    # Start the main loop
    mainEventLoop()


