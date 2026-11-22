"""Engine sound of the F-22: the stock F-15E's recordings (F100, Pratt & Whitney) on both engines, in place of the
F/A-18's sound the configuration starts from (docs/reference/SOUND.md).

The five F-15E files are copied from the user's own game at install under the names of STOCK_COPIES (build_lib.sh
stock_copies; the release installer: BACKLOG), so they never clash with the F/A-18's files of the same names. Its layers
are played as its f15e.tmd plays them, with three changes:
  - its N2 points moved onto ours: its N2 (0.97 x rotation speed) is 0.72 at idle, ~0.88 at full dry (its burner layer
    opens at 0.88 -> 0.89) and up to 0.97 in afterburner; ours is 0.65 / 1.0 / 1.01 (the F/A-18's map). So
    x' = 0.65 + 2.1875 (x - 0.72) up to its 0.88, its afterburner range onto our 1.0 -> 1.01;
  - the turbine layer (jet_00) is held at ~0.6 up to full dry (the F-15E lets it fall to 0.3: its full dry lacked the
    250 Hz - 1 kHz flow), its jet_02 at 1.0 at full dry;
  - N2 and afterburner are smoothed (SMOOTH) and the burner map is linear up to the light's 0.3: the F-15E's map steps
    at 0.01 -> 0.1 and the light clicked. In the cockpit the burner file is lifted to ~0.65 when lit (the F-15E plays
    it at 0.1-0.3 by N2 alone).
Each engine keeps the F-15E's own small pitch offset, as two real engines never run at one rpm."""

STOCK_COPIES = {'f15e_jet_00': 'f15e/jet_00.tsb', 'f15e_jet_00_int': 'f15e/jet_00_int.tsb', 'f15e_jet_01_int': 'f15e/jet_01_int.tsb',
                'f15e_jet_02': 'f15e/jet_02.tsb', 'f15e_jet_afterburn': 'f15e/jet_afterburn.tsb'}

# layer: (file, inside, volume = product of (input, map) factors, pitch map per engine, canopy share of an outside layer)
TURBINE = ' (0.01 0.0) (0.65 0.7) (0.825 0.65) (1.0 0.6) (1.01 0.3) '
TURBINE_PITCH = (' (0.0 0.0) (0.65 0.7) (1.0 0.871) (1.01 0.92) ', ' (0.0 0.0) (0.65 0.72) (1.0 0.885) (1.01 0.935) ')
HIGH_PITCH = (' (0.0 0.0) (0.65 0.6) (1.0 0.827) (1.01 0.88) ', ' (0.0 0.0) (0.65 0.59) (1.0 0.815) (1.01 0.87) ')
BURNER_PITCH = (' (0.0 1.0) (1.0 1.0) ', ' (0.0 0.97) (1.0 0.97) ')
LAYERS = {
    'idle': ('f15e_jet_00', False, (('n2', TURBINE),), TURBINE_PITCH, 0.6),
    'high': ('f15e_jet_02', False, (('n2', ' (0.0 0.0) (0.759 0.0) (0.956 0.9) (1.0 1.0) (1.01 1.0) '),), HIGH_PITCH, 0.6),
    'ab': ('f15e_jet_afterburn', False, (('n2', ' (0.0 0.0) (0.95 0.0) (1.0 0.9) (1.01 1.0) '), ('ab', ' (0.0 0.0) (0.3 0.6) (1.0 1.0) ')),
           BURNER_PITCH, 0.5),
    'int_idle': ('f15e_jet_00_int', True, (('n2', TURBINE),), TURBINE_PITCH, 0),
    'int_high': ('f15e_jet_01_int', True, (('n2', ' (0.0 0.0) (0.759 0.0) (0.956 0.8) (1.0 0.83) (1.01 0.95) '),), HIGH_PITCH, 0),
    'int_ab': ('f15e_jet_afterburn', True, (('n2', ' (0.0 0.0) (0.95 0.0) (1.0 0.05) (1.01 0.3) '), ('ab', ' (0.0 1.0) (0.3 1.8) (1.0 2.2) ')),
               BURNER_PITCH, 0),
}
SMOOTH = 0.15       # s, first-order lag of N2 and afterburner as the sound hears them

NOZZLE = {1: (-5.3, 0.66, 0.27), 2: (-5.3, -0.66, 0.27)}        # the jet_engine bodies (make_f22.py)
FWD, AFT = ' 1.0 0.0 0.0 ', ' -1.0 0.0 0.0 '
CONE_OUT = dict(ConeCenter=0.0, ConeDecay=0.75, ConeFade=0.75)     # the F-15E's outside loops (rearward)
CONE_IN = dict(ConeCenter=0.95, ConeDecay=1.2, ConeFade=0.2)       # its cockpit loops

