"""Our MFD pages ENG, FCS and SYS, one layout for all (2026-11-17: order on the MFD screens - the Hornet's
engine and flight-control pages carried dead numbers and an always empty servo-valve grid, our overlays came in four
font sizes, SYS mixed flight controls with automatics).

Layout (page units 0 .. 1000, y up): title 34 at y 905, rows in one font of 30 every 50 units from y 840, labels from
x 110, values right-aligned in fixed fields. Green values, white section heads, amber cautions, red losses.

  ENG  engines L / R: state (OFF, MOTOR, START, RUN, FADEC = stopped by its FADEC, WMILL = windmilling, SEIZED), N2, N1, EGT, fuel flow, thrust, nozzle, oil, vibration; APU and inlet temperature.
       (The Hornet's FUEL TEMP was a constant 20 C, EPR / CDP / TDP and its THRUST were made up from N2: gone.)
       Fire switches: the ENG page keys as before (failures_f22).
  FCS  surfaces L / R: deflection in degrees and status (OK / DEGD / HYD / JAM / LOST, breakage_f22.fcs_status);
       hydraulics; FCS mode, vector, nozzle, authority; g limit, AoA, load and peak g, pitch rate. Keys DIR and VEC
       (moved from SYS: they are flight control modes).
  SYS  automatics and power: autothrottle (mode, target, step), Auto-GCAS and its floor, alternate gear, generators,
       APU, battery. (VOICE % went: the RADIO VOL panel's VOX knob shows it.)
  STAT (2026-11-22) the systems as a grid of words, white off / green on / amber fault.
  APPR (2026-11-22) the approach: speed, AoA and its FAST / ON SPD / SLOW cue, pitch, path, vertical speed, radar
       altitude, configuration.
  ENG also shows FIRE in a burning engine's column and the aircraft's GW, total thrust and T/W (2026-11-22).

Called from make_f22.py after breakage_f22.fcs_status (the surface states exist then); each page replaces its old
render list in every MFD page switch."""
import math
import re

TITLE, ROW = 34.0, 30.0
STRIDE = 0.9
Y0, DY = 840, 50
X_LABEL = 110
WHITE = (0.85, 0.95, 0.85, 1.0)
GREEN = (0.3, 1.0, 0.3, 1.0)
DEG = 180.0 / math.pi


class Page:
    def __init__(self, ns, key):
        self.ns, self.key, self.items, self.n = ns, key, [], 0
        self.font = dict(ns['UFD_FONT'], FontSize=ROW, Stride=ROW * STRIDE)

    # dynamics helpers
    def dyn(self, type_, name, **f):
        self.ns['obj'](self.ns['dyn'], type_, name, self.ns['anchor'], **f)
        return name + '.Output'

    def _id(self):
        self.n += 1
        return 'F22Mfd%s%d' % (self.key, self.n)

    def text(self, src, x, y, n, right=True, color=None, size=None):
        """A dynamics text output in a field of n characters at x (left edge) - right-aligned unless right=False."""
        k = self._id()
        font = self.font if size is None else dict(self.font, FontSize=size, Stride=size * STRIDE)
        extra = {'Color': ' %g %g %g %g ' % color} if color else {}
        self.items.append(self.ns['place_copy']('UpFrontControllerLine0', k, Input=self.ns['text_out'](k, src),
                                                Position=' %d %d ' % (x, y), Length=str(n),
                                                LeftJustified='true' if not right else 'false', **font, **extra))

    def label(self, text, x, y, color=None, size=ROW):
        self.items.append(self.ns['label'](text, (x, y), size, color))

    def source(self, src):
        """Dynamics cannot read an `output` object (graphics only - the aircraft does not load): what it forwards."""
        name = src.split('.')[0]
        o = next((x for x in self.ns['dyn'].children if x.name == name), None)
        if o is not None and o.type == 'output':
            return self.source(o.get('Input').strip())
        return src

    def value(self, src, x_end, y, n, scale=1.0, offset=0.0, decimals=0, color=None, size=None):
        """A number src x scale + offset, right-aligned, ending at x_end."""
        k = self._id()
        src = self.source(src)
        v = self.dyn('mixlinear', k + 'V', Input0=src, Input1='1.0', Weight0=scale, Weight1=offset)
        t = self.dyn('float_to_text', k + 'T', Input=v, Decimals=('uint32', str(decimals))) if decimals else \
            self.dyn('int_to_text', k + 'T', Input=v)
        self.text(t, x_end - int(n * (size or ROW) * STRIDE), y, n, color=color, size=size)

    def title(self, text):
        w = len(text) * TITLE * STRIDE
        self.label(text, int(500 - w / 2), 905, size=TITLE)

    def install(self, old_names):
        """The page's render list, put in place of the old page in every MFD page switch."""
        name = 'F22Mfd%sPage' % self.key
        self.ns['g']('graphics_animation_render_list', name, RenderList=' %s ' % ' '.join(self.items))
        n = 0
        for o in self.ns['G']:
            if o.type == 'graphics_animation_render_switch' and o.find('RenderList') is not None:
                toks = o.get('RenderList').split()
                if any(t in old_names for t in toks):
                    o.set('RenderList', ' ' + ' '.join(name if t in old_names else t for t in toks) + ' ')
                    n += 1
        print('MFD page %s in %d page switches' % (self.key, n))


