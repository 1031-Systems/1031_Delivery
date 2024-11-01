# servo.py
# Kevin McAleer and John Wright
# March 2021 and March 2024

#from pca import PCA9685
from pca9685 import PCA9685
import math
import time


class Servos:
    def __init__(self, i2c, address=0x40, freq=50, min_us=600, max_us=2400,
                 degrees=180):
        self.period = 1000000 / freq
        self.min_duty = self._us2duty(min_us)
        self.max_duty = self._us2duty(max_us)
        self.degrees = degrees
        self.freq = freq
        self.pca9685 = PCA9685(i2c, address)
        self.pca9685.freq(freq)
        self.positions = [0] * 16

    def _us2duty(self, value):
        return int(4095 * value / self.period)

    def position(self, index, degrees=None, radians=None, us=None, duty=None, push=True):
        ticks = time.ticks_us()
        if duty is not None:
            pass
        elif degrees is not None:
            span = self.max_duty - self.min_duty
            duty = self.min_duty + span * degrees / self.degrees
        elif radians is not None:
            span = self.max_duty - self.min_duty
            duty = self.min_duty + span * radians / math.radians(self.degrees)
        elif us is not None:
            duty = self._us2duty(us)
        elif duty is not None:
            pass
        else:
            return self.pca9685.duty(index)
        print('Conditional time:', time.ticks_diff(time.ticks_us(), ticks))
        #duty = min(self.max_duty, max(self.min_duty, int(duty)))
        ticks = time.ticks_us()
        self.positions[index] = duty
        print('Position time:', time.ticks_diff(time.ticks_us(), ticks))
        ticks = time.ticks_us()
        if push:
            self.pca9685.duty(index, duty)
        print('Push time:', time.ticks_diff(time.ticks_us(), ticks), 'push:', push)

    def duty(self, index, duty):
        self.positions[index] = duty

    def release(self, index):
        self.pca9685.duty(index, 0)

    def releaseAll(self):
        for i in range(16): self.positions[i] = 0
        self.pushValues()

    def pushValues(self):
        self.pca9685.allpwm(self.positions)
