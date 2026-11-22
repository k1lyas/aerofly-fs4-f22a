"""Damage sounds of the F-22 from real recordings, written to sounds/cockpit (44.1 kHz mono 16 bit; the converter makes
the .tsb): the gear leg breaking, the airframe sliding on the runway, the engine rotor seizing (played by failures_f22.py),
the tyre bursting, the compressor stall / flameout.

They replace the synthesised versions of make_cockpit_sounds.py (filtered noise at 22.05 kHz), heard in the game as
'sand in the ears, a rustling plastic bag, not metal' (user, 2026-11-21). Every layer is a real recording; the work is
the sound designer's: the recordings cleaned (their noise floor and the handling noise between events taken out), cut,
pitched down by resampling for the mass of an airframe, layered into a full event (impact, sub-boom, tearing metal,
debris, the airframe's rumble on concrete), then EQ, compression and the short reflection of the runway around it.
The first plain cut was 'weak, an amateur recording with the noise of his movements' (user, 2026-11-21).

Sources (Freesound, all CC0; work/damage_sources, not in the repository, authors in release/CREDITS.md):
  346299  PauliusI      'Car Crash_EXT.wav' - a real Peugeot 406 hitting a Ford Ka, boom mic, 48 kHz
  545544  rsellick      'kettlebell on concrete rock stone metal drag impact.wav'
  545562  rsellick      'kettlebell concrete drag metal rock stone earth.wav'
  452587  kyles         'crowbar metal drag on concrete scrape and handling.wav'
  450356  kyles         'metal gate open with anchor bar drag on concrete loud scrape and drop down hit resonate.flac'
  251759  misosound     'BOOMING PUNCHY EXPLOSION - close, big SCHOEPS MK41.wav' - a pyrotechnic blast on a film set
  159710  AnthonyChan0  'Mossberg 500A - 1 shot and pump' - a real shotgun in a wood

    uv run --with numpy --with scipy python3 make_damage_sounds.py        (F22_SOUND_OUT=<dir> for a trial folder)
"""
import os, subprocess, sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt, resample_poly, stft, istft, fftconvolve

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'work', 'damage_sources')
OUT = os.environ.get('F22_SOUND_OUT') or os.path.join(HERE, 'sounds', 'cockpit')
SR = 44100
RNG = np.random.default_rng(221)
_cache = {}


# ---------------------------------------------------------------- material
def source(fs_id):
    """A whole recording as mono float at 44.1 kHz, cleaned once (denoise)."""
    if fs_id not in _cache:
        names = [f for f in os.listdir(SRC) if f.startswith('%d__' % fs_id)]
        if not names:
            sys.exit('no Freesound original %d in %s' % (fs_id, SRC))
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(SRC, names[0]), '-ac', '1', '-ar', str(SR),
                              '-f', 's16le', '-'], capture_output=True, check=True).stdout
        _cache[fs_id] = denoise(band(np.frombuffer(raw, '<i2').astype(float) / 32768, lo=30))
    return _cache[fs_id]


def denoise(x, over=2.0, floor_db=-30.0):
    """Spectral subtraction with the recording's own noise profile (the quietest 15 % of its frames, per frequency):
    takes out the hiss / room floor and, with it, most of the quiet handling noise between events. The gain is
    smoothed over time and frequency so it does not 'bubble'."""
    f, t, X = stft(x, SR, nperseg=2048, noverlap=1536)
    mag = np.abs(X)
    frame_level = (mag ** 2).sum(0)
    quiet = frame_level <= np.percentile(frame_level, 15)
    noise = np.sqrt((mag[:, quiet] ** 2).mean(1, keepdims=True))
    g = np.maximum(1 - over * noise ** 2 / np.maximum(mag ** 2, 1e-20), 10 ** (floor_db / 10)) ** 0.5
    k = np.ones((3, 5)) / 15.0
    from scipy.signal import convolve2d
    g = convolve2d(g, k, mode='same', boundary='symm')
    _, y = istft(X * g, SR, nperseg=2048, noverlap=1536)
    return y[:len(x)]