def _w(n):
    return int(n * ROW * STRIDE)


# Picture sprites (block G, mfd_symbols). A texture_animation_rectangle does not draw in the screen's window: it works
# in the whole render target, and everything drawn after it in the same list follows it there (in-game 2026-11-22: the
# ENG and BAY texts came out 2.6 x larger and ran onto the next screen). So the pages only declare their sprites here,
# in page units, and make_f22 draws them per screen, last in that screen's list, in its atlas coordinates.
PAGE_SPRITES = {}                       # MFD page number -> [(key, mfd_symbols sprite, (x, y) page units, value or None, crop)]
# the N2 gauge in four strips round its figure (a sprite is opaque: one piece would cover the number drawn before it)
DIAL_STRIPS = (('B', (0, 0, 140, 50)), ('T', (0, 94, 140, 46)), ('L', (0, 50, 24, 44)), ('R', (116, 50, 24, 44)))


def sprite(ns, key, name, pos, index_src=None, scale=1.0, crop=None):
    """A picture of mfd_symbols drawn by texture_animation_rectangle from the display2 atlas: lower left corner at pos and
    size x scale in render-target units (1024 over the atlas); crop (x, y, w, h) a part of each variant; index_src the
    dynamics value picking the variant. Returns the item."""
    import mfd_symbols
    d = mfd_symbols.layout()[name]
    cx, cy, w, h = crop or (0, 0) + tuple(d['size'])
    item = 'F22Spr' + key
    extra = {}
    if index_src:
        gin = 'GfxF22SprIdx' + index_src.split('.')[0]
        if not any(o.name == gin for o in ns['G']):
            ns['g']('graphics_input', gin, InputID=('uint32', ns['published'](index_src.split('.')[0])))
        extra['Input'] = gin + '.Output'
    ns['g']('texture_animation_rectangle', item, TextureName='display2_color',
            TargetPosition=('tmvector2d', ' %.2f %.2f ' % pos), TargetSize=('tmvector2d', ' %.2f %.2f ' % (w * scale, h * scale)),
            TargetScale=('tmvector2d', ' 1024 1024 '), **extra,
            SourcePosition=('tmvector2d', ' %s ' % ' '.join('( %d %d )' % (s[0] + cx, s[1] + cy) for s in d['src'])),
            SourceSize=('tmvector2d', ' %d %d ' % (w, h)), SourceScale=('tmvector2d', ' %d %d ' % (mfd_symbols.ATLAS, mfd_symbols.ATLAS)))
    return item


def screen_sprites(ns, screen, window_pos, window_size, page):
    """The sprites of an MFD page drawn on one screen: page units -> that screen's render-target units."""
    k = window_size / 1024.0
    out = []
    for key, name, (x, y), idx, crop, *rest in PAGE_SPRITES.get(page, []):
        sc = rest[0] if rest else 1.0                   # the sprite's own scale on the page
        ox, oy = (crop[0] * sc, crop[1] * sc) if crop else (0, 0)
        out.append(sprite(ns, '%s%s' % (screen, key), name, (window_pos[0] + (x + ox) * k, window_pos[1] + (y + oy) * k),
                          idx, k * sc, crop))
    return out


