"""Cockpit sounds of the F-22, written to sounds/cockpit (22.05 kHz mono 16 bit, as the SDK samples; the converter makes the .tsb).

    Blender --background --factory-startup --python make_cockpit_sounds.py        (needs numpy; voices need macOS `say`)

Voices: since 2026-11-16 make_voices_kokoro.py writes voice_*.wav (Kokoro-82M, Apache 2.0, voice af_heart chosen by ear by the user) - this
script leaves them alone. The old way, macOS Samantha through the same intercom band (personal, non-commercial use only, never for a published
package), still runs with F22_MACOS_VOICES=1. The rest is synthesised here, ours:
  flow_noise - air along the canopy, broadband and soft: quiet in a pressurised cockpit, no whistle
  buffet     - low rumble of the airframe near the limits
  marker_*   - ILS marker tones as on any receiver: outer 400 Hz dashes, middle 1300 Hz dot-dash, inner 3000 Hz dots
  vox_tone   - one short 1 kHz beep, played at the new level on each click of the VOX volume knob
  stall_bang - compressor stall / flameout: one blunt shotgun-like blast, weight in 150-500 Hz, a short rumble (failures_f22.py)
  engine_rough - a damaged engine running rough: a low uneven grumble, loud as the VIB climbs (failures_f22.py)
  seize_grind  - the rotor seizing: a heavy thud, a short clank, a rough grind fading over ~1.5 s (failures_f22.py)
Loops are periodic by construction (random-phase spectra, keying on whole cycles of the loop).
"""
import os, subprocess, tempfile, wave
import numpy as np

SR = 22050
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sounds', 'cockpit')
RNG = np.random.default_rng(22)


def write(name, x):
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, name + '.wav'), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    print('%-14s %.2f s peak %.2f rms %.3f' % (name, len(x) / SR, np.abs(x).max(), np.sqrt((x ** 2).mean())))


def bandpass(x, low, high, order=4):
    """Butterworth magnitude in the frequency domain, padded so that a phrase does not wrap round."""
    n = len(x) + SR // 2
    f = np.fft.rfftfreq(n, 1.0 / SR)
    with np.errstate(divide='ignore'):
        g = 1 / np.sqrt(1 + (low / np.maximum(f, 1e-3)) ** (2 * order)) / np.sqrt(1 + (f / high) ** (2 * order))
    return np.fft.irfft(np.fft.rfft(x, n) * g, n)[:len(x)]


