import numpy as np
import sounddevice as sd
import tkinter as tk
from tkinter import ttk

class RealtimeSynth:
    def __init__(self, sample_rate=48000):
        self.sample_rate = sample_rate
        self.notes = {}
        self.waveform_type = 'sine'
        self.stream = None
        self.attack = 0.01
        self.decay = 0.1
        self.sustain = 0.7
        self.release = 0.1

    def sine_wave(self, t, freq):
        return 0.3 * np.sin(2 * np.pi * freq * t)

    def sawtooth_wave(self, t, freq):
        return 0.3 * (2 * (t * freq - np.floor(0.5 + t * freq)))

    def square_wave(self, t, freq):
        return 0.3 * np.sign(np.sin(2 * np.pi * freq * t))

    def triangle_wave(self, t, freq):
        return 0.3 * (2 * np.abs(2 * (t * freq - np.floor(0.5 + t * freq))) - 1)

    def generate_waveform(self, t, freq):
        if self.waveform_type == 'sine':
            return self.sine_wave(t, freq)
        elif self.waveform_type == 'sawtooth':
            return self.sawtooth_wave(t, freq)
        elif self.waveform_type == 'square':
            return self.square_wave(t, freq)
        elif self.waveform_type == 'triangle':
            return self.triangle_wave(t, freq)

    def generate_adsr_envelope(self, note_state, note_phase):
        attack_samples = int(self.attack * self.sample_rate)
        decay_samples = int(self.decay * self.sample_rate)
        release_samples = int(self.release * self.sample_rate)

        if note_state == 'pressed':
            if note_phase < attack_samples:
                return note_phase / attack_samples
            elif note_phase < attack_samples + decay_samples:
                return 1 - (1 - self.sustain) * (note_phase - attack_samples) / decay_samples
            else:
                return self.sustain
        elif note_state == 'released':
            if note_phase < release_samples:
                return self.sustain * (1 - note_phase / release_samples)
            else:
                return 0

    def audio_callback(self, outdata, frames, time, status):
        if status:
            print(status)
        t = np.arange(frames) / self.sample_rate
        waveform = np.zeros(frames, dtype=np.float32)
        for freq, (note_state, note_phase) in list(self.notes.items()):
            wave = self.generate_waveform(t + note_phase / self.sample_rate, freq)
            envelope = np.array([self.generate_adsr_envelope(note_state, note_phase + i) for i in range(frames)])
            wave *= envelope
            waveform += wave
            if note_state == 'pressed':
                self.notes[freq] = (note_state, note_phase + frames)
            elif note_state == 'released':
                if note_phase + frames >= int(self.release * self.sample_rate):
                    del self.notes[freq]
                else:
                    self.notes[freq] = (note_state, note_phase + frames)
        outdata[:] = waveform.reshape(-1, 1)

    def start(self):
        if self.stream:
            self.stop()
        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=1,
            callback=self.audio_callback,
            blocksize=1024,
            dtype='float32'
        )
        self.stream.start()

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