def eng_page(ns):
    p = Page(ns, 'Eng')
    lbl = ns['ufc_label']
    p.title('ENGINES')
    xl, xr = 620, 860                     # right ends of the L and R value fields
    # round N2 gauges (block G, 2026-11-22, after the AOA F-22's engine page) either side of the title, the figure
    # inside (same day: under the title, over the table, the page looked crowded); 120 units, 22 steps
    import mfd_symbols
    sc = 120.0 / mfd_symbols.DIAL
    dial_y, digit = 880, 26                 # (850: the right gauge covered the R over its column, in-game)
    for k, cx in ((1, 230), (2, 770)):
        idx = p.dyn('linear_interpolation', 'F22MfdEng%dN2Dial' % k, Input='Engine%dN2.Output' % k, Map=mfd_symbols.n2_index_map())
        for strip, crop in DIAL_STRIPS:
            PAGE_SPRITES.setdefault(8, []).append(('EngN2%d%s' % (k, strip), 'N2', (cx - 60, dial_y), idx, crop, sc))
        p.value('Engine%dN2.Output' % k, cx + int(1.5 * digit * STRIDE), dial_y + 50, 3, 100.0, size=digit)  # (in the strips' hole)
    p.label('N2', 118, dial_y + 50, size=22)
    p.label('L', xl - _w(1), Y0, WHITE)
    p.label('R', xr - _w(1), Y0, WHITE)
    y = Y0 - DY
    p.label('STATE', X_LABEL, y)
    for k, x in ((1, xl), (2, xr)):
        st = p.dyn('multiplexer_text', 'F22MfdEng%dState' % k, InputSelect='F22Eng%dStageS.Output' % k,
                   Inputs=' %s ' % ' '.join(lbl(t) for t in ('OFF', 'MOTOR', 'START', 'RUN', 'FADEC', 'WMILL', 'SEIZED')))
        # a fire (failures_f22 F22FireWarn<k>) in the engine's own column, red, in place of its state (2026-11-22,
        # after the AOA X-Plane F-22: FIRE over the burning engine's gauge)
        st_shown = p.dyn('multiplexer_text', 'F22MfdEng%dStateShown' % k, InputSelect='F22FireWarn%d.Output' % k,
                         Inputs=' %s BlankLabel.Output ' % st)
        fire = p.dyn('multiplexer_text', 'F22MfdEng%dFire' % k, InputSelect='F22FireWarn%d.Output' % k,
                     Inputs=' BlankLabel.Output %s ' % lbl('FIRE'))
        p.text(st_shown, x - _w(6), y, 6)
        p.text(fire, x - _w(6), y, 6, color=ns['UFD_RED'])
    rows = [('N1 %', 'Engine%dN1.Output', 100.0, 0.0, 0),
            ('EGT C', 'Engine%dExhaustGasTemperature.Output', 1.0, -273.15, 0),
            ('FF PPH', 'Engine%dFuelFlow.Output', 7936.64, 0.0, 0),          # kg/s -> lb/h
            ('THRUST KN', 'Engine%d.OutputThrust', 0.001, 0.0, 0),
            ('NOZZLE %', 'Engine%dNozzlePosition.Output', 100.0, 0.0, 0),
            ('OIL PSI', 'Engine%dOilPressure.Output', 1 / 6894.757, 0.0, 0),
            ('VIB', 'Engine%dVibration.Output', 100.0, 0.0, 1)]          # (the Hornet page showed x 100)
    for r, (text, src, k_, off, dec) in enumerate(rows):
        y = Y0 - DY * (r + 2)
        p.label(text, X_LABEL, y)
        for k, x in ((1, xl), (2, xr)):
            p.value(src % k, x, y, 6, k_, off, dec)
    y = Y0 - DY * (len(rows) + 3)
    p.label('APU', X_LABEL, y, WHITE)
    p.text('F22ApuText.Output', 430 - _w(4), y, 4)
    p.label('INLET C', X_LABEL, y - DY)
    p.value('TemperatureSensor.Temperature', 430, y - DY, 3, 1.0, -273.15)
    # the aircraft as a whole (2026-11-22, after the AOA F-22's engine page: gross weight, thrust, thrust / weight):
    # GW = our weight bookkeeping (empty + counted fuel + the combat load; the game itself does not take the fuel off the
    # mass), THR = both engines' thrust now, T/W = THR / (GW x g)
    rows_ = (('GW LB', 'F22GrossWeight.Output', 2.204622621849, 0), ('THR KN', 'F22ThrustTotal.Output', 0.001, 0),
             ('T/W', 'F22ThrustToWeight.Output', 1.0, 2))
    for r, (text, src, k_, dec) in enumerate(rows_):
        p.label(text, 560, y - DY * r)
        p.value(src, xr, y - DY * r, 5, k_, 0.0, dec)
    p.install({'F22EnginesPage', 'EnginesPage'})


