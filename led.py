import RPi.GPIO as GPIO
import logging
import time

class LED(object):
    _colors = {
        'white': (255, 255, 255),
        'yellow': (255, 255, 0),
        'pink': (255, 20, 147),
        'red': (255, 0, 0),
        'green': (0, 255, 0),
        'orange': (255,165,0),
        'blue': (0, 0, 255),
        'purple': (255, 0, 255),
        'off': (0, 0, 0),
    }

    def __init__(self, red, green, blue, initial_color='off'):
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(red, GPIO.OUT)
        GPIO.setup(green, GPIO.OUT)
        GPIO.setup(blue, GPIO.OUT)
        
        self.red = GPIO.PWM(red, 100)
        self.green = GPIO.PWM(green, 100)
        self.blue = GPIO.PWM(blue, 100)

        self.red.start(0)
        self.green.start(0)
        self.blue.start(0)


    def _set(self, rgb):
        rgb = [(x / 255.0) * 100 for x in rgb]

        self.red.ChangeDutyCycle(rgb[0])
        self.red.ChangeDutyCycle(rgb[1])
        self.red.ChangeDutyCycle(rgb[2])

    def set(self, color):
        logging.info('setting led color to %s', color)
        self._current_color = color
        self._set(self._colors[color])

    def blink(self, times=3, duration=100):
        logging.info('blink')
        for _ in xrange(times):
            oldcolor = self._current_color
            self.set('off')
            time.sleep(duration/1000)
            self.set(oldcolor)
            time.sleep(duration/1000)