def cut(fs_id, t0, t1, rate=1.0):
    """t0..t1 s of a recording, played at `rate` (0.8 = 20 % lower and longer, as a slower tape)."""
    x = source(fs_id)[int(t0 * SR):int(t1 * SR)]
    if rate != 1.0:
        x = resample_poly(x, int(round(1000 / rate)), 1000)
    return x


# ---------------------------------------------------------------- processing
def band(x, lo=None, hi=None, order=2):
    if lo:
        x = sosfiltfilt(butter(order, lo, 'highpass', fs=SR, output='sos'), x)
    if hi:
        x = sosfiltfilt(butter(order, hi, 'lowpass', fs=SR, output='sos'), x)
    return x


def eq(x, points):
    """Smooth EQ curve in the frequency domain: points {Hz: dB}, interpolated on a log axis."""
    fx = np.fft.rfftfreq(len(x), 1 / SR)
    fc = np.array(sorted(points), float)
    db = np.interp(np.log2(np.maximum(fx, 10.0)), np.log2(fc), [points[k] for k in sorted(points)])
    return np.fft.irfft(np.fft.rfft(x) * 10 ** (db / 20), len(x))


def compress(x, thr_db=-18.0, ratio=3.0, attack=0.004, release=0.12, parallel=0.5):
    """RMS compressor on the event (relative to its peak), mixed in parallel with the dry signal: denser, louder body
    without flattening the hit."""
    k = max(1, int(0.002 * SR))
    env = np.sqrt(np.convolve(x ** 2, np.ones(k) / k, 'same')) + 1e-9
    a, r = np.exp(-1 / (attack * SR)), np.exp(-1 / (release * SR))
    sm = np.empty_like(env)
    s = env[0]
    for i, v in enumerate(env):            # (a few seconds of audio: a plain loop is fine)
        s = a * s + (1 - a) * v if v > s else r * s + (1 - r) * v
        sm[i] = s
    lvl = 20 * np.log10(sm / np.abs(x).max())
    gain = np.where(lvl > thr_db, (thr_db - lvl) * (1 - 1 / ratio), 0.0)
    wet = x * 10 ** (gain / 20)
    wet *= np.abs(x).max() / np.abs(wet).max()
    return (1 - parallel) * x + parallel * wet