def fcs_page(ns):
    p = Page(ns, 'Fcs')
    lbl = ns['ufc_label']
    AMBER, RED = ns['AMBER'], ns['UFD_RED']
    p.title('FLIGHT CONTROLS')
    # surface table: name | L: deg, status | R: deg, status
    blocks = {'Left': (349, 450), 'Right': (619, 720)}         # (deg field start, status start)
    p.label('SURF DEG', X_LABEL, Y0, WHITE)
    p.label('L', 440, Y0, WHITE)
    p.label('R', 710, Y0, WHITE)
    # deflections, + = trailing edge down / nose up as the Hornet page (radians -> degrees)
    srcs = {'LEF': ('ServoLeftSlat.Output', 'ServoRightSlat.Output', DEG), 'TEF': ('ServoLeftFlap.Output', 'ServoRightFlap.Output', DEG),
            'AIL': ('ServoLeftAileron.Output', 'ServoRightAileron.Output', DEG),
            'RUD': ('ServoLeftRudder.Output', 'ServoRightRudder.Output', DEG),
            'STAB': ('LeftStabilatorPosition.Output', 'RightStabilatorPosition.Output', DEG)}
    texts = {t: 'F22FcsText%s.Output' % t for t in ('OK', 'DEGD', 'HYD', 'LOST', 'JAM')}
    blank = 'F22FcsBlank.Output'
    for r, name in enumerate(('LEF', 'TEF', 'AIL', 'RUD', 'STAB')):
        y = Y0 - DY * (r + 1)
        p.label(name, X_LABEL, y)
        for side, (xd, xs) in blocks.items():
            p.value(srcs[name][0 if side == 'Left' else 1], xd + _w(3), y, 3, srcs[name][2])
            st = 'F22FcsState%s%s.Output' % (name, side[0])
            for colour, rgba, choice in (('G', GREEN, (texts['OK'], blank, blank, blank, blank)),
                                         ('A', AMBER, (blank, texts['DEGD'], texts['HYD'], blank, texts['JAM'])),
                                         ('R', RED, (blank, blank, blank, texts['LOST'], blank))):
                src = p.dyn('multiplexer_text', 'F22MfdFcs%s%s%s' % (colour, name, side[0]), InputSelect=st,
                            Inputs=' %s ' % ' '.join(choice))
                p.text(src, xs, y, 4, right=False, color=rgba)
    y = Y0 - DY * 6
    p.label('HYD', X_LABEL, y)
    for k, (side, (xd, xs)) in enumerate(blocks.items(), 1):
        p.value('F22HydSystem%d.Output' % k, xs - _w(1), y, 4, 3000.0)
        for colour, rgba, choice in (('G', GREEN, (texts['OK'], blank)), ('R', RED, (blank, 'F22FcsTextOut%d.Output' % k))):
            src = p.dyn('multiplexer_text', 'F22MfdFcsHyd%s%d' % (colour, k), InputSelect='F22HydOut%d.Output' % k,
                        Inputs=' %s ' % ' '.join(choice))
            p.text(src, xs, y, 4, right=False, color=rgba)
    # modes and flight state: two columns
    y = Y0 - DY * 8
    p.label('MODE', X_LABEL, y, WHITE)
    p.label('LIMITS', 560, y, WHITE)
    left = [('FCS', ('text', 'F22TvcModeText.Output', 6)), ('VECTOR', ('text', 'F22TvcVectorText.Output', 6)),
            ('NOZ DEG', ('num', 'NozzleAngle.Output', DEG, 0)), ('AUTH %', ('num', 'VectorSpeedFade.Output', 100.0, 0)),
            ('Q D/S', ('num', 'InertialReferenceSystem.OutputQRate', -DEG, 0))]
    right = [('G-LIM', ('num', 'FlightController.OutputAccelerationLimit', 1 / 9.81, 1)),
             ('AOA', ('num', 'PitotTube.AngleOfAttack', DEG, 1)), ('G', ('num', 'Accelerometer.Acceleration', 1 / 9.81, 1)),
             ('PEAK G', ('num', 'Accelerometer.MaximumPositiveAcceleration', 1 / 9.81, 1))]
    for col, (x_lab, x_end, rows) in enumerate(((X_LABEL, 480, left), (560, 880, right))):
        for r, (text, what) in enumerate(rows):
            yy = y - DY * (r + 1)
            p.label(text, x_lab, yy)
            if what[0] == 'text':
                p.text(what[1], x_end - _w(what[2]), yy, what[2])
            else:
                p.value(what[1], x_end, yy, 5, what[2], 0.0, what[3])
    p.install({'F22FcsPage', 'FlightControlsPage'})


