import machine
import utime
import uos
led_onboard = machine.Pin(25, machine.Pin.OUT)

# Set up serial connection
uart = machine.UART(0, baudrate=115200)
uart.init(115200, bits=8, parity=None, stop=1, tx=machine.Pin(0), rx=machine.Pin(1))
# uos.dupterm(uart)
# i2c=I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=400000)

while True:
    # Blink LED at 1 Hz until button pressed
    rate = 1
    led_onboard.toggle()
    while True:
        if uart.any() > 0:
            value = uart.read(1)
            rate /= 2.0
            print(value.decode('utf-8'))
        led_onboard.toggle()
        utime.sleep(rate)

