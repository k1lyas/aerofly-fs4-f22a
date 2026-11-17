"""Our MFD pages ENG, FCS and SYS, one layout for all (user 2026-11-17: "order on the MFD screens" - the Hornet's
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

Called from make_f22.py after breakage_f22.fcs_status (the surface states exist then); each page replaces its old
render list in every MFD page switch."""
import math

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

    def value(self, src, x_end, y, n, scale=1.0, offset=0.0, decimals=0, color=None):
        """A number src x scale + offset, right-aligned, ending at x_end."""
        k = self._id()
        src = self.source(src)
        v = self.dyn('mixlinear', k + 'V', Input0=src, Input1='1.0', Weight0=scale, Weight1=offset)
        t = self.dyn('float_to_text', k + 'T', Input=v, Decimals=('uint32', str(decimals))) if decimals else \
            self.dyn('int_to_text', k + 'T', Input=v)
        self.text(t, x_end - int(n * ROW * STRIDE), y, n, color=color)

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


def eng_page(ns):
    p = Page(ns, 'Eng')
    lbl = ns['ufc_label']
    p.title('ENGINES')
    xl, xr = 620, 860                     # right ends of the L and R value fields
    p.label('L', xl - _w(1), Y0, WHITE)
    p.label('R', xr - _w(1), Y0, WHITE)
    y = Y0 - DY
    p.label('STATE', X_LABEL, y)
    for k, x in ((1, xl), (2, xr)):
        st = p.dyn('multiplexer_text', 'F22MfdEng%dState' % k, InputSelect='F22Eng%dStageS.Output' % k,
                   Inputs=' %s ' % ' '.join(lbl(t) for t in ('OFF', 'MOTOR', 'START', 'RUN', 'FADEC', 'WMILL', 'SEIZED')))
        p.text(st, x - _w(6), y, 6)
    rows = [('N2 %', 'Engine%dN2.Output', 100.0, 0.0, 0), ('N1 %', 'Engine%dN1.Output', 100.0, 0.0, 0),
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
    p.text('F22ApuText.Output', xl - _w(4), y, 4)
    p.label('INLET C', X_LABEL, y - DY)
    p.value('TemperatureSensor.Temperature', xl, y - DY, 4, 1.0, -273.15)
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
    # the A/T keys' legends, across, level with keys 1 and 3 of the right column (calibrated 2026-11-07 on the user's
    # screenshot: keys at page y 786 / 625 / 465 / 307; keys 2 and 4 carry the menu's arrows)
    at_key = p.dyn('binary_to_text', 'F22MfdSysAtKey', Input='F22AtActive.Output', Text0='A/T', Text1='*A/T')
    p.text(at_key, 894, 786, 4)
    p.text('F22AtStepText.Output', 918, 465, 3)
    p.install({'F22TvcPage', 'BuiltInTestPage'})


def pages(ns):
    eng_page(ns)
    fcs_page(ns)
    sys_page(ns)