DONOR_LOOPS = [('SoundEngine%d' % k) + s for k in (1, 2) for s in (
    'TurbineExterm', 'TurbineExtermInside', 'TurbineIntern', 'MidIntern', 'MidExtern', 'MidExternOnInside',
    'AfterburnerExtern', 'AfterburnerExternInside', 'AfterburnerIntern')]
DONOR_MAPS = [('Engine%d' % k) + s for k in (1, 2) for s in (
    'TurbineVolume', 'TurbinePitch', 'TurbineVolumeInside', 'MidVolume', 'MidPitch', 'MidVolumeInside',
    'AfterburnerPitch', 'AfterburnerVolume', 'AfterburnerVolumeExtern', 'AfterburnerVolumeIntern', 'AfterburnerVolumeInside')]


def apply(ns):
    obj, snd, dyn, D = ns['obj'], ns['snd'], ns['dyn'], ns['D']
    drop = set(DONOR_LOOPS + DONOR_MAPS)
    gone = [c.name for c in snd.children if c.name in drop]
    snd.children = [c for c in snd.children if c.name not in drop]
    assert len(gone) == len(drop), sorted(drop - set(gone))
    names = {c.name for c in snd.children}
    assert {'Engine1N2', 'Engine2N2', 'Engine1Afterburner', 'Engine2Afterburner', 'CanopyReducedExternalVolume'} <= names

    def vec(v):
        return ('tmvector3d', ' %.4f %.4f %.4f ' % v)

    def curve(name, src, m):
        obj(snd, 'soundmapping', name, Input=src + '.Output', Map=m)
        return name + '.Output'

    def mul(name, a, b):
        obj(snd, 'soundmultiply', name, Input0=a, Input1=b)
        return name + '.Output'

    def loop(name, vol, pitch, wav, r0, inside, x0, cone, rng):
        f = dict(PositionID=('uint32', 'Fuselage.R'), OrientationID=('uint32', 'Fuselage.Q'), VelocityID=('uint32', 'Fuselage.V'),
                 InputVolume=vol, InputPitch=pitch, SoundFile=wav + '.wav', R0=vec(r0), Radius=2.0, Range=('float64', '%.1f' % rng),
                 X0=('tmvector3d', x0))
        f.update(cone)
        f['External' if inside else 'Internal'] = ('bool', 'false')
        obj(snd, 'soundloop', name, **f)

    count = 0
    for k in (1, 2):
        e = 'F22Eng%d' % k
        smooth = {}
        for key, src in (('n2', 'Engine%dN2' % k), ('ab', 'Engine%dAfterburner' % k)):
            lag = 'F22Snd%sLag' % src       # the lag lives in the dynamics (the sound side has only curves and products)
            D[lag] = obj(dyn, 'first_order_low_pass', lag, Input=src + '.Output', TimeConstant='%g' % SMOOTH)
            # the sound reads own dynamics values only through an `output` object (published()); read directly it gets 0
            obj(snd, 'soundinput', lag, InputID=('uint32', ns['published'](lag)))
            smooth[key] = lag
        for key, (wav, inside, factors, pitches, canopy) in LAYERS.items():
            t = e + 'F15' + key.title().replace('_', '')
            vol = None
            for i, (src, m) in enumerate(factors):
                c = curve(t + 'Vol%d' % i, smooth[src], m)
                vol = c if vol is None else mul(t + 'Vol%dx' % i, vol, c)
            pitch = curve(t + 'Pitch', smooth['n2'], pitches[k - 1])
            if inside:
                loop(t + 'Sound', vol, pitch, wav, NOZZLE[k], True, FWD, CONE_IN, 500.0)
            else:
                loop(t + 'Sound', vol, pitch, wav, NOZZLE[k], False, AFT, CONE_OUT, 2000.0)
                # heard inside with the canopy open (the F-15E / F/A-18 CanopyReducedExternalVolume)
                cv = mul(t + 'CanopyVolume0', vol, 'CanopyReducedExternalVolume.Output')
                cv = mul(t + 'CanopyVolume', cv, '%g' % canopy)
                loop(t + 'SoundCanopy', cv, pitch, wav, NOZZLE[k], True, FWD, CONE_IN, 500.0)
                count += 1
            count += 1
    print('engine sound: F-15E recordings on both engines (%d loops)' % count)
    return True
