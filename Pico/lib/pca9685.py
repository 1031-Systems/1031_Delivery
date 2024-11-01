# pca9685.py
# Kevin McAleer and John Wright
# March 2021 and March 2024
'''
@author Kevin McAleer and John Wright
'''

import struct
import time

try:
    time.sleep_us(1)
    def sleep_us(usec):
        time.sleep_us(usec)
except:
    def sleep_us(usec):
        time.sleep(float(usec) / 1000000.0)

class PCA9685:
    """
    This class models the PCA9685 board, used to control up to 16
    servos, using just 2 wires for control over the I2C interface
    """
    def __init__(self, i2c, address=0x40):
        """
        class constructor

        Args:
            i2c ([I2C Class, from the build in machine library]): This is used to 
            bring in the i2c object, which can be created by 
            > i2c = I2C(id=0, sda=Pin(0), scl=Pin(1))
            address (hexadecimal, optional): [description]. Defaults to 0x40.
        """
        self.i2c = i2c
        self.address = address
        self.reset()

    def _write(self, address, value):
        self.i2c.writeto_mem(self.address, address, bytearray([value]))

    def _read(self, address):
        return self.i2c.readfrom_mem(self.address, address, 1)[0]

    def reset(self):
        self._write(0x00, 0x00) # Mode1

    def freq(self, freq=None):
        if freq is None:
            return int(25000000.0 / 4096 / (self._read(0xfe) - 0.5))
        prescale = int(25000000.0 / 4096.0 / freq + 0.5)
        old_mode = self._read(0x00) # Mode 1
        self._write(0x00, (old_mode & 0x7F) | 0x10) # Mode 1, sleep
        self._write(0xfe, prescale) # Prescale
        self._write(0x00, old_mode) # Mode 1
        sleep_us(5)
        self._write(0x00, old_mode | 0xa1) # Mode 1, autoincrement on

    def pwm(self, index, on=None, off=None):
        if on is None or off is None:
            data = self.i2c.readfrom_mem(self.address, 0x06 + 4 * index, 4)
            return struct.unpack('<HH', data)
        data = struct.pack('<HH', on, off)
        self.i2c.writeto_mem(self.address, 0x06 + 4 * index,  data)

    def jambytes(self, thebytes, start=0):
        """
        The jambytes method accepts a preformatted bytearray with up to 16x 16-bit pairs
        of on and off values and streams them out to the pca9685 board in autoincrement mode.
        Generally starts at location 0 and writes all the pairs to the board.
        This should be the fastest way to set all 16 PWM duty cycles.
        """
        old_mode = self._read(0x00) # Mode 1
        self._write(0x00, old_mode | 0xa1) # Mode 1, autoincrement on
        self.i2c.writeto_mem(self.address, 0x06 + 4 * start, thebytes)
        self._write(0x00, old_mode) # Mode 1, original mode

    def allpwm(self, off=None, on=None, start=0):
        """
        The method allpwm implements use of autoincrement to allow faster writing
        of multiple servos.  Autoincrement begins at an address and writes bits
        into the registers of the pca9685 chip to control the on and off times.
        By default, the ON values are set to 0 for all servos being set but the
        user may override them if they want to.  The OFF values generally represent
        the duty cycle of the output when the ON values are 0.
            member of class: PCA9685
        Parameters
        ----------
            self : PCA9685
            off=None : array of up to 16 off values ranging from 0 to 4095
            on=None : array of same size of on values ranging from 0 to 4095
            start=0 : first address to write to (0-15)
        """
        if off is None:
            retdata = []
            for i in range(16):
                data = self.i2c.readfrom_mem(self.address, 0x06 + 4 * i, 4)
                retdata.append(struct.unpack('<HH', data))
            return retdata
        bytes = bytearray(b'')
        for i in range(len(off)):
            if on is not None and i < len(on): onval = on[i]
            else: onval = 0
            bytes.extend(bytearray(struct.pack('<HH', onval, off[i])))
        self.jambytes(bytes, start)

    def duty(self, index, value=None, invert=False):
        if value is None:
            pwm = self.pwm(index)
            if pwm == (0, 4096):
                value = 0
            elif pwm == (4096, 0):
                value = 4095
            value = pwm[1]
            if invert:
                value = 4095 - value
            return value
        if not 0 <= value <= 4095:
            raise ValueError("Out of range")
        if invert:
            value = 4095 - value
        if value == 0:
            self.pwm(index, 0, 4096)
        elif value == 4095:
            self.pwm(index, 4096, 0)
        else:
            self.pwm(index, 0, value)
