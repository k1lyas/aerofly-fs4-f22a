"""The missile launch sound (0.9.2, weapons_f22.py), written to sounds/cockpit (44.1 kHz mono 16 bit; the converter
makes the .tsb), two layers played at the motor's ignition:

  missile_launch.wav      outside: the recording as heard on the ground beside a launch - the motor lighting with a
                          crack and its roar going away. Played at the missile's own body, so the game moves it away
                          with the missile (distance, Doppler).
  missile_launch_int.wav  in the cockpit: only the motor lighting - about a second, muffled by the sealed canopy and
                          the helmet, then gone (2026-11-25: inside one hears the first second as the motor
                          lights, not the missile going away; the first cut ran the whole 6 s): low-passed, quieter.

Source (Freesound, CC0; work/launch_sources, not in the repository, author in release/CREDITS.md):
  182794  qubodup  'Rocket Launch.flac' - three rocket launches from a US Government video (public domain); the first
                   (0.5 - 6.75 s) is used

    uv run --with numpy --with scipy python3 make_launch_sound.py        (F22_SOUND_OUT=<dir> for a trial folder)
"""
import os, subprocess
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'work', 'launch_sources', '182794__qubodup__rocket-launch.flac')
OUT = os.environ.get('F22_SOUND_OUT') or os.path.join(HERE, 'sounds', 'cockpit')
SR = 44100
CUT = (0.50, 6.75)          # s: the first launch, from just before its onset to the silence after it
FADE_OUT = 0.8              # s
INT_LOWPASS = 750.0         # Hz: the canopy and helmet take the top off (the F-15E's cockpit loops are dark too)
INT_GAIN = 0.35             # the inside layer against the outside one
INT_LENGTH, INT_FADE = 1.3, 0.7     # s: the cockpit hears the ignition, then the sound dies away over INT_FADE


def load():
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', SRC, '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def shape(x):
    a, b = (int(t * SR) for t in CUT)
    y = x[a:b].copy()
    y -= y.mean()
    n_in, n_out = int(0.005 * SR), int(FADE_OUT * SR)
    y[:n_in] *= np.linspace(0.0, 1.0, n_in)
    y[-n_out:] *= np.linspace(1.0, 0.0, n_out) ** 2
    return y


def save(name, y, peak):
    y = y * (peak / max(1e-9, np.abs(y).max()))
    os.makedirs(OUT, exist_ok=True)
    wavfile.write(os.path.join(OUT, name), SR, (np.clip(y, -1, 1) * 32767).astype(np.int16))
    print('%s: %.2f s, peak %.2f' % (name, len(y) / SR, peak))


def main():
    y = shape(load())
    save('missile_launch.wav', y, 0.89)
    # inside: low-passed twice over (24 dB / octave), a little of the body kept below 120 Hz - the airframe's thump
    lp = sosfiltfilt(butter(4, INT_LOWPASS, 'low', fs=SR, output='sos'), y)
    low = sosfiltfilt(butter(2, 120.0, 'low', fs=SR, output='sos'), y)
    inside = (lp + 0.5 * low)[:int(INT_LENGTH * SR)]
    n = int(INT_FADE * SR)
    inside[-n:] *= np.linspace(1.0, 0.0, n) ** 2
    save('missile_launch_int.wav', inside, 0.89 * INT_GAIN)


if __name__ == '__main__':
    main()
