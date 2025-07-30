try:
    import serial
    from serial.tools import list_ports
except:
    pass

try:
    from machine import Pin,UART
except:
    pass

from sys import version_info

PY2 = version_info[0] == 2   #Running Python 2.x?

#
#---------------------------
# Maestro Servo Controller
#---------------------------
#
# Support for the Pololu Maestro line of servo controllers
#
# Steven Jacobs -- Aug 2013
# https://github.com/FRC4564/Maestro/
#
# These functions provide access to many of the Maestro's capabilities using the
# Pololu serial protocol
#
# Many updates by John Wright -- June 2025
# Provided access through UARTs to Maestro capabilities for microcontrollers,
# specifically the Raspberry Pi Pico.
#
class Controller:
    # When connected via USB, the Maestro creates two virtual serial ports
    # /dev/ttyACMn for commands and /dev/ttyACMn+1 for communications.
    # Be sure the Maestro is configured for "USB Dual Port" serial mode.
    # "USB Chained Mode" may work as well, but hasn't been tested.
    #
    # When hanging the Maestro(s) off a microcontroller like the Raspberry Pi
    # Pico, the Maestros are controlled via UART from a GPIO pin.  In this case,
    # the Maestro must be in UART mode, preferably autodetect baudrate.
    #
    # Pololu protocol allows for multiple Maestros to be connected to a single
    # serial port. Each connected device is then indexed by number.
    # This device number defaults to 0x0C (or 12 in decimal), which this module
    # assumes.  If two or more controllers are connected to different serial
    # ports, or you are using a Windows OS, you can provide the tty port.  For
    # example, '/dev/ttyACM2' or for Windows, something like 'COM3'.
    def __init__(self,ttyStr=None, device=0x0c, TxPin=None):
        if TxPin is None:
            # Use serial mode over USB
            if ttyStr is None:
                # Look for first port with a Pololu device
                for port in serial.tools.list_ports.comports():
                    if port.manufacturer.find('Pololu') >= 0:
                        if ttyStr is None or port.device < ttyStr:
                            ttyStr = port.device
            if ttyStr is None:
                sys.stderr.write('\nWHOOPS - Could not find Pololu device.\n\n')
                return
            print('Device:', ttyStr)
            # Open the command port
            self.usb = serial.Serial(ttyStr, baudrate=115200)
            self.closable = True
        else:
            # Use UART port on pin TxPin from microcontroller
            if TxPin == 0:
                self.usb = UART(0, baudrate=115200, tx=Pin(0, Pin.OUT))
            elif TxPin == 4:
                self.usb = UART(1, baudrate=115200, tx=Pin(4, Pin.OUT))
            elif TxPin == 8:
                self.usb = UART(1, baudrate=115200, tx=Pin(8, Pin.OUT))
            elif TxPin == 12:
                self.usb = UART(0, baudrate=115200, tx=Pin(12, Pin.OUT))
            self.closable = False

        # Command lead-in and device number are sent for each Pololu serial command.
        self.PololuCmd = chr(0xaa) + chr(device)
        # Track target position for each servo. The function isMoving() will
        # use the Target vs Current servo position to determine if movement is
        # occuring.  Upto 24 servos on a Maestro, (0-23). Targets start at 0.
        self.Targets = [0] * 24
        # Servo minimum and maximum targets can be restricted to protect components.
        self.Mins = [0] * 24
        self.Maxs = [0] * 24
        self.close()
        self.commands = []
        
    # Cleanup by closing USB serial port
    def close(self):
        if self.closable:
            self.usb.close()

    # Reopen the USB serial port
    def open(self):
        if self.closable:
            self.usb.open()

    # Set the board id
    def setBoard(self, device):
        self.PololuCmd = chr(0xaa) + chr(device)

    # Send a Pololu command out the serial port
    def sendCmd(self, cmd):
        cmdStr = self.PololuCmd + cmd
        if PY2:
            self.usb.write(cmdStr)
        else:
            #print('Sending:', bytes(cmdStr,'latin-1'))
            self.usb.write(bytes(cmdStr,'latin-1'))

    # Send a stream of commands while holding the port open
    # Defaults to sending the internal command list
    def sendCmds(self, cmds=None):
        if cmds is None:
            cmds = self.commands
        self.open()
        for cmd in cmds:
            cmdStr = self.PololuCmd + cmd
            self.usb.write(bytes(cmdStr,'latin-1'))
        self.close()
        self.clearCmds()

    # Clear the current command list
    def clearCmds(self):
        self.commands = []

    # Add a command to the command list
    def addCmd(self, cmd):
        self.commands.append(cmd)

    # Set channels min and max value range.  Use this as a safety to protect
    # from accidentally moving outside known safe parameters. A setting of 0
    # allows unrestricted movement.
    #
    # ***Note that the Maestro itself is configured to limit the range of servo travel
    # which has precedence over these values.  Use the Maestro Control Center to configure
    # ranges that are saved to the controller.  Use setRange for software controllable ranges.
    def setRange(self, chan, min, max):
        self.Mins[chan] = min
        self.Maxs[chan] = max

    # Return Minimum channel range value
    def getMin(self, chan):
        return self.Mins[chan]

    # Return Maximum channel range value
    def getMax(self, chan):
        return self.Maxs[chan]
        
    # Set channel to a specified target value.  Servo will begin moving based
    # on Speed and Acceleration parameters previously set.
    # Target values will be constrained within Min and Max range, if set.
    # For servos, target represents the pulse width in of quarter-microseconds
    # Servo center is at 1500 microseconds, or 6000 quarter-microseconds
    # Typcially valid servo range is 3000 to 9000 quarter-microseconds
    # If channel is configured for digital output, values < 6000 = Low ouput
    def setTarget(self, chan, target):
        # if Min is defined and Target is below, force to Min
        if self.Mins[chan] > 0 and target < self.Mins[chan]:
            target = self.Mins[chan]
        # if Max is defined and Target is above, force to Max
        if self.Maxs[chan] > 0 and target > self.Maxs[chan]:
            target = self.Maxs[chan]
        #    
        lsb = target & 0x7f #7 bits for least significant byte
        msb = (target >> 7) & 0x7f #shift 7 and take next 7 bits for msb
        cmd = chr(0x04) + chr(chan) + chr(lsb) + chr(msb)
        self.addCmd(cmd)
        # Record Target value
        self.Targets[chan] = target
        
    # Set speed of channel
    # Speed is measured as 0.25microseconds/10milliseconds
    # For the standard 1ms pulse width change to move a servo between extremes, a speed
    # of 1 will take 1 minute, and a speed of 60 would take 1 second.
    # Speed of 0 is unrestricted.
    def setSpeed(self, chan, speed):
        lsb = speed & 0x7f #7 bits for least significant byte
        msb = (speed >> 7) & 0x7f #shift 7 and take next 7 bits for msb
        cmd = chr(0x07) + chr(chan) + chr(lsb) + chr(msb)
        self.addCmd(cmd)

    # Set acceleration of channel
    # This provide soft starts and finishes when servo moves to target position.
    # Valid values are from 0 to 255. 0=unrestricted, 1 is slowest start.
    # A value of 1 will take the servo about 3s to move between 1ms to 2ms range.
    def setAccel(self, chan, accel):
        lsb = accel & 0x7f #7 bits for least significant byte
        msb = (accel >> 7) & 0x7f #shift 7 and take next 7 bits for msb
        cmd = chr(0x09) + chr(chan) + chr(lsb) + chr(msb)
        self.addCmd(cmd)
    
    # Get the current position of the device on the specified channel
    # The result is returned in a measure of quarter-microseconds, which mirrors
    # the Target parameter of setTarget.
    # This is not reading the true servo position, but the last target position sent
    # to the servo. If the Speed is set to below the top speed of the servo, then
    # the position result will align well with the acutal servo position, assuming
    # it is not stalled or slowed.
    def getPosition(self, chan):
        cmd = chr(0x10) + chr(chan)
        self.open()
        self.sendCmd(cmd)
        lsb = ord(self.usb.read())
        msb = ord(self.usb.read())
        self.close()
        return (msb << 8) + lsb

    # Test to see if a servo has reached the set target position.  This only provides
    # useful results if the Speed parameter is set slower than the maximum speed of
    # the servo.  Servo range must be defined first using setRange. See setRange comment.
    #
    # ***Note if target position goes outside of Maestro's allowable range for the
    # channel, then the target can never be reached, so it will appear to always be
    # moving to the target.  
    def isMoving(self, chan):
        if self.Targets[chan] > 0:
            if self.getPosition(chan) != self.Targets[chan]:
                return True
        return False
    
    # Have all servo outputs reached their targets? This is useful only if Speed and/or
    # Acceleration have been set on one or more of the channels. Returns True or False.
    # Not available with Micro Maestro.
    def getMovingState(self):
        cmd = chr(0x13)
        self.open()
        self.sendCmd(cmd)
        readval = self.usb.read()
        self.close()
        if readval == chr(0):
            return False
        else:
            return True

    # Run a Maestro Script subroutine in the currently active script. Scripts can
    # have multiple subroutines, which get numbered sequentially from 0 on up. Code your
    # Maestro subroutine to either infinitely loop, or just end (return is not valid).
    def runScriptSub(self, subNumber):
        cmd = chr(0x27) + chr(subNumber)
        # can pass a param with command 0x28
        # cmd = chr(0x28) + chr(subNumber) + chr(lsb) + chr(msb)
        self.open()
        self.sendCmd(cmd)
        self.close()

    # Stop the current Maestro Script
    def stopScript(self):
        cmd = chr(0x24)
        self.open()
        self.sendCmd(cmd)
        self.close()