def room(x, mix=0.12, t60=0.55):
    """The runway around the event: the ground reflection (~8 ms) and a short open-air tail - an impulse response of
    decaying noise, darker as it decays (air absorption)."""
    n = int(t60 * 1.2 * SR)
    t = np.arange(n) / SR
    ir = RNG.standard_normal(n) * 10 ** (-3 * t / t60)
    ir = band(ir, lo=80, hi=5000)
    ir[:int(0.006 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum())
    ir[int(0.008 * SR)] += 0.5
    wet = fftconvolve(x, ir)[:len(x)]
    return x + mix * wet * rms(x) / max(rms(wet), 1e-12)


# Inside the aircraft. The game plays these sounds dry (a position and a distance, no filtering, no reverb: failures_f22
# engine_once / cockpit_loop), and only in the cockpit - so the cockpit has to be in the file. The first full scenes were
# outside sounds 'put in headphones, not tied to the aircraft' (user, 2026-11-21): the event reaches the pilot through
# the structure - the highs are lost (the F/A-18's cockpit in the game: -18 dB at 1 kHz, -29 at 2 kHz, -40 at 8 kHz
# under 63 Hz, 2026-11-21 recording), and the airframe rings with it: its panels and frames are struck, and their low
# modes (60-900 Hz, damped in tenths of a second) carry the hit. The same airframe for all layers: it glues them.
TRANSMISSION = {25: 0.0, 63: 0.0, 125: -1.0, 250: -4.0, 500: -10.0, 1000: -17.0, 2000: -26.0, 4000: -33.0, 8000: -41.0,
                16000: -55.0, 22000: -65.0}
MODES = ((58, 0.30, 1.0), (84, 0.26, 0.9), (121, 0.22, 0.8), (167, 0.18, 0.7), (236, 0.14, 0.55), (330, 0.11, 0.45),
         (470, 0.08, 0.35), (660, 0.06, 0.25), (930, 0.045, 0.18))      # Hz, decay time constant s, amplitude


def airframe(x, wet=0.55):
    """The structure's ring: x through a bank of damped modes (an impulse response of decaying sines), mixed with x."""
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    ir = sum(a * np.exp(-t / tau) * np.sin(2 * np.pi * f * t + RNG.uniform(0, 2 * np.pi)) for f, tau, a in MODES)
    ir /= np.sqrt((ir ** 2).sum())
    y = fftconvolve(x, ir)[:len(x)]
    return (1 - wet) * x / rms(x) + wet * y / rms(y)


def master(x, low=3.0, presence=2.0, comp=(-20.0, 3.0), room_mix=0.12, inside=1.0, final=(-16.0, 2.5)):
    """The event outside (EQ, compression, the runway), then as the pilot hears it inside (transmission, airframe).
    inside < 1 lets more of the top through: a crack in the airframe itself reaches the pilot sharper than a scrape
    under it; `final` is the last compressor (threshold, ratio): lower and harder = denser, louder in the game."""
    x = eq(x, {30: low - 2, 80: low, 160: low * 0.5, 350: -2.0, 800: 0.0, 2500: presence, 6000: presence * 0.5,
               12000: -2.0, 20000: -6.0})
    x = compress(x, *comp)
    x = room(x, room_mix)
    x = airframe(eq(x, {f: d * inside for f, d in TRANSMISSION.items()}))
    return compress(x, final[0], final[1], 0.006, 0.15, 0.4 if final[1] < 3 else 0.7)


def rms(x):
    return np.sqrt((x ** 2).mean())


def norm(x):
    return x / np.abs(x).max()


def fade(x, a=0.005, r=0.3):
    n = len(x)
    g = np.ones(n)
    na, nr = int(a * SR), min(int(r * SR), n)
    g[:na] = np.linspace(0, 1, na)
    g[n - nr:] *= np.linspace(1, 0, nr) ** 2
    return x * g


def place(n, *parts):
    """Sum of (signal, start s, gain) into n samples."""
    y = np.zeros(n)
    for x, at, g in parts:
        a = int(at * SR)
        m = min(len(x), n - a)
        if m > 0:
            y[a:a + m] += g * x[:m]
    return y


def chain(segments, xf=0.06):
    """Segments joined end to end with equal-power crossfades of xf s."""
    k = int(xf * SR)
    w = np.sin(np.linspace(0, np.pi / 2, k))
    y = segments[0].copy()
    for s in segments[1:]:
        y[-k:] = y[-k:] * w[::-1] + s[:k] * w
        y = np.r_[y, s[k:]]
    return y


def ride(x, win=0.08, amount=0.8):
    """Even out the level of a drag (a slow gain riding on a smoothed envelope, like a fader): a scrape loop must not
    jump by 20 dB where the hand pressed harder; `amount` 1 = flat level, 0 = as recorded. Texture under ~12 Hz kept."""
    k = int(win * SR)
    env = np.sqrt(np.convolve(x ** 2, np.ones(k) / k, 'same')) + 1e-6
    g = (rms(x) / env) ** amount
    return x * np.convolve(g, np.ones(k) / k, 'same')


def seamless(x, seconds, xf=0.25):
    """A loop of `seconds` from a longer signal: its tail crossfaded (equal power) into its head."""
    n, k = int(seconds * SR), int(xf * SR)
    assert len(x) >= n + k, (len(x) / SR, seconds + xf)
    w = np.sin(np.linspace(0, np.pi / 2, k))
    y = x[:n].copy()
    y[:k] = x[:k] * w + x[n:n + k] * w[::-1]
    return y


def tame(x, over_db=15.0):
    """Round off single ticks standing far over the body (fewer than 1 sample in 10 000), so they do not set the level."""
    t = rms(x) * 10 ** (over_db / 20)
    return np.where(np.abs(x) > t, np.sign(x) * t * (1 + 0.25 * np.tanh(np.abs(x) / t - 1)), x)


def write(name, x, peak_db=-1.0):
    x = x - x.mean()
    x = x * 10 ** (peak_db / 20) / np.abs(x).max()
    os.makedirs(OUT, exist_ok=True)
    wavfile.write(os.path.join(OUT, name + '.wav'), SR, (x * 32767).astype('<i2'))
    print('%-14s %5.2f s  rms %5.1f dBFS' % (name, len(x) / SR, 20 * np.log10(rms(x))))


# ---------------------------------------------------------------- the events
def debris(n, times, gain):
    """Loose parts: small knocks of the kettlebell (545562, its last 16 s), each a little different in pitch."""
    hits = [(32.0, 32.6), (34.0, 34.6), (38.3, 38.9), (41.4, 42.0), (42.6, 43.2), (44.3, 44.9), (46.0, 46.6), (48.0, 48.6)]
    parts = []
    for i, at in enumerate(times):
        a, b = hits[i % len(hits)]
        h = band(cut(545562, a, b, RNG.uniform(0.75, 1.05)), lo=180)
        parts.append((fade(norm(h), 0.001, 0.15), at, gain * RNG.uniform(0.5, 1.0)))
    return place(n, *parts)


def gear_crunch():
    """A gear leg breaking: the crash's impact and crunch with its debris, a sub-boom (the same impact an octave
    down), the kettlebell's heavy hit for weight, the anchor bar tearing on concrete just after, loose parts."""
    n = int(3.2 * SR)
    crash = cut(346299, 3.60, 7.40, 0.85)
    boom = band(cut(346299, 3.60, 4.60, 0.5), hi=160, order=4)
    thud = band(cut(545544, 18.62, 19.6, 0.7), hi=1500)
    tear = band(fade(cut(450356, 10.40, 11.20, 0.75), 0.01, 0.35), lo=150)
    x = place(n, (norm(crash), 0.0, 1.0), (norm(boom), 0.0, 0.9), (norm(thud), 0.05, 0.5), (norm(tear), 0.12, 0.35))
    x += debris(n, (0.45, 0.62, 0.9, 1.25, 1.6, 2.1), 0.12)
    # in the game it was buried by the slide starting with it (2026-11-21): sharper (half the transmission loss) and
    # denser, and the slide now swells in over ~1 s after it (failures_f22)
    return fade(master(x, presence=3.0, inside=0.5, final=(-22.0, 4.0)), 0.002, 0.7)


def tyre_burst():
    """A tyre bursting under the aircraft: a real shotgun's report for the crack of ~300 psi letting go (the closest real
    sound to a burst), the pyrotechnic blast's low punch under it for the volume of air, the airframe kicked by it, a
    few loose bits. In the first build (the crash's first instant) it was 'not a tyre' (user, 2026-11-21)."""
    n = int(1.6 * SR)
    crack = band(fade(cut(159710, 0.065, 0.75, 0.92), 0.0005, 0.35), lo=90)
    punch = band(fade(cut(251759, 0.085, 0.75, 0.8), 0.001, 0.3), hi=300, order=4)
    x = place(n, (norm(crack), 0.0, 1.0), (norm(punch), 0.004, 0.55))
    x += debris(n, (0.3, 0.55, 0.85), 0.05)
    return fade(master(x, low=4.0, presence=3.0, room_mix=0.15, inside=0.4, final=(-22.0, 4.0)), 0.001, 0.6)


def stall_bang():
    """A compressor stall / flameout: the engine's surge is a blast in its intake and nozzle - the pyrotechnic explosion
    (its punch and natural rolling decay), the shotgun's report a little lower for the sharp edge, through the airframe
    from behind the pilot (more of the top lost than the tyre: the engine is in the fuselage, not under the floor).
    Replaces the synthetic noise blast of make_cockpit_sounds (user, 2026-11-21: 'make a proper flameout sound')."""
    n = int(2.2 * SR)
    blast = band(fade(cut(251759, 0.07, 2.2, 0.85), 0.0005, 0.9), lo=30)
    edge = band(fade(cut(159710, 0.07, 0.6, 0.8), 0.0005, 0.3), lo=150)
    x = place(n, (norm(blast), 0.0, 1.0), (norm(edge), 0.003, 0.35))
    return fade(master(x, low=4.0, presence=2.0, room_mix=0.1, inside=0.65, final=(-22.0, 4.0)), 0.001, 0.8)


def belly_scrape(L=8.0):
    """The airframe sliding on the runway (a loop; failures_f22 sets its volume and pitch by ground speed): heavy metal
    dragged on concrete (the kettlebell's drags, without their pauses), the airframe's rumble under it (the same drags
    much lower), the crowbar's steady scrape for the metal edge, bursts of the anchor bar's loud scrape where the
    surface catches, bumps and loose parts."""
    drags = [cut(545562, a, b, 0.85) for a, b in ((8.05, 11.85), (12.75, 15.95))] + \
            [cut(545544, a, b, 0.85) for a, b in ((7.35, 10.6), (13.85, 17.6), (1.25, 4.95))]
    heavy = ride(band(chain(drags), lo=40))
    rumble = ride(band(chain([cut(545562, 8.05, 11.85, 0.5), cut(545544, 13.85, 17.6, 0.5), cut(545562, 12.75, 15.95, 0.5)]),
                       lo=30, hi=320, order=4))
    edge = ride(band(cut(452587, 21.9, 30.5, 0.9), lo=150))
    n = int((L + 0.3) * SR)
    burst = band(fade(cut(450356, 10.35, 11.3, 0.75), 0.05, 0.4), lo=120)
    x = place(n, (heavy / rms(heavy), 0.0, 1.0), (rumble / rms(rumble), 0.0, 0.8), (edge / rms(edge), 0.0, 0.5),
              (burst / rms(burst), 1.7, 0.6), (burst / rms(burst), 5.4, 0.45))
    x += debris(n, (0.8, 2.6, 3.9, 6.3, 7.4), 2.5)
    x = master(x, low=4.0, presence=1.5, comp=(-14.0, 4.0), room_mix=0.08)
    return tame(seamless(x, L, 0.3))


def seize_grind():
    """The rotor seizing: a heavy hit and its sub-boom (a big rotor stopping at once), the crash's metal crunch for
    bite, a clank, the anchor bar grinding on and fading over ~1.5 s, a rattle of loose parts."""
    n = int(2.8 * SR)
    hit = band(cut(545544, 6.62, 7.5, 0.6), hi=1200)
    boom = band(cut(545544, 6.62, 7.3, 0.4), hi=140, order=4)
    bite = band(cut(346299, 3.62, 4.10, 0.7), lo=300)
    clank = band(cut(450356, 12.9, 13.6, 0.85), lo=200)
    grind = fade(ride(band(cut(450356, 10.35, 12.3, 0.8), lo=120), amount=0.6), 0.02, 0.9)
    x = place(n, (norm(hit), 0.0, 1.0), (norm(boom), 0.0, 1.4), (norm(bite), 0.01, 0.35), (norm(clank), 0.04, 0.4),
              (grind / rms(grind), 0.08, 0.2))
    x += debris(n, (0.35, 0.55, 0.8, 1.2), 0.1)
    return fade(master(x, low=5.0), 0.002, 0.6)


def main():
    write('gear_crunch', gear_crunch())
    write('belly_scrape', belly_scrape())
    write('seize_grind', seize_grind())
    write('tyre_burst', tyre_burst())        # last: the random draws of the sounds above stay as accepted
    write('stall_bang', stall_bang())


if __name__ == '__main__':
    main()