def sys_page(ns):
    p = Page(ns, 'Sys')
    lbl = ns['ufc_label']
    p.title('SYSTEMS')
    xv = 700                               # right end of the values (the A/T legends stand by the right keys)
    rows = [('AUTOTHROTTLE', None), ('MODE', ('F22TvcAtText.Output', 6)), ('TARGET', ('F22AtTargetText.Output', 6)),
            ('STEP', ('F22AtStepText.Output', 3)), (None, None),
            ('AUTO GCAS', None), ('STATUS', ('F22TvcGcasText.Output', 3)), ('FLOOR FT', 'floor'), (None, None),
            ('POWER', None), ('GEN L', ('gen1', 3)), ('GEN R', ('gen2', 3)), ('APU', ('F22ApuText.Output', 4)),
            ('BATTERY', ('batt', 6)), ('ALT GEAR', ('altgr', 6))]
    gens = {'gen%d' % k: p.dyn('binary_to_text', 'F22MfdSysGen%d' % k, Input='Engine%dGeneratorContactor.Output' % k,
                               Text0='OFF', Text1='ON') for k in (1, 2)}
    gens['batt'] = p.dyn('binary_to_text', 'F22MfdSysBatt', Input='F22OnBattery.Output', Text0='STBY', Text1='IN USE')
    gens['altgr'] = p.dyn('binary_to_text', 'F22MfdSysAltGr', Input='F22AltGear.Output', Text0='NORM', Text1='PULLED')
    for r, (text, what) in enumerate(rows):
        y = Y0 - DY * r
        if text is None:
            continue
        if what is None:
            p.label(text, X_LABEL, y, WHITE)
            continue
        p.label(text, X_LABEL + _w(1), y)
        if what == 'floor':
            p.value('F22AltFloor.Output', xv, y, 5, 3.28084)
        else:
            src, n = what
            p.text(gens.get(src, src), xv - _w(n), y, n)
    # the A/T keys' legends, across, level with keys 1 and 3 of the right column (calibrated 2026-11-07 on a
    # screenshot: keys at page y 786 / 625 / 465 / 307; keys 2 and 4 carry the menu's arrows)
    at_key = p.dyn('binary_to_text', 'F22MfdSysAtKey', Input='F22AtActive.Output', Text0='A/T', Text1='*A/T')
    p.text(at_key, 894, 786, 4)
    p.text('F22AtStepText.Output', 918, 465, 3)
    p.install({'F22TvcPage', 'BuiltInTestPage'})


