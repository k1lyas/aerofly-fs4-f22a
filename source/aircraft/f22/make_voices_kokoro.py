"""Cockpit voices of the F-22 with a freely licensed synthesiser, for the published package.

    uv run --python 3.12 --with kokoro --with soundfile --with pip make_voices_kokoro.py samples
    uv run --python 3.12 --with kokoro --with soundfile --with pip make_voices_kokoro.py final <voice>

Kokoro-82M (hexgrad/Kokoro-82M on Hugging Face), model weights under Apache 2.0 - unlike the macOS system voices of
make_cockpit_sounds.py (personal, non-commercial use only), its output can go into the GPL-3 package. `samples` writes
one phrase per candidate voice, clean and through the intercom band, into work/voice_samples_kokoro/ for the user to
choose by ear; `final` writes the eight phrases into sounds/cockpit/voice_*.wav (22.05 kHz mono 16 bit, as the other
cockpit sounds; ./build.sh convert makes the .tsb). The intercom chain is make_cockpit_sounds.voice()'s own.
"""
import os, sys, wave
import numpy as np

SR = 22050
HERE = os.path.dirname(os.path.abspath(__file__))
# (PULL UP with its phonemes spelled out and 'up' fully stressed: 'Pull up.' read the 'up' unstressed, user 2026-11-17)
PHRASES = [('voice_pullup', '[Pull](/pˈʊl/) [up](/ˈʌp/)!'), ('voice_altitude', 'Altitude.'), ('voice_bingo', 'Bingo fuel.'),
           ('voice_overg', 'Over G.'), ('voice_fire_left', 'Engine fire, left.'), ('voice_fire_right', 'Engine fire, right.'),
           ('voice_engine_left', 'Engine out, left.'), ('voice_engine_right', 'Engine out, right.')]
CANDIDATES = ['af_heart', 'af_bella', 'af_sarah', 'af_kore', 'af_nicole', 'bf_emma']
SAMPLE_TEXT = 'Pull up. Altitude. Bingo fuel. Engine fire, left.'
_pipes = {}


def synth(text, voice, speed=1.0):
    from kokoro import KPipeline
    lang = voice[0]                                   # a = American, b = British English
    if lang not in _pipes:
        _pipes[lang] = KPipeline(lang_code=lang, repo_id='hexgrad/Kokoro-82M')
    parts = [np.asarray(audio, dtype=np.float64) for _, _, audio in _pipes[lang](text, voice=voice, speed=speed)]
    x = np.concatenate(parts)                         # 24 kHz
    n = int(round(len(x) * SR / 24000.0))             # -> 22.05 kHz, band-limited
    spec = np.fft.rfft(x)
    return np.fft.irfft(spec[:n // 2 + 1], n) * n / len(x)


def bandpass(x, low, high, order=4):
    n = len(x) + SR // 2
    f = np.fft.rfftfreq(n, 1.0 / SR)
    with np.errstate(divide='ignore'):
        g = 1 / np.sqrt(1 + (low / np.maximum(f, 1e-3)) ** (2 * order)) / np.sqrt(1 + (f / high) ** (2 * order))
    return np.fft.irfft(np.fft.rfft(x, n) * g, n)[:len(x)]


def trim(x):
    on = np.nonzero(np.abs(x) > 0.01 * np.abs(x).max())[0]
    return x[max(0, on[0] - 110):on[-1] + 440]


def intercom(x):
    """make_cockpit_sounds.voice(): narrow band, a little saturation as a headset, levelled, short fades."""
    y = bandpass(x, 320.0, 3800.0)
    y = y * 0.2 / np.sqrt((y ** 2).mean())
    y = np.tanh(2.2 * y) / np.tanh(2.2)
    y = y * 0.16 / np.sqrt((y ** 2).mean())
    y = y * min(1.0, 0.85 / np.abs(y).max())
    n = min(220, len(y) // 4)
    y[:n] *= np.linspace(0, 1, n)
    y[-n:] *= np.linspace(1, 0, n)
    return y


def final_stop(x):
    """(closure start, release start) of a phrase-final plosive - the last stretch of near silence (30 ms or more under
    3 % of the peak envelope) with a short sound after it; None if the phrase ends otherwise."""
    win = int(0.005 * SR)
    env = np.sqrt(np.convolve(x ** 2, np.ones(win) / win, 'same'))
    quiet = env < 0.03 * env.max()
    k = len(x) - 1
    while k > 0 and quiet[k]:          # the silence after the release
        k -= 1
    end = k
    while k > 0 and not quiet[k]:      # the release
        k -= 1
    release = k + 1
    while k > 0 and quiet[k]:          # the closure
        k -= 1
    closure = k + 1
    if release - closure < 0.03 * SR or end - release > 0.2 * SR:
        return None
    return closure, release


def harden(x):
    """A final p / t unreleased (user 2026-11-17: 'PULL UP' ended in a soft 'пь', 'LEFT' in 'ть' - Kokoro releases a
    final stop with ~70 ms of hiss above 3 kHz, the English aspiration a Russian ear hears as softness; of three
    versions - no release, a 15 ms release, a 15 ms release low-passed - the user took the one without): the phrase
    ends 20 ms into the closure."""
    st = final_stop(x)
    if st is None:
        return x
    y = x[:st[0] + int(0.02 * SR)].copy()
    n = int(0.004 * SR)
    y[-n:] *= np.linspace(1, 0, n)
    return y


def write(path, x):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    print('%-52s %.2f s  peak %.2f' % (os.path.relpath(path, HERE), len(x) / SR, np.abs(x).max()))


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'samples'
    if mode == 'samples':
        out = os.path.join(HERE, 'work', 'voice_samples_kokoro')
        for v in (sys.argv[2:] or CANDIDATES):
            x = trim(synth(SAMPLE_TEXT, v))
            write(os.path.join(out, v + '_clean.wav'), x * 0.7 / np.abs(x).max())
            write(os.path.join(out, v + '_intercom.wav'), intercom(x))
    elif mode == 'final':
        voice = sys.argv[2]
        speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
        for name, text in PHRASES:
            x = trim(synth(text, voice, speed))
            print('%-20s final stop %s' % (name, 'cut' if final_stop(x) else '-'))
            write(os.path.join(HERE, 'sounds', 'cockpit', name + '.wav'), intercom(harden(x)))
    else:
        raise SystemExit(__doc__)