def voice(name, text, rate=165):
    if not os.environ.get('F22_MACOS_VOICES'):       # the voices are make_voices_kokoro.py's
        return
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, 'v.aiff'), os.path.join(d, 'v.wav')
        subprocess.check_call(['say', '-v', 'Samantha', '-r', str(rate), '-o', a, text])
        subprocess.check_call(['afconvert', '-f', 'WAVE', '-d', 'LEI16@%d' % SR, '-c', '1', a, b])
        with wave.open(b) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), '<i2') / 32768.0
    on = np.nonzero(np.abs(x) > 0.01)[0]
    x = x[max(0, on[0] - 110):on[-1] + 440]
    y = bandpass(x, 320.0, 3800.0)
    y = y * 0.2 / np.sqrt((y ** 2).mean())
    y = np.tanh(2.2 * y) / np.tanh(2.2)                    # a little saturation, as a headset
    y = y * 0.16 / np.sqrt((y ** 2).mean())
    y = y * min(1.0, 0.85 / np.abs(y).max())
    n = min(220, len(y) // 4)
    y[:n] *= np.linspace(0, 1, n)
    y[-n:] *= np.linspace(1, 0, n)
    write(name, y)


def loop_noise(seconds, shape, level):
    n = int(SR * seconds)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    spec = shape(f) * np.exp(2j * np.pi * RNG.random(len(f)))
    spec[0] = 0
    x = np.fft.irfft(spec, n)
    return x * level / np.sqrt((x ** 2).mean())


def keyed(freq, pattern, seconds=2.0, level=0.3):
    """Tone keyed by [(start, length)] in seconds, repeated over the loop; whole cycles of the tone per loop."""
    n = int(SR * seconds)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * round(freq * seconds) / seconds * t)
    env = np.zeros(n)
    for start, length in pattern:
        a, b = int(start * SR), int((start + length) * SR)
        ramp = min(66, (b - a) // 4)
        e = np.ones(b - a)
        e[:ramp] = np.linspace(0, 1, ramp)
        e[-ramp:] = np.linspace(1, 0, ramp)
        env[a:b] = e
    return tone * env * level


voice('voice_pullup', 'Pull up.')
voice('voice_altitude', 'Altitude.')
voice('voice_bingo', 'Bingo fuel.')
voice('voice_overg', 'Over G.')
write('flow_noise', loop_noise(6.0, lambda f: 1 / np.sqrt(1 + (f / 500.0) ** 2) / np.sqrt(1 + (120.0 / np.maximum(f, 1.0)) ** 4), 0.18))
write('buffet', loop_noise(5.0, lambda f: 1 / np.sqrt(1 + (22.0 / np.maximum(f, 1.0)) ** 6) / (1 + (f / 90.0) ** 3), 0.25))
write('marker_outer', keyed(400.0, [(k * 0.5, 0.375) for k in range(4)]))            # dashes, 2 a second
write('marker_middle', keyed(1300.0, [(k * 2 / 3 + d, l) for k in range(3) for d, l in ((0.0, 0.1), (0.2, 0.37))]))    # dot-dash
write('marker_inner', keyed(3000.0, [(k / 6.0, 0.1) for k in range(12)]))              # dots, 6 a second
write('vox_tone', keyed(1000.0, [(0.0, 0.15)], seconds=0.2))                       # VOX knob click: one beep
# failures (failures_f22.py, 2026-11-09): fire and engine-out voices, the stall bang (made last: the noise above keeps its
# random numbers)
voice('voice_fire_left', 'Engine fire, left.')
voice('voice_fire_right', 'Engine fire, right.')
voice('voice_engine_left', 'Engine out, left.')
voice('voice_engine_right', 'Engine out, right.')
def rise(x, n=24):
    x[:n] *= np.linspace(0, 1, n)
    x[-400:] *= np.linspace(1, 0, 400)
    return x


# stall bang. In-game 2026-11-09: v1 55 Hz thump "muffled"; v2 + 70/140 Hz tones "a kick at an empty barrel" (pure
# tones ring); v3 broadband to 6 kHz + a second pop "something thrown at a metal fence, bouncing off" (the highs are
# metal, the second pop is the bounce). v4: one blunt shotgun-like blast - noise only, cut above 2.5 kHz, its weight
# in 150-500 Hz, a short low rumble after it; soft clipping for loudness
RNG = np.random.default_rng(101)      # own seed: a change to one sound leaves the others as they are
n_ = int(SR * 1.2)
t_ = np.arange(n_) / SR
punch = bandpass(RNG.standard_normal(n_), 60.0, 2500.0, order=3) * np.exp(-t_ / 0.045)
weight = bandpass(RNG.standard_normal(n_), 150.0, 500.0, order=3) * np.exp(-t_ / 0.09)
rumble = bandpass(RNG.standard_normal(n_), 40.0, 300.0, order=3) * np.exp(-t_ / 0.35)
bang = punch / np.abs(punch).max() + 0.9 * weight / np.abs(weight).max() + 0.4 * rumble / np.abs(rumble).max()
bang = np.tanh(2.2 * bang / np.abs(bang).max())
write('stall_bang', rise(bang * 0.95 / np.abs(bang).max(), 8))
# the feel block (failures_f22.py, 2026-11-09), after the stall bang for the same reason
RNG = np.random.default_rng(102)      # own seed: a change to one sound leaves the others as they are
n_ = int(SR * 4.0)
t_ = np.arange(n_) / SR
grumble = loop_noise(4.0, lambda f: 1 / np.sqrt(1 + (60.0 / np.maximum(f, 1.0)) ** 4) / (1 + (f / 320.0) ** 3), 1.0)
env = 0.55 + 0.25 * np.sin(2 * np.pi * 7.0 * t_) + 0.15 * np.sin(2 * np.pi * 11.25 * t_ + 1.0) \
    + 0.1 * np.sin(2 * np.pi * 3.25 * t_ + 2.0)          # whole cycles per 4 s loop: 28, 45, 13
write('engine_rough', grumble * env * 0.9 / np.abs(grumble * env).max())
# rotor seizing. In-game 2026-11-09: v1 high screech "the radio"; v2 slowing pulses over a low groan "a stick in a
# fan" (right) "or a fart"; v3 stepped random scraping to 6 kHz "steel balls poured on a sheet / firecrackers" (each
# 10 ms step clicked). v4: a heavy dull thud, a short low clank, then one rough grinding noise (300-2000 Hz) swelling
# and fading smoothly over ~1.5 s - no steps, no tones that ring; the engine's own sound runs down with N2 meanwhile
RNG = np.random.default_rng(103)
n_ = int(SR * 2.0)
t_ = np.arange(n_) / SR
thud = bandpass(RNG.standard_normal(n_), 50.0, 700.0, order=3) * np.exp(-t_ / 0.07)
clank = bandpass(RNG.standard_normal(n_), 600.0, 1800.0, order=4) * np.exp(-t_ / 0.03)
wobble = bandpass(RNG.standard_normal(n_), 2.0, 12.0, order=2)            # smooth roughness, 2-12 Hz
wobble = 0.6 + 0.4 * wobble / np.abs(wobble).max()
grind_env = np.clip(t_ / 0.08, 0, 1) * np.clip(1 - (t_ - 0.08) / 1.5, 0, 1) ** 1.3
grind = bandpass(RNG.standard_normal(n_), 300.0, 2000.0, order=3) * wobble * grind_env
x = thud / np.abs(thud).max() + 0.35 * clank / np.abs(clank).max() + 0.55 * grind / np.abs(grind).max()
x = np.tanh(1.8 * x / np.abs(x).max())
write('seize_grind', rise(x * 0.9 / np.abs(x).max(), 8))
# landing gear failures (failures_f22.py, 2026-11-13): a leg breaking under the aircraft, then the airframe sliding on
# the runway on its belly / the broken leg
#   gear_crunch  - a heavy dull impact, a sharp crack of breaking metal, a groan of bending, a few clanks of loose parts
#   belly_scrape - metal grinding on concrete: gritty broadband 400 Hz - 5 kHz, rough and uneven, a low airframe rumble
#                  under it (loop, volume and pitch by ground speed)
RNG = np.random.default_rng(104)
n_ = int(SR * 1.6)
t_ = np.arange(n_) / SR
impact = bandpass(RNG.standard_normal(n_), 40.0, 450.0, order=3) * np.exp(-t_ / 0.10)
crack = bandpass(RNG.standard_normal(n_), 1500.0, 7000.0, order=3) * np.exp(-t_ / 0.012)
groan_env = np.clip((t_ - 0.03) / 0.06, 0, 1) * np.exp(-np.clip(t_ - 0.09, 0, None) / 0.35)
groan = bandpass(RNG.standard_normal(n_), 140.0, 600.0, order=4) * groan_env
clanks = np.zeros(n_)
for k, at in enumerate(sorted(RNG.uniform(0.08, 0.9, 6))):
    a = int(at * SR)
    tt = np.arange(n_ - a) / SR
    clanks[a:] += bandpass(RNG.standard_normal(n_ - a), 900.0, 3500.0, order=3) * np.exp(-tt / 0.018) * (0.8 ** k)
x = impact / np.abs(impact).max() + 0.7 * crack / np.abs(crack).max() + 0.5 * groan / np.abs(groan).max() \
    + 0.35 * clanks / np.abs(clanks).max()
x = np.tanh(2.0 * x / np.abs(x).max())
write('gear_crunch', rise(x * 0.95 / np.abs(x).max(), 8))
RNG = np.random.default_rng(105)
grit = loop_noise(4.0, lambda f: 1 / np.sqrt(1 + (400.0 / np.maximum(f, 1.0)) ** 4) / np.sqrt(1 + (f / 5000.0) ** 4), 1.0)
rough = loop_noise(4.0, lambda f: 1 / (1 + (f / 18.0) ** 4) / np.sqrt(1 + (2.0 / np.maximum(f, 0.25)) ** 2), 1.0)
rough = 0.55 + 0.45 * rough / np.abs(rough).max()
low = loop_noise(4.0, lambda f: 1 / np.sqrt(1 + (45.0 / np.maximum(f, 1.0)) ** 4) / (1 + (f / 220.0) ** 3), 1.0)
x = grit * rough + 0.6 * low
write('belly_scrape', x * 0.85 / np.abs(x).max())
