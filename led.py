from __future__ import division
import RPi.GPIO as GPIO
import logging
import time
from threading import Lock

class LED(object):
    _colors = {
        'white': (255, 255, 255),
        'yellow': (255, 255, 0),
        'pink': (255, 20, 147),
        'red': (255, 0, 0),
        'green': (0, 255, 0),
        'orange': (255, 50, 0),
        'blue': (0, 0, 255),
        'purple': (255, 0, 255),
        'teal': (0, 128, 200),
        'gray': (1, 1, 1),
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

        self._lock = Lock()


    def _set(self, rgb):
        rgb = [100 - (x / 255.0) * 100 for x in rgb]

        self.red.ChangeDutyCycle(rgb[0])
        self.green.ChangeDutyCycle(rgb[1])
        self.blue.ChangeDutyCycle(rgb[2])

    def set(self, color, lock=True):
        try:
            if lock:
                self._lock.acquire()
            logging.info('setting led color to %s', color)
            self._current_color = color
            self._set(self._colors[color])
        finally:
            if lock:
                self._lock.release()

    def blink(self, duration=100):
        with self._lock:
            logging.info('blink')

            old_color = self._colors[self._current_color]
            new_color = [x/2 for x in old_color]

            self._set(new_color)
            time.sleep(duration / 1000)
            self._set(old_color)
