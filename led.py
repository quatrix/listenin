import RPi.GPIO as GPIO

class LED(object):
    _colors = {
        'white': (0, 0, 0),
        'red': (0, 1, 1),
        'green': (1, 0, 1),
        'blue': (1, 1, 0),
        'purple': (0, 1, 0),
        'off': (1, 1, 1),
    }

    def __init__(self, red, green, blue):
        self.pins = (red, green, blue)

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pins, GPIO.OUT)

    def _set(self, color):
        for pin, state in zip(self.pins, color):
            logging.debug('_set: %r %r', pin, state)
            GPIO.output(pin, state)

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
