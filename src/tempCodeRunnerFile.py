import numpy as np
import sounddevice as sd
import time
from scipy.signal import convolve

def generate_sine_wave(frequency, duration, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    waveform = 0.5 * np.sin(2 * np.pi * frequency * t)
    return waveform

def apply_hall_reverb(waveform, sample_rate=44100, decay=0.5):
    reverb_kernel = np.exp(-decay * np.arange(0, sample_rate) / sample_rate)
    reverb_kernel /= np.sum(reverb_kernel)
    reverb_waveform = convolve(waveform, reverb_kernel, mode='full')[:len(waveform)]
    return reverb_waveform

def main():
    frequency = 440  # A4 note
    duration = 2.0  # seconds
    sample_rate = 44100

    print("Generating sine wave...")
    sine_wave = generate_sine_wave(frequency, duration, sample_rate)

    print("Playing sound...")
    sd.play(sine_wave, sample_rate)
    sd.wait()
    print("Done playing sound.")

    print("Waiting for 2 seconds...")
    time.sleep(2)
    print("Done.")

if __name__ == "__main__":
    main()