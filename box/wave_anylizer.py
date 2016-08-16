"""
CREDIT:
-------

most of the code in this file were written by @endolith (https://github.com/endolith)
specificly in https://github.com/endolith/waveform-analyzer, i just copy-pasted bits from his code!

endolith, if you're reading this, many thanks!
"""


from __future__ import division
from scikits.audiolab import Sndfile
from numpy import absolute, argmax, log
from numpy.fft import rfft
from scipy.signal import kaiser
import sys


def load(filename):
    """
    Load a wave file and return the signal, sample rate and number of channels.

    Can be any format that libsndfile supports, like .wav, .flac, etc.
    """
    wave_file = Sndfile(filename, 'r')
    signal = wave_file.read_frames(wave_file.nframes)
    sample_rate = wave_file.samplerate
    return signal, sample_rate, wave_file.nframes
 

def freq_from_fft(signal, fs):
    """Estimate frequency from peak of FFT
    
    Pros: Accurate, usually even more so than zero crossing counter 
    (1000.000004 Hz for 1000 Hz, for instance).  Due to parabolic 
    interpolation being a very good fit for windowed log FFT peaks?
    https://ccrma.stanford.edu/~jos/sasp/Quadratic_Interpolation_Spectral_Peaks.html
    Accuracy also increases with signal length
    
    Cons: Doesn't find the right value if harmonics are stronger than
    fundamental, which is common.
    
    """
    N = len(signal)
    
    # Compute Fourier transform of windowed signal
    windowed = signal * kaiser(N, 100)
    f = rfft(windowed)
    # Find the peak and interpolate to get a more accurate peak
    i_peak = argmax(abs(f)) # Just use this value for less-accurate result
    i_interp = parabolic(log(abs(f)), i_peak)[0]
    
    # Convert to equivalent frequency
    return fs * i_interp / N # Hz


def parabolic(f, x):
    """
    Quadratic interpolation for estimating the true position of an
    inter-sample maximum when nearby samples are known.

    f is a vector and x is an index for that vector.

    Returns (vx, vy), the coordinates of the vertex of a parabola that goes
    through point x and its two neighbors.

    Example:
    Defining a vector f with a local maximum at index 3 (= 6), find local
    maximum if points 2, 3, and 4 actually defined a parabola.

    In [3]: f = [2, 3, 1, 6, 4, 2, 3, 1]

    In [4]: parabolic(f, argmax(f))
    Out[4]: (3.2142857142857144, 6.1607142857142856)
    """
    xv = 1/2. * (f[x-1] - f[x+1]) / (f[x-1] - 2 * f[x] + f[x+1]) + x
    yv = f[x] - 1/4. * (f[x-1] - f[x+1]) * (xv - x)
    return (xv, yv)


def is_noise(signal, sample_rate):
    freq = freq_from_fft(signal, sample_rate)
    return 50.6 > freq > 49.4 or freq < 4


def is_silence(signal):
    peak_level = max(absolute(signal))
    return peak_level < 0.03
    

class Wave(object):
    def __init__(self, filename):
        signal, sample_rate, samples = load(filename)
        self.length = samples / sample_rate

        self.is_silence = False
        self.is_noise = False

        if is_silence(signal):
            self.is_silence = True
        elif is_noise(signal, sample_rate):
            self.is_noise = True


if __name__ == '__main__':
    n = Wave(sys.argv[1])

    if n.is_silence:
        print(sys.argv[1], n.length, 'SILENCE')
    elif n.is_noise:
        print(sys.argv[1], n.length, 'NOISE')
    else:
        print(sys.argv[1], n.length, 'MUSIC')