class SynthesizerApp(tk.Tk):
    def __init__(self, sample_rate=44100):
        super().__init__()
        self.synth = RealtimeSynth(sample_rate)
        self.synth.start()  # Start continuous audio
        self.title("Synthesizer")
        self.geometry("800x400")
        self.waveform_type = tk.StringVar(value='sine')
        self.current_octave = 4
        self.pressed_keys = set()
        self.create_widgets()
        self.bind_keys()

    def create_widgets(self):
        waveforms = ['sine', 'sawtooth', 'square', 'triangle']
        for i, waveform in enumerate(waveforms):
            radio_button = tk.Radiobutton(self, text=waveform.capitalize(), variable=self.waveform_type, value=waveform, command=self.update_waveform_type)
            radio_button.grid(row=0, column=i, padx=5, pady=5)

        self.canvas_frame = tk.Frame(self)
        self.canvas_frame.grid(row=1, column=0, columnspan=4, sticky='nsew')

        self.canvas = tk.Canvas(self.canvas_frame, bg='white', height=200)
        self.scrollbar = tk.Scrollbar(self.canvas_frame, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.scrollbar.grid(row=1, column=0, sticky='ew')

        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        self.white_key_width = 60
        self.white_key_height = 200
        self.black_key_width = 40
        self.black_key_height = 120

        self.white_keys = []
        self.black_keys = []

        for octave in range(1, 9):  # Start from C1 to C8
            base_freq = 32.70 * (2 ** (octave - 1))  # C1 frequency is 32.70 Hz
            self.white_keys.extend([
                ('C', base_freq),
                ('D', base_freq * (9/8)),
                ('E', base_freq * (5/4)),
                ('F', base_freq * (4/3)),
                ('G', base_freq * (3/2)),
                ('A', base_freq * (5/3)),
                ('B', base_freq * (15/8)),
            ])
            self.black_keys.extend([
                ('C#', base_freq * (16/15)),
                ('D#', base_freq * (6/5)),
                None,
                ('F#', base_freq * (25/18)),
                ('G#', base_freq * (8/5)),
                ('A#', base_freq * (9/5)),
                None,
            ])

        for i, (note, freq) in enumerate(self.white_keys):
            button = tk.Button(self.canvas, bg='white', fg='black')
            button.bind('<ButtonPress-1>', lambda event, n=note: self.key_press(event, n))
            button.bind('<ButtonRelease-1>', lambda event, n=note: self.key_release(event, n))
            self.canvas.create_window(i * self.white_key_width, 0, anchor='nw', window=button, width=self.white_key_width, height=self.white_key_height)

        for i, key in enumerate(self.black_keys):
            if key is not None:
                note, freq = key
                button = tk.Button(self.canvas, bg='black', fg='white')
                button.bind('<ButtonPress-1>', lambda event, n=note: self.key_press(event, n))
                button.bind('<ButtonRelease-1>', lambda event, n=note: self.key_release(event, n))
                self.canvas.create_window((i + 0.75) * self.white_key_width, 0, anchor='nw', window=button, width=self.black_key_width, height=self.black_key_height)

        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

        # ADSR Controls
        adsr_frame = tk.Frame(self)
        adsr_frame.grid(row=2, column=0, columnspan=4, pady=10)

        tk.Label(adsr_frame, text="Attack").grid(row=0, column=0)
        self.attack_slider = ttk.Scale(adsr_frame, from_=0.01, to=1.0, value=self.synth.attack, command=self.update_attack)
        self.attack_slider.grid(row=1, column=0, padx=5)

        tk.Label(adsr_frame, text="Decay").grid(row=0, column=1)
        self.decay_slider = ttk.Scale(adsr_frame, from_=0.01, to=1.0, value=self.synth.decay, command=self.update_decay)
        self.decay_slider.grid(row=1, column=1, padx=5)

        tk.Label(adsr_frame, text="Sustain").grid(row=0, column=2)
        self.sustain_slider = ttk.Scale(adsr_frame, from_=0.0, to=1.0, value=self.synth.sustain, command=self.update_sustain)
        self.sustain_slider.grid(row=1, column=2, padx=5)

        tk.Label(adsr_frame, text="Release").grid(row=0, column=3)
        self.release_slider = ttk.Scale(adsr_frame, from_=0.01, to=1.0, value=self.synth.release, command=self.update_release)
        self.release_slider.grid(row=1, column=3, padx=5)

    def bind_keys(self):
        key_note_map = {
            'a': 'C', 'w': 'C#', 's': 'D', 'e': 'D#', 'd': 'E', 'f': 'F', 't': 'F#',
            'g': 'G', 'z': 'G#', 'h': 'A', 'u': 'A#', 'j': 'B', 'k': 'C', 'o': 'C#',
            'l': 'D', 'p': 'D#', ';': 'E', "'": 'F'
        }
        for key, note in key_note_map.items():
            self.bind(f'<KeyPress-{key}>', lambda event, n=note: self.key_press(event, n))
            self.bind(f'<KeyRelease-{key}>', lambda event, n=note: self.key_release(event, n))

        self.bind('<KeyPress-x>', self.increase_octave)
        self.bind('<KeyPress-y>', self.decrease_octave)

    def key_press(self, event, note):
        self.pressed_keys.add(note)
        self.update_pressed_keys_display()
        self.update_synth()

    def key_release(self, event, note):
        if note in self.pressed_keys:
            self.pressed_keys.remove(note)
        self.update_pressed_keys_display()
        self.update_synth()

    def update_synth(self):
        base_freq = 32.70 * (2 ** (self.current_octave - 1))  # C1 frequency is 32.70 Hz
        note_freq_map = {
            'C': base_freq,
            'C#': base_freq * (16/15),
            'D': base_freq * (9/8),
            'D#': base_freq * (6/5),
            'E': base_freq * (5/4),
            'F': base_freq * (4/3),
            'F#': base_freq * (25/18),
            'G': base_freq * (3/2),
            'G#': base_freq * (8/5),
            'A': base_freq * (5/3),
            'A#': base_freq * (9/5),
            'B': base_freq * (15/8),
        }
        for note in self.pressed_keys:
            freq = note_freq_map[note]
            if freq not in self.synth.notes:
                self.synth.notes[freq] = ('pressed', 0)
        for freq in list(self.synth.notes.keys()):
            if freq not in [note_freq_map[note] for note in self.pressed_keys]:
                self.synth.notes[freq] = ('released', 0)

    def update_waveform_type(self):
        self.synth.waveform_type = self.waveform_type.get()

    def update_attack(self, value):
        self.synth.attack = float(value)

    def update_decay(self, value):
        self.synth.decay = float(value)

    def update_sustain(self, value):
        self.synth.sustain = float(value)

    def update_release(self, value):
        self.synth.release = float(value)

    def update_pressed_keys_display(self):
        pressed_keys_str = ', '.join(self.pressed_keys)
        self.title(f"Synthesizer - Pressed Keys: {pressed_keys_str}")

    def increase_octave(self, event):
        if self.current_octave < 8:
            self.current_octave += 1
            print(f"Octave increased to {self.current_octave}")

    def decrease_octave(self, event):
        if self.current_octave > 1:
            self.current_octave -= 1
            print(f"Octave decreased to {self.current_octave}")

if __name__ == "__main__":
    app = SynthesizerApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        app.synth.stop()
        app.destroy()
        print("Synthesizer stopped and GUI closed")