def _state_cell(p, key, text, x, y, on, fault=None, on_is_fault=False):
    """One word of a status grid: white = off, green = on, amber = fault (or on, for a mode that is a caution in
    itself). Three texts at one place, one of them non-blank."""
    lbl = p.ns['ufc_label']
    w = lbl(text)
    terms = ' %s %s ' % (on, fault) if fault else ' %s 0.0 ' % on
    s = p.dyn('mixlinear', 'F22Stat%sSel' % key, Input0=terms.split()[0], Input1=terms.split()[1],
              Weight0=2.0 if on_is_fault else 1.0, Weight1=2.0)
    blank = 'BlankLabel.Output'
    for colour, rgba, pick in (('W', WHITE, (w, blank, blank, blank, blank)), ('G', GREEN, (blank, w, blank, blank, blank)),
                               ('A', p.ns['AMBER'], (blank, blank, w, w, w))):
        src = p.dyn('multiplexer_text', 'F22Stat%s%s' % (key, colour), InputSelect=s, Inputs=' %s ' % ' '.join(pick))
        p.text(src, x, y, len(text), right=False, color=rgba)


def stat_page(ns):
    """STATUS (2026-11-22, after the AOA F-22's CNI system grid): the aircraft's systems in one grid, each word white
    when off, green when on, amber on a fault. Replaces the Hornet's mission initialisation page (no menu link before)."""
    p = Page(ns, 'Stat')
    p.title('STATUS')
    d = lambda type_, name, **f: p.dyn(type_, name, **f)
    # derived states
    hyd_ok = d('logic_invert', 'F22StatHydOk', Input='F22HydLow.Output')
    canopy_shut = d('logic_invert', 'F22StatCanopyShut', Input='CanopyOpen.Output')
    canopy_air = d('logic_and', 'F22StatCanopyAir', Inputs=' CanopyOpen.Output F22AtAirborne.Output ')
    nav = d('logic_greater', 'F22StatNav', Input0='PositionLightBrightnessKnob.Output', Input1='0.04')
    form = d('logic_greater', 'F22StatForm', Input0='FormationLightBrightness.Output', Input1='0.01')
    ldg = d('logic_greater', 'F22StatLdg', Input0='LandingLight.Output', Input1='0.5')
    taxi = d('logic_greater', 'F22StatTaxi', Input0='F22TaxiLight.Output', Input1='0.5')
    gen = {k: d('logic_greater', 'F22StatGen%d' % k, Input0='Engine%dGeneratorContactor.Output' % k, Input1='0.5')
           for k in (1, 2)}
    grid = [[('BATT', 'BatterySwitchOn.Output', 'F22OnBattery.Output'), ('APU', 'F22ApuTurning.Output', None),
             ('GEN L', gen[1], 'Engine1GeneratorCaution.Output'), ('GEN R', gen[2], 'Engine2GeneratorCaution.Output'),
             ('HYD', hyd_ok, 'F22HydLow.Output')],
            [('A/T', 'F22AtActive.Output', None), ('AP', 'FlightController.OutputAutopilotActive', None),
             ('GCAS', 'F22GcasArmed.Output', None), ('VEC', 'F22VectorOn.Output', None), ('DIR', 'F22DirectMode.Output', 'amber')],
            [('BAY', 'F22BayOpen.Output', None), ('GEAR', 'AllGearDown.Output', None), ('HOOK', 'ArrestingHookDown.Output', None),
             ('P BRK', 'ParkingBrakeSet.Output', None), ('CANOPY', canopy_shut, canopy_air)],
            [('NAV', nav, None), ('FORM', form, None), ('LDG', ldg, None), ('TAXI', taxi, None), ('BIT', 'F22BitPass.Output', None)]]
    for r, row in enumerate(grid):
        for c, (text, on, fault) in enumerate(row):
            key = re.sub(r'[^A-Za-z0-9]', '', text)
            if fault == 'amber':
                _state_cell(p, key, text, 70 + 180 * c, 800 - 90 * r, on, on_is_fault=True)
            else:
                _state_cell(p, key, text, 70 + 180 * c, 800 - 90 * r, on, fault)
    p.label('ON', X_LABEL, 380, GREEN)
    p.label('OFF', 260, 380, WHITE)
    p.label('FAULT', 440, 380, ns['AMBER'])
    p.install({'MissionInitializationPage'})


def appr_page(ns):
    """APPROACH (2026-11-22, after the AOA F-22's low speed page): the approach on one page - speed, angle of attack
    against the 8.5 deg the A/T holds with the gear down (FAST / ON SPD / SLOW, +-1 deg), pitch, flight path, vertical
    speed, radar altitude and the configuration. Replaces the Hornet's EW page (no menu link before)."""
    p = Page(ns, 'Appr')
    lbl = ns['ufc_label']
    AMBER = ns['AMBER']
    p.title('APPROACH')
    left = [('IAS KT', 'AirDataComputer.OutputCalibratedAirspeed', 1.943844, 0),
            ('AOA DEG', 'PitotTube.AngleOfAttack', DEG, 1), ('PITCH DEG', 'InertialReferenceSystem.OutputPitchAngle', DEG, 1),
            ('FPA DEG', 'InertialReferenceSystem.OutputFlightPathAngle', DEG, 1),
            ('VS FPM', 'InertialReferenceSystem.OutputVerticalVelocity', 196.8504, 0), ('RALT FT', 'RadarAltimeter.Output', 3.28084, 0)]
    for r, (text, src, k_, dec) in enumerate(left):
        y = Y0 - DY * r
        p.label(text, X_LABEL, y)
        p.value(src, 560, y, 6, k_, 0.0, dec)
    # the angle of attack cue: below 7.5 deg FAST, 7.5 .. 9.5 ON SPD, above SLOW (the A/T's 8.5 deg target +-1)
    cue = p.dyn('linear_interpolation', 'F22ApprCueIndex', Input='PitotTube.AngleOfAttack',
                Map=' (0.1308 0.0) (0.1309 1.0) (0.1657 1.0) (0.1658 2.0) ')
    blank = 'BlankLabel.Output'
    p.label('TGT AOA 8.5', 590, Y0, WHITE)
    for colour, rgba, pick in (('A', AMBER, (lbl('FAST'), blank, lbl('SLOW'))), ('G', GREEN, (blank, lbl('ON SPD'), blank))):
        src = p.dyn('multiplexer_text', 'F22ApprCue%s' % colour, InputSelect=cue, Inputs=' %s ' % ' '.join(pick))
        p.text(src, 640, Y0 - DY * 2, 6, right=False, color=rgba, size=TITLE)
    # configuration
    y = Y0 - DY * 7
    p.label('CONFIG', X_LABEL, y, WHITE)
    gear = p.dyn('mixlinear', 'F22ApprGearIndex', Input0='AnyGearDown.Output', Input1='AllGearDown.Output', Weight0=1.0, Weight1=1.0)
    rows = [('GEAR', p.dyn('multiplexer_text', 'F22ApprGear', InputSelect=gear,
                           Inputs=' %s ' % ' '.join(lbl(t) for t in ('UP', 'TRANS', 'DOWN'))), 5),
            ('SPD BRK', p.dyn('binary_to_text', 'F22ApprSpdBrk', Input='F22SpeedBrakeOut.Output', Text0='IN', Text1='OUT'), 3),
            ('A/T', p.dyn('binary_to_text', 'F22ApprAt', Input='F22AtActive.Output', Text0='OFF', Text1='ON'), 3),
            ('HOOK', p.dyn('binary_to_text', 'F22ApprHook', Input='ArrestingHookDown.Output', Text0='UP', Text1='DOWN'), 4)]
    for r, (text, src, n) in enumerate(rows):
        yy = y - DY * (r + 1)
        p.label(text, X_LABEL + _w(1), yy)
        p.text(src, 560 - _w(n), yy, n)
    p.install({'ElectronicWarfarePage'})


def pages(ns):
    eng_page(ns)
    fcs_page(ns)
    sys_page(ns)
    stat_page(ns)
    appr_page(ns)
