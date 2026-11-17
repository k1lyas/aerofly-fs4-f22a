"""Aircraft config: F-22A Raptor from the Grinnelli Designs DCS mod (GPL-3), physics donor F/A-18 (stock).

Read by the generic tools (export_parts.py, anim_tables.py, measure_parts.py). See docs/PORTING_GUIDE.md.
"""
import os
import re

NAME = 'f22'
HERE = os.path.dirname(os.path.abspath(__file__))     # aircraft/f22/
EDM = os.path.join(HERE, 'source', 'Shapes/F-22A.EDM')
TEXTURES = os.path.join(HERE, 'source', 'tex_all')
COLLECTION = 'F-22A'
# export pose: gear down, everything else neutral (canopy closed, bays closed, flaps up)
POSE = {0: 1.0, 3: 1.0, 5: 1.0}

# DCS-only content: sunglasses, ground power cart, weapon pylons, lights and flames (the pilot figure is kept: part
# 'Pilot', seen from outside only - PILOT_MATERIAL)
EXCLUDE_MATERIAL = re.compile(r'Sunglasses|GPU_|CartLight|F22A_LIGHT|BANO|TACI_LAND_ON|^0\d - Default$|'
                              r'^F22_CANOPY_GLASS$|^F22_Clipboard$|^PHOTO$|^TAPE$|Garfield', re.I)
EXCLUDE_KIND = re.compile(r'transparent_self_illum|bano', re.I)
# exterior-model cockpit pieces replaced by the cockpit model (Cockpit_F-22A.EDM, merged by tools/merge_cockpit.py:
# DCS shows one of the two, Aerofly draws both): seat, HUD glass and frame; the cockpit model's own canopy glass
# duplicates the exterior canopy (one glass surface only - every extra layer is haze and z-fighting)
# _0.011 / _1.011 / _1.012: the exterior model's own simplified cockpit (tub with a painted low-res panel, canopy
# fittings), all faces inside the airframe - it showed through the detailed cockpit as blurry blocks
EXCLUDE_NAME = re.compile(r'WeaponPylon|^F-22A_Cockpit_ACES_II|^HUD GLASS$|^hud align$|^_0\.011$|^_1\.01[12]$|'
                          r'^CP_ON_(NOSE|LEFT|RIGHT)_GEAR$|^CP_ON_BATTERY$', re.I)
# (CP_ON_*_GEAR: the lit copies of the gear position plates - DCS shows one of the two; the CP_OFF_* plates carry
# both looks here as lamps, LAMPS below)
# removed on the user's request (2026-10-22, a clear glareshield): the two swivelling map lights on the UFD hoods
# (cockpit arguments 716 / 717, stowed and unused since stage 5) with their brackets and cables (merged into a larger
# F22_ACC object: faces in the box), and beside each UFD the unit with eight dark-blue 6 x 8 mm lenses (static in the
# DCS mod, no argument, no label): lenses (F22_SCREEN), their slanted plate and housing and the wire bundle behind it
# (F22_ACC, a triangle soup - no connected pieces to pick): a box along the lens plane (plane fitted to the 16 lens
# faces; u along the plate, v across towards the UFD, n towards the pilot), 10 cm deep to take the wires - renders:
# the frame behind and the UFD housing stay whole. The first build removed the lenses only: the panel showed the empty
# cells and the background through them (user, 2026-10-22)
EXCLUDE_ARGS = (10716, 10717)
REMOVE_FACES = [dict(material=r'^F22_ACC$', box=((7.63, 0.10, 1.125), (7.735, 0.175, 1.18)), mirror_y=True,
                     note='map light brackets'),
                dict(material=r'^F22_(ACC|SCREEN)$', centre=(7.6819, 0.2352, 1.0689),
                     axes=((-0.4336, 0.269, -0.86), (0.3782, -0.8119, -0.4447), (-0.8179, -0.518, 0.2503)),
                     ranges=((-0.045, 0.045), (-0.03, 0.05), (-0.10, 0.015)), mirror_y=True, note='lens units')]
GLASS_KIND = re.compile(r'glass', re.I)
# exterior canopy gold (user, 2026-10-22): tried GLASS_OUTSIDE = dict(tint=(0.85, 0.58, 0.08) - the mod's F22_GLASS
# colour - opacity=0.22, specular=(0.46, 0.32, 0.05)): in the game the canopy came out bright pale blue and stood out
# from the airframe. The exterior glass shader's use of the colour is not known (absorption? the denser layer only
# showed more sky) - back to the stock grey until a stock tinted canopy shows how it is set
GLASS_PLAIN = re.compile(r'^F22A_VISOR|^\d+ - Default$|^F22_HUD_GLASS$')   # visor, small lenses: no gold
BURNER = None
# afterburner (tests 11-13, 2026-10-20): a translucent plume outside the nozzles could not be drawn with the standard or the
# exterior glass shader, flame rollers inside the 2D nozzles read as a spinning lava cylinder. Now (2026-10-30, _burner_objects):
# the engine inside the nozzles is real lit geometry, as on the stock F/A-18 and F-15E (nozzle_fire_f22.py). Plume tests 2026-10-30, both dropped: instrument glass drew a grey card always (no luminance, no fade), the propeller
# disc shader showed nothing at disc speeds 20 and 300.
# ICP see-through band: a labelled UV grid on the F22_UFC colour map showed what the game draws there (2026-10-30, _icp_patch)
UV_GRID_MATERIAL = None        # 'f22_ufc' for the diagnostic grid
UV_GRID_CELLS = 32
# Aerofly culls back faces: export every triangle as authored in DCS (see tools/export_parts.py SINGLE_SIDED)
SINGLE_SIDED = True
# full resolution (4096, as in DCS) for the skin and the cockpit seen at arm's length (2048 made the panels mushy);
# the ejection seat behind the pilot stays at 2048
FULL_RES = re.compile(r'^(f-22a_default|f22_(?!taxi|glass|aces))', re.I)
# interior shader (the game's 'Brighten aircraft interior' setting and the cockpit lighting act on these): the
# cockpit model's textures F22_* (not the exterior lamp/glass textures f22_taxi_light, f22_glass*), and the pilot's suit
# and helmet (with the exterior shader the cloth shone like the painted skin); the mirror visor keeps the exterior one
INTERIOR_TEXTURE = re.compile(r'^(f22_(?!taxi|glass)|f22a_pilot$|hgu-55p$)', re.I)
# night cockpit lighting (stage 5): every interior material gets a lighting map (channel k = InputIllumination<k>,
# make_f22.py): red = flood light from its ambient occlusion (FLOOD knob), green = the side-console lettering
# (CONSOLE knob), blue = the instrument panel and ICP key lettering (INST PNL knob). The lettering masks are the DCS
# self-illumination masks in the alpha of the mod's panel textures (F22_LABLES' four words: F22_LABLES_GREEN's alpha)
FLOOD_ILLUMINATION = 0.12         # plain level (x ambient): switches and labels on the consoles (0.35: the light switch
                                  # handles glowed against the panels under the stronger flood colour)
FLOOD_BAKED_LEVEL = 0.8           # brightest texel of the baked flood light (BAKE_FLOOD)
# flood lamps light the consoles and the instrument panel, not the whole tub: the first build lit every interior
# texture alike - floor, side walls, seat and straps turned flat grey as by day. Not lit: F22_SIDE (side walls / sills),
# F22_TUB, F22_FRAME_*, F22_ACES_II (seat), F22_EXTRA (straps), F22_HOOD (glareshield), F22_RUDDER (pedals)
# Since 2026-10-22 the side consoles only (BAKE_FLOOD below): their panels with the baked lamp light, their switches
# and labels at a plain level; the centre panel, ICP, UFDs and MFD bezels none (lit by their displays)
FLOOD_TEXTURE = re.compile(r'^F22_(PANEL_(LEFT|RIGHT|FRONT)|SWITCH|THROTTLE|STICK|LABLES)$', re.I)
# baked cockpit light (tools/bake_cockpit_light.py, 2026-10-22). The mod's RoughMet red channel is no ambient
# occlusion (median 0 on most cockpit textures: the whole cockpit sat at the AMBIENT_MIN floor, flat by day and the
# flood map built from it flat at night). Ambient occlusion baked from the geometry for the materials with a unique
# UV layout (measured: no overlap between objects, < 7 % within one); the others keep a plain ambient (INTERIOR_AMBIENT)
BAKE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'work', 'bake')
# (F22_FRAME_LOWER is unique too, but its upper half F22_FRAME_UPPER is not: baked alone, the sill showed a step)
BAKE_AO = ['F22_PANEL_LEFT', 'F22_PANEL_RIGHT', 'F22_PANEL_FRONT', 'F22_TUB', 'F22_SIDE', 'F22_HOOD',
           'F22_UFC', 'F22_THROTTLE', 'F22_STICK', 'F22_RUDDER', 'F22_ACES_II', 'F22_MFD']
BAKED_AMBIENT_MIN = 0.5           # ambient = min + (1 - min) * AO (0.35 left a third of the walls and floor at the floor
                                  # value, darker than the former flat 0.6)
BAKE_AO_DISTANCE = 0.30           # 0.12 m only darkened the contact lines: the tub's own shading (under the glareshield,
                                  # along the walls) needs rays the size of the consoles
FLOOD_ON_LABELS = 0.15             # flood map on the lettering, whose own lamps are the CONSOLE and INST PNL knobs: 16-24 x its panel at 1.0 (measured 2026-11-01)
FLOOD_GAMMA = 0.5                 # flood map ** gamma: softer pools (linear, half of the console sat below 1/8)
INTERIOR_AMBIENT = 0.75           # interior textures without a baked AO (about the baked panels' median)
# Flood light (FLOOD knob) as the F/A-18's: lamps under the canopy rails shining down on the side consoles - soft pools
# of light with the knobs' shadows, baked per texel (red channel of the lighting map). The centre panel needs none at
# night (user, 2026-10-22: its displays light it). Knobs and switches share small textures with overlapping UVs: they
# take the plain FLOOD_ILLUMINATION level (FLOOD_TEXTURE)
BAKE_FLOOD = dict(materials=['F22_PANEL_LEFT', 'F22_PANEL_RIGHT', 'F22_PANEL_FRONT', 'F22_THROTTLE', 'F22_STICK'],
                  reference=['F22_PANEL_LEFT', 'F22_PANEL_RIGHT'],
                  # over the controls (x 7.15 .. 7.62, the rear plates are blank), z 0.84: from z >= 0.90 a ray test
                  # saw 0 - 25 % of the panel (something lies across above the consoles) - the first lamps lit the
                  # blank rear plates through gaps (user); from here 80 - 87 %
                  lamps=[((x, s * 0.44, 0.84), (x + 0.02, s * 0.40, 0.62), 0.04, 120.0, 5.0)
                         for x in (7.22, 7.38, 7.52) for s in (1, -1)])
LABEL_ILLUMINATION = [(re.compile(r'^F22_PANEL_(LEFT|RIGHT)$', re.I), 1),
                      (re.compile(r'^F22_LABLES$', re.I), 2, 'F22_LABLES_GREEN'),
                      (re.compile(r'^F22_(PANEL_FRONT|SCREEN)$', re.I), 2)]

# DCS argument -> how Aerofly drives it ('table': a sampled DCS animation table driven by a dynamics output). Directions
# are checked with the sampled tables before the first conversion (docs/PORTING_GUIDE.md, lessons).
DRIVERS = {
    0: dict(kind='table', source='GearSequence', range=(0.0, 1.0)),            # nose gear (1 = down)
    3: dict(kind='table', source='GearSequence', range=(0.0, 1.0)),            # right main
    5: dict(kind='table', source='GearSequence', range=(0.0, 1.0)),            # left main
    1: dict(kind='table', source='StrokeNose', range=(0.0, 1.0)),              # strut compression
    4: dict(kind='table', source='StrokeRight', range=(0.0, 1.0)),
    6: dict(kind='table', source='StrokeLeft', range=(0.0, 1.0)),
    # nose wheel: DCS +1 turns the wheel to the left (60 deg), ServoSteering + = right (as on the Su-35)
    2: dict(kind='table', source='ServoSteering', range=(-1.0, 1.0), map=[(-1.047, 1.0), (1.047, -1.0)]),
    101: dict(kind='spin', hull='LeftFrontWheelHull'),
    102: dict(kind='spin', hull='LeftWheelHull'),
    103: dict(kind='spin', hull='RightWheelHull'),
    9: dict(kind='table', source='FlaperonRight', range=(-1.0, 1.0), map=[(-0.5236, -1.0), (0.5236, 1.0)]),
    10: dict(kind='table', source='FlaperonLeft', range=(-1.0, 1.0), map=[(-0.5236, -1.0), (0.5236, 1.0)]),
    # ailerons: DCS +1 = trailing edge up; Aerofly aileron servo + = trailing edge down (F-15E/F-18 graphics, and
    # it is the aerowing flap angle) -> inverted. Flaperons 9/10: DCS +1 = down = flap + aileron sum, direct.
    11: dict(kind='table', source='ServoRightAileron', range=(-1.0, 1.0), map=[(-0.5236, 1.0), (0.5236, -1.0)]),
    12: dict(kind='table', source='ServoLeftAileron', range=(-1.0, 1.0), map=[(-0.5236, 1.0), (0.5236, -1.0)]),
    15: dict(kind='body', body='RightStabilator'),
    16: dict(kind='body', body='LeftStabilator'),
    17: dict(kind='table', source='ServoRightRudder', range=(-1.0, 1.0), map=[(-0.5236, -1.0), (0.5236, 1.0)]),
    18: dict(kind='table', source='ServoLeftRudder', range=(-1.0, 1.0), map=[(-0.5236, -1.0), (0.5236, 1.0)]),
    182: dict(kind='table', source='ServoAirBrake', range=(0.0, 1.0)),      # speed brake: control surfaces split
    38: dict(kind='table', source='CanopySequence', range=(0.0, 0.9)),
    # nozzles: 89/90 petal translation, 610/611 2D nozzle flaps, 622/623 thrust vectoring. Sampled so that the parts stay animated parts, but
    # the seals and flaps are drawn by NOZZLE_PLATES below, not by these tables
    89: dict(kind='table', source='NozzleRight', range=(0.0, 1.0)),
    90: dict(kind='table', source='NozzleLeft', range=(0.0, 1.0)),
    610: dict(kind='table', source='NozzleRight', range=(0.0, 1.0)),
    611: dict(kind='table', source='NozzleLeft', range=(0.0, 1.0)),
    622: dict(kind='table', source='VectorPitch', range=(-1.0, 1.0)),
    623: dict(kind='table', source='VectorPitch', range=(-1.0, 1.0)),
    # leading-edge flaps (F-22A.lua: 603 --LEF): rigid pieces turning about the leading-edge hinge, 0 .. 20 deg down
    # for arg 0 .. 1 (negative values do nothing). Driven by the donor's LEF servo (radians, F/A-18 schedule with
    # angle of attack / flaps, up to ~34 deg): true angle up to the 20 deg the model shows, held there above.
    603: dict(kind='table', source='ServoLeftSlat', range=(0.0, 1.0), map=[(0.0, 0.0), (0.349, 1.0), (0.7, 1.0)]),
    # weapon bays (stage 6): 600 main bay doors, 601 / 602 left / right side bay doors with the AIM-9 trapeze; 22 the
    # air refuelling receptacle door - 0 closed .. 1 open, from the BAY page / AAR switch servos (make_f22.py)
    600: dict(kind='table', source='F22BayCenter', range=(0.0, 1.0)),
    601: dict(kind='table', source='F22BayLeft', range=(0.0, 1.0)),
    602: dict(kind='table', source='F22BayRight', range=(0.0, 1.0)),
    22: dict(kind='table', source='F22AARDoor', range=(0.0, 1.0)),
}
# The nozzle flaps do not follow the DCS tables (args 90/89, 611/610, 623/622). There a seal and its flap are separate pieces with different travel, which go into each other at
# most settings, with the bare DCS model too (triangle crossings counted over the travel, 2026-11-01), and arg -1 lowers the flap tips while the thrust of a nose-up command needs them
# raised. Here a seal and its flap are one rigid plate, hinged on the outer skin at the seal's forward edge: nothing moves between them, and the angle is the physics' own nozzle angle
# (tvc_f22.py) plus the opening. part: (Upper / Lower, engine side)
NOZZLE_PLATES = {'A_185_184_183': ('Upper', 'Left'), 'A_187_186_183': ('Upper', 'Left'), 'A_180_179_178': ('Lower', 'Left'), 'A_182_181_178': ('Lower', 'Left'),
                 'A_172_171_167': ('Upper', 'Right'), 'A_169_168_167': ('Upper', 'Right'), 'A_177_176_173': ('Lower', 'Right'), 'A_175_174_173': ('Lower', 'Right')}
NOZZLE_HINGE = {'Upper': (-4.33, 0.87), 'Lower': (-4.30, -0.33)}    # x, z of the seals' forward outer edge
NOZZLE_OPEN = 0.52      # rad per unit of the Nozzle<side> schedule: about 15 deg at full afterburner (0.5), 9 at idle (0.3), shut at full dry
# not animated: 39 pilot head, 324/325 turbine discs (flat textured discs, now behind the real wheel of nozzle_fire_f22.py),
# 614/615 gun (no guns in Aerofly), 617/618 power cart
SAMPLES = 11

# ---- cockpit controls (Cockpit_F-22A.EDM, merged by merge_cockpit.py; argument numbers from the mod's
# mainpanel_init.lua / clickabledata.lua / Systems/*.lua). Sampled at all cockpit arguments 0. Keys are
# COCKPIT_ARG_BASE + DCS cockpit argument (the exterior uses the same numbers). Directions checked on the EDM:
# 71 +1 = stick right, 74 +1 = stick aft, 500 +1 = right pedal forward, 761/762 -1 released .. +1 pressed,
# 766/768 +1 idle .. -1 full afterburner (Engine_System.lua), 765/767 0 cut-off .. 1 run, 83 gear handle 0 down .. 1
# up, switches 1 = on. Aerofly: elevator stick +1 = push, aileron +1 = right, pedals +1 = right forward, thrust lever
# -0.2 cut-off .. 0 idle .. 0.65 military .. 1, GearLever 1 = down.
COCKPIT_ARG_BASE, COCKPIT_NODE_BASE = 10000, 100000
COCKPIT_POSE = {}
COCKPIT_DRIVERS = {
    71: dict(kind='table', source='ServoAileronStick', range=(-1.0, 1.0)),
    74: dict(kind='table', source='ServoElevatorStick', range=(-1.0, 1.0), map=[(-1.0, 1.0), (1.0, -1.0)]),
    500: dict(kind='table', source='RudderPedals', range=(-1.0, 1.0)),
    761: dict(kind='table', source='LeftBrakePedal', range=(-1.0, 1.0), map=[(0.0, -1.0), (1.0, 1.0)]),
    762: dict(kind='table', source='RightBrakePedal', range=(-1.0, 1.0), map=[(0.0, -1.0), (1.0, 1.0)]),
    766: dict(kind='table', source='Engine2ThrustLeverPosition', range=(-1.0, 1.0), map=[(0.0, 1.0), (1.0, -1.0)]),
    768: dict(kind='table', source='Engine1ThrustLeverPosition', range=(-1.0, 1.0), map=[(0.0, 1.0), (1.0, -1.0)]),
    765: dict(kind='table', source='Engine2ThrustLeverPosition', range=(0.0, 1.0), map=[(-0.2, 0.0), (-0.05, 1.0)]),
    767: dict(kind='table', source='Engine1ThrustLeverPosition', range=(0.0, 1.0), map=[(-0.2, 0.0), (-0.05, 1.0)]),
    83: dict(kind='table', source='GearLeverOutput', range=(0.0, 1.0), map=[(0.0, 1.0), (1.0, 0.0)]),
    700: dict(kind='table', source='BatteryOverrideSwitch', range=(0.0, 1.0), map=[(0.0, 0.0), (1.0, 1.0)]),
    # APU OFF / ARM / START (DCS arg -1 / 0 / 1, Switch_Up_Down_Release); work/anim.json samples the whole -1 .. 1
    # (a mirrored half on top of it gave double keys at every negative sample)
    # (arg +1 is START: an inverting map, tried 2026-11-06, drew the cold-start OFF at START; the 'cannot start' it was
    # meant to fix was the APU latch dropping on the DC ESS dip at generator pick-up, see make_f22.py)
    701: dict(kind='table', source='F22ApuSwitch', range=(-1.0, 1.0)),
    702: dict(kind='table', source='Engine1GeneratorSwitch', range=(0.0, 1.0)),
    703: dict(kind='table', source='Engine2GeneratorSwitch', range=(0.0, 1.0)),
    704: dict(kind='table', source='LeftMFDBrightness', range=(0.0, 1.0)),
    705: dict(kind='table', source='PanelLightKnob', range=(0.0, 1.0)),          # INST PNL (DCS 'PFD Brightness')
    706: dict(kind='table', source='ConsoleBrightnessKnob', range=(0.0, 1.0)),
    707: dict(kind='table', source='FloodLightKnob', range=(0.0, 1.0)),
    708: dict(kind='table', source='MasterArmSafeSwitch', range=(0.0, 1.0)),
    # LDG / OFF / TAXI (make_f22.py): switch 0 TAXI (aft, -1), 1 OFF (0), 2 LDG (forward, +1)
    709: dict(kind='table', source='LandingLightSwitch', range=(-1.0, 1.0), map=[(0.0, 0.0), (1.0, 0.5), (2.0, 1.0)]),
    710: dict(kind='table', source='ParkingBrake', range=(0.0, 1.0)),
    711: dict(kind='table', source='EmergencyJettisionButton', range=(0.0, 1.0)),
    714: dict(kind='table', source='FormationLightBrightnessKnob', range=(0.0, 1.0)),
    # NAV knob: 5 detents OFF / DIM / MED / BRT / FLASH (make_f22.py NAV_STEPS) from the F/A-18 knob's 0..1
    715: dict(kind='table', source='PositionLightBrightnessKnob', range=(0.0, 0.4),
              map=[(0.0, 0.0), (0.1249, 0.0), (0.125, 0.1), (0.3749, 0.1), (0.375, 0.2), (0.6249, 0.2), (0.625, 0.3),
                   (0.8749, 0.3), (0.875, 0.4), (1.0, 0.4)]),
    # (716 / 717, the swivelling map lights on the UFD hoods: removed from the model - EXCLUDE_ARGS)
    718: dict(kind='table', source='HUDDayNightSwitch', range=(0.0, 1.0)),
    # AAR panel (FUEL, left console): door switch OPEN / CLOSE and the receptacle light knob (stage 6)
    712: dict(kind='table', source='F22AARSwitch', range=(0.0, 1.0)),
    713: dict(kind='table', source='F22AARLightKnob', range=(0.0, 1.0)),
}
# cockpit canopy (181: the inner frame with the sill panels) moves with the exterior canopy (38): the two models
# hinge it at different points (x 5.65 z 1.37 / x 5.58 z 1.13) and open it 31 / 25 deg at the same value
COCKPIT_FOLLOW = {181: 38}
DRIVERS.update({COCKPIT_ARG_BASE + a: d for a, d in COCKPIT_DRIVERS.items()})

# exterior lights (positions and colours of the DCS light nodes; make_f22.py adds the sources and the switches of the
# F/A-18): the landing / taxi lamp lenses on the nose gear glow (lit '_ON' twins are hidden DCS variants). The wingtip
# nav / anti-collision lights have no lens geometry (F22A_BANO are glow cards of the DCS renderer): point lights only.
# Formation lights: the DCS F22A_LIGHT objects are glow boxes for DCS's additive renderer (one 8 cm above the wing,
# side faces through the skin) - opaque in Aerofly they floated, showed through the skin and mirrored the sun. A glow
# mask on the painted strips was pixelated (~60x140 texels per strip) and left the painted black edge. Instead: flat
# panels of our own (EXTRA_OBJECTS) laid 2.5 mm over each painted strip and its black edge, matte, lit by the switch.
LAMPS = [
    dict(key='Formation', name=r'^FORMATION_PANEL_'),
    dict(key='Landing', name=r'^ARG_LANDING_605$'),
    dict(key='Taxi', name=r'^ARG_TAXI_604$'),
    # gear position lights on the landing gear panel (user 2026-11-04): the mod's NOSE / LEFT / RIGHT plates beside the
    # gear handle (DCS arguments 723 / 724 / 725, 'N_GEAR_LIGHT'); green when that gear is down and locked (make_f22.py)
    dict(key='GearNose', name=r'^CP_OFF_NOSE_GEAR$'),
    dict(key='GearLeft', name=r'^CP_OFF_LEFT_GEAR$'),
    dict(key='GearRight', name=r'^CP_OFF_RIGHT_GEAR$'),
    # their amber twins while the gear moves (2026-11-06): copies of the same plates (EXTRA_OBJECTS _gear_amber_plates)
    # - one geometry drawn by two graphics objects stops the model from loading
    # the gear handle's wheel lit red while the gear is in transit, as the F/A-18's (user 2026-11-16): a copy of the
    # wheel riding the handle (EXTRA_OBJECTS _gear_handle_light), hidden while dark
    dict(key='GearHandle', name=r'^CP_GEAR_HANDLE_LIGHT$'),
    dict(key='GearNoseAmber', name=r'^CP_AMBER_NOSE_GEAR$'),
    dict(key='GearLeftAmber', name=r'^CP_AMBER_LEFT_GEAR$'),
    dict(key='GearRightAmber', name=r'^CP_AMBER_RIGHT_GEAR$'),
    # BATT beside the battery switch (same two-plate scheme): amber while the battery alone feeds the DC bus
    dict(key='BattLamp', name=r'^CP_OFF_BATTERY$'),
]
LAMP_COLOURS = {'Formation': (0.10, 0.80, 0.50), 'Landing': (1.0, 0.96, 0.88), 'Taxi': (1.0, 0.96, 0.88),
                'GearNose': (0.25, 1.0, 0.35), 'GearLeft': (0.25, 1.0, 0.35), 'GearRight': (0.25, 1.0, 0.35),
                'BattLamp': (1.0, 0.6, 0.1), 'GearHandle': (1.0, 0.07, 0.03),
                'GearNoseAmber': (1.0, 0.6, 0.1), 'GearLeftAmber': (1.0, 0.6, 0.1), 'GearRightAmber': (1.0, 0.6, 0.1)}

# measurement helpers
WHEEL_ARGS = {101: 'nose', 102: 'main', 103: 'main'}
STAB_ARGS = {15: 'right', 16: 'left'}
MEASURE = dict(
    gear_args=[0, 3, 5],
    wing_root=2.6, wing_z=(-0.3, 0.6), wing_x_min=-4.4,
    fin_z0=1.0, fin_x_max=-1.5,
    fuselage_half_width=2.5,
    # pilot eye: DCS puts it at CockpitLocalPoint (z 1.36, the mod's own note: 'too level with the frame'); at that
    # height the horizon lay on the top edge of the HUD combiner (z 1.125 .. 1.353): 1.29 sees it ~4 deg above centre
    eye=[7.15, 0.0, 1.29],   # visor 7.19-7.27 / 1.28-1.41
)


def _formation_light():
    """Lit formation strip as on the stock F/A-18 (user's night screenshots, 2026-10-30): three segments, brightest down the middle
    with soft edges, not a flat bright slab. Array rows = v (across the panel), columns = u (along it, PANEL_SEGMENTS quads)."""
    import numpy as np
    n = 256
    v, u = np.mgrid[0:n, 0:n] / float(n - 1)
    # lit over the panel's width: a thin core read as a much narrower strip at night than the panel the daylight shows (user)
    across = np.clip((0.5 - np.abs(v - 0.5)) / 0.10, 0.0, 1.0) * (0.72 + 0.28 * np.exp(-((v - 0.5) / 0.28) ** 2))
    along = np.clip(np.minimum(u, 1.0 - u) / 0.03, 0.0, 1.0)
    edge = np.abs(((u * 3.0) % 1.0) - 0.5)
    gaps = 1.0 - 0.75 * np.clip((edge - 0.47) / 0.03, 0.0, 1.0)
    i = (0.06 + 0.94 * across) * along * gaps
    return np.repeat(i[..., None], 3, axis=2).astype(np.float32)


def _gear_label_light():
    """The words of the mod's label atlas (F22_LABLES_GREEN alpha: BATT, NOSE, RIGHT, LEFT) on a lit lens: each plate is
    one quad over its window (23 x 9 mm, UVs around its word), so the whole window glows (user 2026-11-05: only the
    letters lit read as a console screen, not a lamp) - a dim lens (0.08), the letters full with a little halo of light
    spread in the lens. Unlit the plate shows the words a little lighter than the black (write_lamp_textures)."""
    import numpy as np
    import aerofly_tex as X
    a = np.clip(X.load_image(X.find_texture(TEXTURES, 'F22_LABLES_GREEN'))[..., 3], 0, 1).astype(np.float64)
    halo = _blur(a, 4.0 * a.shape[0] / 512.0)
    # (2026-11-06, user: the lens at 0.30 glowed as a lit panel - a dim lens behind bright letters, as a lamp)
    i = np.clip(0.08 + 0.92 * a + 0.30 * halo, 0, 1)
    return np.repeat(i[..., None], 3, axis=2).astype(np.float32)


_GEAR_PLATE = dict(off=(0.10, 0.11, 0.10), specular=0.04, gloss=0.6, reflection=0.03, light=_gear_label_light)
LAMP_SURFACE = {'Formation': dict(off=(0.33, 0.36, 0.32), specular=0.06, gloss=0.3, reflection=0.02, light=_formation_light),
                'GearNose': _GEAR_PLATE, 'GearLeft': _GEAR_PLATE, 'GearRight': _GEAR_PLATE, 'BattLamp': _GEAR_PLATE,
                'GearNoseAmber': _GEAR_PLATE, 'GearLeftAmber': _GEAR_PLATE, 'GearRightAmber': _GEAR_PLATE}

# painted formation strips on f-22a_default: UV boxes (found by projecting the DCS glow boxes onto the skin), a point
# near each strip and its outward normal (the outer and inner skins of the fins and the nose share UVs). None =
# outward from the centreline on whichever side the strip is.
FORMATION_STRIPS = [
    ((0.1335, 0.1719, 0.0757, 0.1328), (-3.15, -2.58, 2.47), (0.0, -0.89, -0.45)),     # right fin
    ((0.4104, 0.4487, 0.0752, 0.1326), (-3.15, 2.58, 2.47), (0.0, 0.89, -0.45)),       # left fin
    ((0.5034, 0.5427, 0.1729, 0.2083), (-2.24, -5.57, 0.20), (0.0, 0.0, 1.0)),         # right wing tip (top)
    ((0.0398, 0.0820, 0.1719, 0.2083), (-2.24, 5.57, 0.20), (0.0, 0.0, 1.0)),          # left wing tip (top)
    ((0.7900, 0.8213, 0.2930, 0.3318), (7.45, 0.0, 0.21), None),                       # nose sides
    ((0.6726, 0.7039, 0.2927, 0.3318), (7.45, 0.0, 0.21), None),
]
PANEL_LIFT = 0.0025          # m above the skin
PANEL_MARGIN = 0.004         # m beyond the painted strip on every side
PANEL_SEGMENTS = 8           # along the strip (follows the skin curvature)


def _strip_mask(img, box):
    """Painted strip texels in a UV box: the yellow paint and the black edge painted along it."""
    import numpy as np
    h, w = img.shape[:2]
    u0, u1, v0, v1 = box
    x0, x1, y0, y1 = int(u0 * w), int(u1 * w), int(v0 * h), int(v1 * h)
    b = img[y0:y1, x0:x1, :3]
    yellow = (b[..., 0] > 0.3) & (b[..., 1] > 0.3) & (b[..., 2] < 0.55 * np.minimum(b[..., 0], b[..., 1]))
    grown = yellow.copy()
    for _ in range(8):
        grown = grown | np.roll(grown, 1, 0) | np.roll(grown, -1, 0) | np.roll(grown, 1, 1) | np.roll(grown, -1, 1)
    return (x0, y0), yellow | ((b.mean(2) < 0.12) & grown)


def TEXTURE_HOOK(out, name, X):
    """Paint the formation strips over with the surrounding skin colour: the panels (EXTRA_OBJECTS) carry the light;
    nothing yellow or black can show at their edges."""
    if UV_GRID_MATERIAL and name == UV_GRID_MATERIAL:
        _uv_grid(X, out, name)
        return
    if name.upper() in COCKPIT_WEAR:
        _cockpit_wear(out, name, X)
        return
    if name != 'f_22a_default':
        return
    import numpy as np
    path = os.path.join(out, name + '_color.png')
    c = X.load_image(path)
    rgb = c[..., :3].copy()
    for box, _, _ in FORMATION_STRIPS:
        (x0, y0), m = _strip_mask(rgb, box)
        for _ in range(2):
            m = m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)
        ring = m.copy()
        for _ in range(4):
            ring = ring | np.roll(ring, 1, 0) | np.roll(ring, -1, 0) | np.roll(ring, 1, 1) | np.roll(ring, -1, 1)
        region = rgb[y0:y0 + m.shape[0], x0:x0 + m.shape[1]]
        region[m] = np.median(region[ring & ~m], axis=0)
    _paint_out_decor(rgb)
    X.save_png(path, rgb, limit=c.shape[1])



# Cockpit wear (user 2026-11-04: the DCS cockpit textures are nearly flat - the tub one tone, the normal maps empty - and
# read lifeless next to the stock F/A-18 and our Su-35). Painted from the cockpit's own geometry, nothing invented:
# work/bake/<material>_wear.png (tools/bake_cockpit_light.py BAKE_ONLY=wear) R = convex edges (4 mm bevel x short AO:
# plate edges, the Dzus fastener heads, knob rims, sill and glareshield edges), G/B = coarse (~17 cm) / fine (~2 cm) 3D
# noise in metres (seamless across UV islands); <material>_pos/_nrm.png = where each texel is and which way it faces;
# the accepted AO bake (<material>_ao.png: crevices = where it is darker than around).
# Second version (user: the first put the same noise and wear on every surface - read as a stylised material): wear by
# ZONES where the pilot touches the cockpit - boots on the floor in front of the seat and on the pedals, elbows on the
# sill tops, hands at the throttle and stick and on the consoles' inner lips, legs on the consoles' inner walls, fingers
# on the ICP keys and MFD bezel buttons; far plates, the instrument panel face and the glareshield keep only a trace on
# their edges. No fine noise in the tone, the coarse one barely (a few 1/1000).
# Colour = base x grime in the crevices + coarse tone + paint rubbed lighter on the edges (edge x zone, broken up by
# the noise) + scuffs on flat surfaces inside the contact zones; worn texels a little glossier. The panel lettering
# (alpha masks, LABEL_ILLUMINATION) is left untouched: it is already at the converter's white limit (0.82).
# Third version (user 2026-11-05: v2 read low resolution and without detail - its masks were 2048 bakes stretched on the
# 4096 maps and its rubbed patches and their gloss were soft blotches, cloudy in the game's reflections): detail at
# the colour map's own resolution from a 3D noise of each texel's position (16-bit position bake <material>_pos16.npz,
# 0.06 mm; the 8-bit one stepped 16 mm), nothing soft and large left:
#  - chips: on the strong convex edges (the bake's bevel mask) only, ragged where the fine (6 mm) noise is high, the
#    paint gone to the primer / aluminium (METAL) - about a quarter of an edge's length at full wear;
#  - a slight rub along the edges; thin straight scratches (noise stretched 0.15 m along, 4 mm across a random direction
#    in the surface, three families, sparse) on the flat parts inside the contact zones;
#  - grime only in tight crevices (AO darker than 3 px around), broken up by a 12 mm noise; on the floor fine dust specks;
#  - gloss on chips and scratches only.
# base = share of the wear outside the contact zones, chip = how far a chip goes to METAL, rub / scratch / dust =
# lightening, grime = darkening in crevices, gloss = added gloss on chips and scratches
COCKPIT_WEAR = {
    'F22_PANEL_LEFT':  dict(base=0.20, chip=0.55, rub=0.05, scratch=0.05, grime=0.45, dust=0.0, gloss=0.25),
    'F22_PANEL_RIGHT': dict(base=0.20, chip=0.55, rub=0.05, scratch=0.05, grime=0.45, dust=0.0, gloss=0.25),
    'F22_PANEL_FRONT': dict(base=0.15, chip=0.40, rub=0.03, scratch=0.02, grime=0.40, dust=0.0, gloss=0.15),
    'F22_UFC':         dict(base=0.25, chip=0.45, rub=0.05, scratch=0.04, grime=0.40, dust=0.0, gloss=0.25),
    'F22_MFD':         dict(base=0.15, chip=0.40, rub=0.04, scratch=0.03, grime=0.35, dust=0.0, gloss=0.20),
    'F22_TUB':         dict(base=0.15, chip=0.55, rub=0.05, scratch=0.07, grime=0.50, dust=0.05, gloss=0.20),
    'F22_HOOD':        dict(base=0.15, chip=0.30, rub=0.03, scratch=0.02, grime=0.35, dust=0.0, gloss=0.10),
    'F22_SIDE':        dict(base=0.15, chip=0.45, rub=0.04, scratch=0.05, grime=0.45, dust=0.02, gloss=0.15),
    'F22_THROTTLE':    dict(base=0.40, chip=0.50, rub=0.05, scratch=0.04, grime=0.35, dust=0.0, gloss=0.35),
    'F22_STICK':       dict(base=0.40, chip=0.50, rub=0.05, scratch=0.04, grime=0.35, dust=0.0, gloss=0.35),
    'F22_RUDDER':      dict(base=0.30, chip=0.60, rub=0.06, scratch=0.08, grime=0.45, dust=0.04, gloss=0.30),
    'F22_ACES_II':     dict(base=0.20, chip=0.25, rub=0.03, scratch=0.02, grime=0.35, dust=0.0, gloss=0.05),
}
WEAR_METAL = (0.36, 0.36, 0.37)      # bare aluminium / primer showing through a chip
# contact points measured from the position bake (2026-11-04): the throttle and stick grips; consoles z 0.57-0.66,
# |y| 0.28-0.54; floor (tub, facing up) z 0.25-0.45; sill and canopy rail tops z > 0.70, |y| > 0.42; consoles' inner
# walls (F22_SIDE) |y| 0.27, z 0.28-0.73; pedals x 7.5-8.0
WEAR_HANDS = [(7.41, 0.34, 0.68), (7.46, -0.34, 0.65)]
WEAR_BOX = ((5.5, -1.2, -0.2), (9.5, 1.2, 2.2))      # = bake_cockpit_light.ZONE_BOX


def wear_zone(name, P, N):
    """0..1 contact weight of each texel (P position m, N world normal)."""
    import numpy as np
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    ay = np.abs(y)
    up = np.clip((N[..., 2] - 0.5) / 0.3, 0, 1)
    sm = lambda a, lo, hi: np.clip((a - lo) / (hi - lo), 0, 1)
    hand = np.zeros(x.shape)
    for h in WEAR_HANDS:
        d = np.sqrt((x - h[0]) ** 2 + (y - h[1]) ** 2 + (z - h[2]) ** 2)
        hand = np.maximum(hand, np.exp(-(d / 0.16) ** 2))
    n = name.upper()
    if n in ('F22_PANEL_LEFT', 'F22_PANEL_RIGHT'):
        lip = sm(0.36 - ay, 0.0, 0.05) * sm(x, 7.0, 7.15)          # the inner lip beside the pilot's thighs
        return np.maximum(hand, 0.7 * lip)
    if n == 'F22_TUB':
        floor = up * sm(0.47 - z, 0.0, 0.04) * sm(x, 7.15, 7.35)   # in front of the seat (behind it no boot reaches)
        sill = up * sm(z, 0.68, 0.72) * sm(ay, 0.40, 0.45)        # elbows, climbing in
        return np.maximum(np.maximum(floor, 0.9 * sill), hand)
    if n == 'F22_SIDE':
        return 0.6 * sm(0.64 - z, 0.0, 0.06) * sm(x, 7.0, 7.2)       # thighs and boots along the consoles' inner walls
    if n in ('F22_THROTTLE', 'F22_STICK'):
        return np.maximum(0.5, hand)
    if n == 'F22_RUDDER':
        return np.clip(0.3 + np.maximum(N[..., 2], -N[..., 0]), 0, 1)  # treads facing up / back to the boots
    if n == 'F22_UFC':
        return np.full(x.shape, 0.6)                                 # the keypad
    if n == 'F22_MFD':
        return 0.35 * sm(1.0 - z, 0.0, 0.1)                          # bezel buttons of the lower displays
    if n == 'F22_ACES_II':
        return 0.4 * sm(z, 0.40, 0.45) * sm(0.85 - z, 0.0, 0.05)      # cushion and arm areas
    return np.zeros(x.shape)


def _baked(name, suffix):
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'work', 'bake')
    if not os.path.isdir(d):
        return None
    f = {x.lower(): x for x in os.listdir(d)}.get(name.lower() + suffix)
    return os.path.join(d, f) if f else None


def _to_size(a, shape):
    """Bilinear resample (the 2048 bakes onto 4096 colour maps: nearest left stair steps on the edge wear)."""
    import numpy as np
    if a.shape[:2] == tuple(shape):
        return a
    y = (np.arange(shape[0]) + 0.5) * a.shape[0] / shape[0] - 0.5
    x = (np.arange(shape[1]) + 0.5) * a.shape[1] / shape[1] - 0.5
    y0 = np.clip(np.floor(y).astype(int), 0, a.shape[0] - 1)
    x0 = np.clip(np.floor(x).astype(int), 0, a.shape[1] - 1)
    y1, x1 = np.minimum(y0 + 1, a.shape[0] - 1), np.minimum(x0 + 1, a.shape[1] - 1)
    fy = np.clip(y - y0, 0, 1).reshape((-1, 1) + (1,) * (a.ndim - 2))
    fx = np.clip(x - x0, 0, 1).reshape((1, -1) + (1,) * (a.ndim - 2))
    top = a[y0][:, x0] * (1 - fx) + a[y0][:, x1] * fx
    bot = a[y1][:, x0] * (1 - fx) + a[y1][:, x1] * fx
    return top * (1 - fy) + bot * fy


def _cockpit_wear(out, name, X):
    import numpy as np
    import time
    t0 = time.time()
    p = COCKPIT_WEAR[name.upper()]
    wf, af, nf_ = (_baked(name, s) for s in ('_wear.png', '_ao.png', '_nrm.png'))
    pf = _baked(name, '_pos16.npz')
    if not (wf and af and nf_ and pf):
        print('WEAR no baked wear / AO / zone maps for', name, '(BAKE_ONLY=wear, zones)')
        return
    cpath = os.path.join(out, name + '_color.png')
    c = X.load_image(cpath)[..., :3].astype(np.float64)
    sh = c.shape[:2]
    w = _to_size(X.load_image(wf)[..., :3].astype(np.float32), sh)
    isl = w.sum(2) > 0
    idx = np.nonzero(isl)
    lo, hi = np.array(WEAR_BOX[0]), np.array(WEAR_BOX[1])
    p16 = np.load(pf)['p'].astype(np.float32) / 65535.0
    P = lo + _to_size(p16, sh)[idx].astype(np.float64) * (hi - lo)
    del p16
    N = _to_size(X.load_image(nf_)[..., :3].astype(np.float32), sh)[idx].astype(np.float64) * 2 - 1
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
    edge = np.clip(w[..., 0][idx], 0, 1).astype(np.float64)
    a0 = X.load_image(af)[..., 0].astype(np.float64)
    s = a0.shape[0] / 2048.0
    crev = _to_size(np.clip((_blur(a0, 3.0 * s) - a0) * 5.0, 0, 1), sh)[idx]
    zone = np.clip(wear_zone(name, P[None], N[None])[0], 0, 1)
    keep = np.zeros(sh)
    d = X.find_texture(TEXTURES, name.upper())
    if d:
        al = X.load_image(d)[..., 3]
        if al.mean() < 0.5:
            keep = _grow(_to_size(al, sh) > 0.3, 2).astype(np.float64)
    free = 1.0 - keep[idx]
    W = p['base'] + (1.0 - p['base']) * zone
    seed = sum(map(ord, name))
    chipn = _fbm(P, 0.006, 3, seed)
    # chips: on the strong edges only, in ragged bits where the fine noise is high (about a quarter of the edge length
    # at full wear) - not a continuous light outline
    chip = _smooth(np.minimum(edge * W * 1.4, 1.0) * _smooth(chipn, 0.56, 0.62), 0.55, 0.62) * free
    rub = _smooth(edge, 0.3, 1.0) * W * free * 0.5
    flat = np.clip(1.0 - 2.0 * edge, 0, 1)
    scr = _scratches(P, N, seed + 7) * zone * flat * free
    dirt = crev * (0.7 + 0.6 * _fbm(P, 0.012, 2, seed + 3))
    up = np.clip((N[:, 2] - 0.6) / 0.3, 0, 1)
    speck = _smooth(_fbm(P, 0.0012, 2, seed + 11), 0.62, 0.70)
    dust = p['dust'] * zone * up * (0.3 + speck) * free
    cc = c[idx]
    col = cc * (1.0 - p['grime'] * np.clip(dirt, 0, 1))[:, None]
    col = col + (p['rub'] * rub + p['scratch'] * scr + dust)[:, None]
    ca = (p['chip'] * chip)[:, None]
    col = col * (1 - ca) + np.array(WEAR_METAL)[None] * ca
    res = c.copy()
    res[idx] = col
    X.save_png(cpath, X.clamp_colour(res), limit=sh[1])
    spath = os.path.join(out, name + '_specular.png')
    gpath = os.path.join(out, name + '_specular_alpha.png')
    if os.path.exists(spath) and os.path.exists(gpath):
        sp = X.load_image(spath)[..., :3].astype(np.float64)
        g = X.load_image(gpath)[..., 0].astype(np.float64)
        shine = np.zeros(sh)
        shine[idx] = np.clip(chip + 0.5 * scr + 0.3 * rub * zone, 0, 1)
        shine = _to_size(shine, sp.shape[:2])
        sp = np.clip(sp + (0.4 * p['gloss'] * shine)[..., None], 0, 1)
        g = np.clip(g + p['gloss'] * shine, 0, 1)
        X.save_png(spath, sp, g, limit=sp.shape[1])
    print('WEAR %s: %d texels, chip %.4f, scratch %.4f, dirt %.3f, %.0f s' % (
        name, len(idx[0]), chip.mean(), scr.mean(), dirt.mean(), time.time() - t0))


def _hash3(ix, iy, iz, seed):
    import numpy as np
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF).astype(np.float64) / float(0xFFFFFF)


def _vnoise(P, scale, seed=0):
    """3D value noise 0..1 of points P (n x 3, metres) at feature size scale (m); seamless across UV islands."""
    import numpy as np
    q = P / scale
    i = np.floor(q).astype(np.int64)
    f = q - i
    f = f * f * (3 - 2 * f)
    out = np.zeros(len(P))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out += w * _hash3(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def _fbm(P, scale, octaves, seed=0):
    import numpy as np
    v, a, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        v = v + a * _vnoise(P, scale / 2 ** o, seed + o)
        tot += a
        a *= 0.5
    return v / tot


def _smooth(a, lo, hi):
    import numpy as np
    return np.clip((a - lo) / (hi - lo), 0, 1)


def _scratches(P, N, seed, along=0.15, across=0.004, density=0.25):
    """Thin straight-ish scratches: ridges of a noise stretched along a direction in the surface, in a few families."""
    import numpy as np
    out = np.zeros(len(P))
    rng = np.random.RandomState(seed)
    for fam in range(3):
        d = rng.normal(size=3)
        d /= np.linalg.norm(d)
        # direction projected into each texel's tangent plane
        t = d[None, :] - (N @ d)[:, None] * N
        t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-9
        b = np.cross(N, t)
        u = (P * t).sum(1)
        v = (P * b).sum(1)
        w = (P * N).sum(1)
        Q = np.stack([u / along, v / across, w / along], 1)
        n = _vnoise(Q, 1.0, seed * 10 + fam)
        ridge = 1.0 - np.abs(2.0 * n - 1.0)
        line = _smooth(ridge, 0.955, 0.99)
        sparse = _smooth(_vnoise(P, 0.02, seed * 10 + fam + 5), 1.0 - density, 1.0 - density + 0.1)
        out = np.maximum(out, line * sparse)
    return out


# Decor of the mod's skin that the real aircraft (06-4123, 525 FS, AK) does not carry (agreed with the user 2026-11-04):
#  - the light-blue band with bulldog paw prints along the fin and rudder tips: only the 525 FS flagship 10-4195 wore
#    paw prints (May 2012, PACAF/JBER captions); a regular 525 FS jet in 2009 (Commons "525th Fighter Squadron - F-22 -
#    Elmendorf.jpg") has plain fin tips
#  - the round badge and the 3rd Wing shield on the fuselage sides below the chines (x 4.3-4.6 m): no photo of a regular
#    jet shows them
# Kept: AK, AF 06 123, the PACAF badge, '123' on the nose gear doors, the national insignia, the rescue/danger stencils.
# Boxes in texture pixels at 4096, origin top-left (as an image viewer shows the map), mode 'blue' = the bluish band and
# everything it encloses (the paws), 'band' = the same, a straight band across the box (each row filled between its
# first and last band texel: the paws' feet touch the band edge and are not enclosed), 'light' = linework lighter than
# the skin around it.
DECOR_REMOVE = [
    ((470, 3490, 700, 3610), 'band'),       # fin A tip, band (both skins share the UVs)
    ((150, 3930, 380, 4030), 'band'),       # fin A, the band's other part on the island
    ((1690, 3500, 1900, 3610), 'band'),     # fin B
    ((2010, 3930, 2230, 4030), 'band'),
    ((3370, 2510, 3720, 2650), 'blue'),     # rudder tips
    ((3360, 3080, 3700, 3220), 'blue'),
    ((2040, 2595, 2120, 2655), 'light'),    # round badge, left fuselage side
    ((2622, 2594, 2690, 2658), 'light'),    # 3rd Wing shield, right side
]


def _grow(m, n):
    import numpy as np
    for _ in range(n):
        m = m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)
    return m


def _fill_holes(m):
    """Pixels not in m and not connected to the box border through non-m pixels (the paws inside the band)."""
    import numpy as np
    out = np.zeros_like(m)
    out[0, :], out[-1, :], out[:, 0], out[:, -1] = ~m[0, :], ~m[-1, :], ~m[:, 0], ~m[:, -1]
    free = ~m
    while True:
        nxt = _grow(out, 1) & free
        if nxt.sum() == out.sum():
            return m | ~out
        out = nxt


def _blur(a, r):
    """Separable gaussian, edges extended (zero padding darkened the box borders: the whole box read as decor)."""
    import numpy as np
    n = int(3 * r) + 1
    k = np.exp(-0.5 * (np.arange(-n, n + 1) / float(r)) ** 2)
    k /= k.sum()
    a = np.pad(np.asarray(a, np.float64), n, mode='edge')
    a = np.apply_along_axis(lambda v: np.convolve(v, k, mode='valid'), 0, a)
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode='valid'), 1, a)


def _shrink(m, n):
    return ~_grow(~m, n)


def decor_mask(rgb, box, mode):
    """(row0, col0), mask of the decor inside box (array rows count from the bottom: load_image)."""
    import numpy as np
    h = rgb.shape[0]
    s = h / 4096.0
    x0, y0, x1, y1 = [int(round(v * s)) for v in box]
    r0, r1 = h - y1, h - y0
    b = rgb[r0:r1, x0:x1]
    lum = b.mean(2)
    skin = lum > 0.12                                   # the island; the black background around it is no source
    src = _shrink(lum > 0.25, 2)                        # fill sources: clean skin, not the dark rim at the island edge
    if mode in ('blue', 'band'):
        bl = _blur(b[..., 2] - b[..., 0], 1.5)
        m = _grow(_shrink((bl > 0.05) & skin, 2), 2)           # opening: no stray bluish grains of the skin
        m = _shrink(_grow(m, 9), 9)                             # closing: the paws (about 10 px) inside the band
        m = _fill_holes(m) & skin
        if mode == 'band':
            idx = np.arange(m.shape[1])
            for r in np.nonzero(m.any(1))[0]:
                c = idx[m[r]]
                m[r, c.min():c.max() + 1] = True
            m &= skin
        m = _grow(m, 2) & skin
    else:
        base = np.median(lum[skin])
        m = (lum - _blur(np.where(skin, lum, base), 6.0) > 0.025) & skin
        m = _fill_holes(_grow(m, 2)) & skin
        m = _grow(m, 1) & skin
    return (r0, x0), m, src


def _nblur(a, w, r, blur):
    """Normalized convolution: blur of a over the texels where w (no leak of the masked ones)."""
    import numpy as np
    if a.ndim == 3:
        return np.stack([_nblur(a[..., k], w, r, blur) for k in range(a.shape[2])], -1)
    return blur(a * w, r) / (blur(w.astype(np.float64), r) + 1e-9)


def _guided_fill(b, m, known, G, blur, grow, skin):
    """Fill b inside m along the guide G (the model's own roughness map, same UVs, no decor): tone spreads only
    between texels of like guide value (one panel), the panel lines and grain come from the guide's high-pass."""
    import numpy as np
    Gl = blur(G, 1.0)
    L = _nblur(b, known, 2.0, blur)                      # tone of the known skin, no masked texel leaks in
    d = np.abs(Gl - np.roll(Gl, 1, 1))[known & np.roll(known, 1, 1)]
    sg = max(3.0 * float(np.median(d)), 0.004)
    out = L.copy()
    kn = known.copy()
    todo = m & ~known
    thr = 0.6
    while todo.any():
        acc = np.zeros(b.shape)
        ws = np.zeros(b.shape[:2])
        wmax = np.zeros(b.shape[:2])
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if not (dy or dx):
                    continue
                k = np.roll(np.roll(kn, dy, 0), dx, 1)
                gq = np.roll(np.roll(Gl, dy, 0), dx, 1)
                w = np.exp(-((Gl - gq) / sg) ** 2) * k
                acc += np.roll(np.roll(out, dy, 0), dx, 1) * w[..., None]
                ws += w
                wmax = np.maximum(wmax, w)
        new = todo & (wmax > thr)
        if not new.any():
            if thr < 1e-6:
                break
            thr *= 0.5
            continue
        out[new] = acc[new] / ws[new][:, None]
        kn |= new
        todo &= ~new
        thr = 0.6
    # left over (guide unlike every neighbour, e.g. the island's rim): plain onion peel, then from any skin
    for pool in (kn, kn | skin):
        kn2 = pool.copy()
        while todo.any():
            acc = np.zeros(b.shape)
            cnt = np.zeros(b.shape[:2])
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy or dx:
                        k = np.roll(np.roll(kn2, dy, 0), dx, 1)
                        src_ = out if pool is kn else np.where(kn[..., None], out, b)
                        acc += np.roll(np.roll(src_, dy, 0), dx, 1) * k[..., None]
                        cnt += k
            new = todo & (cnt > 0)
            if not new.any():
                break
            out[new] = acc[new] / cnt[new][:, None]
            kn2 |= new
            kn |= new
            todo &= ~new
    # seams where fronts met: smoothing inside the patch, weighted by the guide (no blur across a panel edge)
    for _ in range(3):
        acc = np.zeros(b.shape)
        ws = np.zeros(b.shape[:2])
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                gq = np.roll(np.roll(Gl, dy, 0), dx, 1)
                w = np.exp(-((Gl - gq) / sg) ** 2) * np.exp(-(dy * dy + dx * dx) / 8.0)
                w = w * np.roll(np.roll(kn, dy, 0), dx, 1)
                acc += np.roll(np.roll(out, dy, 0), dx, 1) * w[..., None]
                ws += w
        sm = acc / (ws[..., None] + 1e-9)
        out[m] = sm[m]
    # detail: colour high-pass = k * guide high-pass, k from the clean skin around the patch (least squares)
    Ghp = G - _nblur(G, skin, 3.0, blur)                 # over the skin only: the black around the island is no line
    Chp = b - _nblur(b, known, 3.0, blur)
    ring = known & grow(m, 40) & ~grow(m, 2)
    kk = []
    for c in range(3):
        x, y = Ghp[ring], Chp[..., c][ring]
        kk.append(float((x * y).sum() / ((x * x).sum() + 1e-12)))
    det = np.stack([kk[c] * Ghp for c in range(3)], -1)
    lo = np.stack([np.percentile(Chp[..., c][ring], 0.5) for c in range(3)])
    hi = np.stack([np.percentile(Chp[..., c][ring], 99.5) for c in range(3)])
    det = np.clip(det, lo, hi)                          # no deeper line than the skin around has
    res = Chp - det
    # the colour's own grain the guide lacks: residual of the nearest clean offset, clipped (no lines copied)
    clean = known & ~grow(m, 3)
    rr, cc = np.nonzero(m)
    h, w_ = m.shape
    best = None
    for d in range(4, max(h, w_), 2):
        for dr, dc in ((d, 0), (-d, 0), (0, d), (0, -d), (d, d), (d, -d), (-d, d), (-d, -d)):
            r2, c2 = rr + dr, cc + dc
            ok = (r2 >= 0) & (r2 < h) & (c2 >= 0) & (c2 < w_)
            ok[ok] = clean[r2[ok], c2[ok]]
            if ok.mean() > 0.9:
                best = (dr, dc, ok)
                break
        if best:
            break
    grain = np.zeros(b.shape)
    if best:
        dr, dc, ok = best
        lim = 2.5 * float(np.median(np.abs(res[clean]))) + 1e-4
        g = np.zeros((len(rr), 3))
        g[ok] = np.clip(res[rr[ok] + dr, cc[ok] + dc], -lim, lim)
        grain[rr, cc] = g
    out = np.where(m[..., None], out + det + grain, b)
    return np.clip(out, 0, 1), kk, best and best[:2], sg


def _paint_out_decor(rgb, pad=96):
    """Second version (user 2026-11-05: the first, a smoothed fill, blurred the straight panel edges and broke the paint
    boundaries): the mod's own F-22A_Default_RoughMet (same UVs; its R channel carries every panel and line of the skin and
    none of the decor - checked on all eight boxes) guides the fill: the tone spreads only between texels of like
    roughness (one panel, edges kept straight), the panel lines and grain come from its high-pass (_guided_fill)."""
    import numpy as np
    import aerofly_tex as X
    H, W = rgb.shape[:2]
    g = X.load_image(X.find_texture(TEXTURES, 'F-22A_Default_RoughMet'))[..., 0].astype(np.float64)
    g = _to_size(g, (H, W))
    for box, mode in DECOR_REMOVE:
        (r0, c0), m, _ = decor_mask(rgb, box, mode)
        if not m.any():
            print('DECOR nothing found in', box)
            continue
        R0, C0 = max(r0 - pad, 0), max(c0 - pad, 0)
        R1, C1 = min(r0 + m.shape[0] + pad, H), min(c0 + m.shape[1] + pad, W)
        win = rgb[R0:R1, C0:C1]
        mw = np.zeros(win.shape[:2], bool)
        mw[r0 - R0:r0 - R0 + m.shape[0], c0 - C0:c0 - C0 + m.shape[1]] = m
        b = win.astype('float64')
        src = _shrink(b.mean(2) > 0.25, 2)
        out, kk, off, _ = _guided_fill(b, mw, src & ~mw, g[R0:R1, C0:C1], _blur, _grow, b.mean(2) > 0.12)
        win[...] = out
        print('DECOR %s %s: %d texels, line gain %.2f, grain from %s' % (mode, box, m.sum(), kk[1], off))


# the mod's pilot as DCS shows him (body, head, HGU-55/P helmet, closed visor shell, mirror visor; the other visors and
# the sunglasses are hidden by DCS at argument 0): one part, hidden in the pilot's own view (make_f22.py ShowInside)
PILOT_MATERIAL = re.compile(r'^F22A_(PILOT|HELMET|VISOR_MIRROR)$')
# their maps as DCS uses them: the materials list no RoughMet (DCS finds <diffuse>_RoughMet by name - without it the
# suit, helmet and visor were one even matte), and the normal maps carry cloth folds and straps, which the skin's
# panel-line high-pass removed - a wider one and a deeper range (tools/aerofly_tex.py height_from_normals)
# The mod's pilot normal map is nearly flat (deviation 0.007 against the skin's 0.035): the folds, straps and seams
# are painted into its colour map as shading - their relief is taken from there (aerofly_tex.albedo_relief)
MATERIAL_TEXTURE_OPTIONS = [
    (r'^(F22A_PILOT|HGU-55P)$', dict(roughmet_by_name=True, normal_strength=1.0,
                                    height=dict(depth_px=12.0, sigma_px=40.0, albedo=0.06))),
    (r'^HELMET_GLASS_MIRROR$', dict(roughmet_by_name=True))]


def EXTRA_OBJECTS(objs, mesh_object, X, tex_dir):
    for o in objs:
        if PILOT_MATERIAL.match(o.get('edm_material', '')):
            o['aerofly_part'] = 'Pilot'
    return (_formation_panels(objs, mesh_object, X, tex_dir) + _store_objects(X, tex_dir) + _nozzle_fire(objs, mesh_object) +
            _icp_patch(objs, mesh_object) + _flcs_bushing(objs, mesh_object) + _gear_amber_plates(objs) + _gear_handle_light(objs) +
            _gear_debris(objs, _burst_tyres(objs)))


# sheared struts (block 3, 2026-11-11): the lower strut and the wheel of each gear leg, copied as the debris that rolls
# away on its own body (breakage_f22.gear_shear) - its parts on the aircraft hide at the shear. The leg's upper part
# (main: A_51 / A_56, nose: A_6 with the piston) stays, broken off below. DCS animation nodes of the parts per gear:
# lower strut (main: the compression-driven link, nose: the steering fork), wheel; the wheel twice (intact, burst)
GEAR_DEBRIS = {'L': ('53,51', '54,53,51'), 'R': ('58,56', '59,58,56'), 'N': ('14,13,6', '15,14,13,6')}


def _gear_debris(objs, flats):
    out = []
    for key, (lower, wheel) in GEAR_DEBRIS.items():
        for o in objs:
            nodes = str(o.get('edm_anim_nodes', ''))
            if o.get('edm_source') == 'cockpit' or 'aerofly_part' in o or nodes not in (lower, wheel):
                continue
            c = o.copy()
            c.data = o.data.copy()
            c.name = 'DEBRIS_%s_%s' % (key, o.name)
            c['aerofly_part'] = 'D_GearDebris%s' % key if nodes == lower else 'D_GearDebrisWheel%s' % key
            c['aerofly_keep_all'] = 1
            out.append(c)
        flat = next(f for f in flats if f.name == 'TYRE_BURST_' + key)
        c = flat.copy()
        c.data = flat.data.copy()
        c.name = 'DEBRIS_%s_FLAT' % key
        c['aerofly_part'] = 'D_GearDebrisWheel%sFlat' % key
        c['aerofly_keep_all'] = 1
        out.append(c)
    parts = sorted({o['aerofly_part'] for o in out})
    assert len(parts) == 9, parts
    print('gear debris: %s' % ', '.join('%s %d' % (p, sum(1 for o in out if o['aerofly_part'] == p)) for p in parts))
    return flats + out


# burst tyres (block 3 of docs/reference/FAILURES.md, 2026-11-11): a copy of each wheel with the rubber outside the rim
# pressed onto it - the tyre after a burst, run flat on the rim, ground down and folded out at the sidewalls. It spins
# with the rim (the sidewall lettering turns as before). The physics lowers that wheel's hull onto its rim at the same
# time (breakage_f22.tyre_hubs), so the drawn rim stands at its rim radius over the ground and the squashed rubber
# just touches it. The DCS model's own burst nose wheel (F-22A_Gear_Nose_Wheal_DAMAGE, arg 134) keeps both sidewalls
# at full radius: with the wheel on its rim they would sink 13 cm into the ground - not used.
# spin argument -> wheel key, rim radius (m, the physics hulls' RimRadius)
TYRE_WHEELS = {101: ('N', 0.16146), 102: ('L', 0.226039), 103: ('R', 0.226039)}
TYRE_SQUASH = 0.12          # rubber height kept, of the tyre's own (0.185 m on a main wheel -> 2 cm)
TYRE_RAGGED = 0.08          # + up to this much, varying round the wheel (torn rubber)
TYRE_FOLD = 0.2           # sidewalls fold out by this part of the height they lose (~3 cm: clear of brake and strut)


def _burst_tyres(objs):
    import math
    import numpy as np
    from mathutils import Vector
    out = []
    for o in objs:
        args = [int(a) for a in str(o.get('edm_anim_args', '')).split(',') if a.strip().isdigit()]
        spin = [a for a in args if a in TYRE_WHEELS]
        if not spin or o.get('edm_source') == 'cockpit' or 'DAMAGE' in o.name or 'aerofly_part' in o:
            continue
        key, rim = TYRE_WHEELS[spin[0]]
        mw = o.matrix_world
        w = np.array([tuple(mw @ v.co) for v in o.data.vertices])
        centre = (w.min(0) + w.max(0)) / 2
        evals, evecs = np.linalg.eigh(np.cov((w - centre).T))
        axle = evecs[:, 0]                       # a wheel is a disc: least spread along its axle
        d = w - centre
        ax = d @ axle
        radial = d - np.outer(ax, axle)
        r = np.linalg.norm(radial, axis=1)
        e1 = radial[np.argmax(r)] / r.max()
        e2 = np.cross(axle, e1)
        theta = np.arctan2(radial @ e2, radial @ e1)
        k = TYRE_SQUASH + TYRE_RAGGED * (0.5 + 0.5 * np.sin(7 * theta + 0.6) * np.cos(3 * theta))
        outer = r > rim
        lost = np.where(outer, (r - rim) * (1 - k), 0.0)
        r2 = r - lost
        ax2 = ax + np.sign(ax) * lost * TYRE_FOLD
        scale = np.where(r > 1e-9, r2 / np.maximum(r, 1e-9), 1.0)
        w2 = centre + np.outer(ax2, axle) + radial * scale[:, None]
        c = o.copy()
        c.data = o.data.copy()
        c.name = 'TYRE_BURST_' + key
        inv = mw.inverted()
        for v, p in zip(c.data.vertices, w2):
            v.co = inv @ Vector(p)
        c['aerofly_part'] = 'A_%s__FLAT' % str(o.get('edm_anim_nodes', '')).replace(',', '_')
        c['aerofly_keep_all'] = 1
        out.append(c)
        print('burst tyre %s: %s, rim %.3f m, outer %.3f -> %.3f m, %d of %d vertices squashed' % (
            key, c['aerofly_part'], rim, r.max(), r2.max(), int(outer.sum()), len(r)))
    assert sorted(o.name for o in out) == ['TYRE_BURST_L', 'TYRE_BURST_N', 'TYRE_BURST_R'], [o.name for o in out]
    return out


def _gear_amber_plates(objs):
    """Copies of the NOSE / LEFT / RIGHT gear lamp plates for their amber state (LAMPS GearNoseAmber...), 0.3 mm towards
    the pilot (the first, exactly on the plates, came out empty - 'unable to compute bounding sphere' in the game's log:
    the export drops coincident faces)."""
    from mathutils import Vector
    eye = Vector(MEASURE['eye'])
    out = []
    for o in objs:
        m = re.match(r'^CP_OFF_(NOSE|LEFT|RIGHT)_GEAR$', o.name)
        if m:
            c = o.copy()
            c.data = o.data.copy()
            c.name = 'CP_AMBER_%s_GEAR' % m.group(1)
            p = c.data.polygons[0]
            nrm = (o.matrix_world.to_3x3() @ p.normal).normalized()
            if nrm.dot(eye - o.matrix_world @ p.center) < 0:
                nrm = -nrm
            c.matrix_world = __import__('mathutils').Matrix.Translation(nrm * 0.0003) @ o.matrix_world
            out.append(c)
    print('gear lamp amber plates: %d' % len(out))
    return out


def _gear_handle_light(objs):
    """The gear handle's wheel once more as a lamp (LAMPS GearHandle): the faces of the handle (CP__7.003, animated by
    cockpit argument 83) within 19 mm of the wheel's centre (CLICK_GRIPS: the wheel is 30 mm across, 16 mm wide), blown
    up 3 % about that centre - half a millimetre over the wheel (coincident copies are dropped by the export). The copy
    keeps the handle's animation: it rides with it."""
    import bmesh
    from mathutils import Vector
    centre = Vector(CLICK_GRIPS['GearLever'][0])
    for o in objs:
        if o.name != 'CP__7.003':
            continue
        c = o.copy()
        c.data = o.data.copy()
        c.name = 'CP_GEAR_HANDLE_LIGHT'
        M = o.matrix_world
        Mi = M.inverted()
        bm = bmesh.new()
        bm.from_mesh(c.data)
        far = [f for f in bm.faces if any((M @ v.co - centre).length > 0.019 for v in f.verts)]
        bmesh.ops.delete(bm, geom=far, context='FACES')
        for v in bm.verts:
            v.co = Mi @ (centre + (M @ v.co - centre) * 1.03)
        n = len(bm.faces)
        bm.to_mesh(c.data)
        bm.free()
        print('gear handle light: %d faces of the wheel' % n)
        return [c] if n else []
    print('WARNING gear handle light: CP__7.003 not found')
    return []


def _flcs_bushing(objs, mesh_object):
    """FLCS BIT switch base: the ALT FLAPS toggle's own nut (washer, ring, dome: the F22_SWITCH faces of the static panel
    within 7 mm of its axis, below its bat) copied under the BIT bat, with its UVs (the same light grey), scaled down to
    fit under the closed guard: radius to 4.3 mm, height from the slot floor 1.6 mm up to 4.9 mm (the closed lid comes
    down to 5.1 mm over the bat's foot, scratchpad base_probe2.py). User 2026-11-07: under the lifted guard the bat stood
    on black rails, "not a full switch" next to its neighbours with their grey round bases; the first base (2026-11-06)
    was a bare 12-sided bushing in the rails' black."""
    import numpy as np
    k = next(x for x in SWITCH_PARTS if x['part'] == 'K_FlcsBit')
    af = next(x for x in SWITCH_PARTS if x['part'] == 'K_AltFlaps')
    n = np.array(k['above'][0]); base = k['above'][1]; base_af = af['above'][1]
    lat = np.array(_LAT_L); fwd = np.cross(lat, n)
    piv_af = np.array(af['pivot'])
    R, H_TOP = 0.007, 0.0115
    src = []                                              # (world corners, uvs) of the nut's faces
    for o in objs:
        if o.type != 'MESH' or not o.data.uv_layers.active or o.get('aerofly_part') or o.get('aerofly_hinge'):
            continue
        names = [m.name if m else '' for m in o.data.materials] or [o.get('edm_material', '')]
        mw, uvs = o.matrix_world, o.data.uv_layers.active.data
        for p in o.data.polygons:
            if (names[min(p.material_index, len(names) - 1)] or o.get('edm_material', '')) != 'F22_SWITCH':
                continue
            V = [np.array(mw @ o.data.vertices[i].co) for i in p.vertices]
            ok = True
            for v in V:
                d = v - piv_af; h = v @ n - base_af
                if (d @ fwd) ** 2 + (d @ lat) ** 2 > R * R or not 0.0003 <= h <= H_TOP:
                    ok = False
                    break
            if ok:
                src.append((V, [tuple(uvs[li].uv) for li in p.loop_indices]))
    if not src:
        print('WARNING FLCS base: no ALT FLAPS nut faces')
        return []
    P = np.array([v for V, _ in src for v in V])
    F, L, Hh = (P - piv_af) @ fwd, (P - piv_af) @ lat, P @ n - base_af
    cf, cl = (F.min() + F.max()) / 2, (L.min() + L.max()) / 2
    r_max = np.sqrt((F - cf) ** 2 + (L - cl) ** 2).max()
    s_r, h0 = 0.0043 / r_max, Hh.min()
    s_h = (0.0049 - 0.0016) / (Hh.max() - h0)
    foot = np.array(FLCS_FRAME_ORIGIN) + fwd * 0.0023 + lat * 0.0001
    foot = foot - n * (foot @ n - base)
    verts, faces, fuv = [], [], []
    for V, uv in src:
        idx = []
        for v in V:
            d = v - piv_af
            w = foot + fwd * ((d @ fwd - cf) * s_r) + lat * ((d @ lat - cl) * s_r) + n * (0.0016 + (v @ n - base_af - h0) * s_h)
            idx.append(len(verts)); verts.append(tuple(w))
        faces.append(tuple(idx)); fuv.append(uv)
    print('FLCS base: ALT FLAPS nut, %d faces, r %.1f mm h %.1f-%.1f mm -> scale %.2f / %.2f at %s'
          % (len(faces), r_max * 1e3, h0 * 1e3, Hh.max() * 1e3, s_r, s_h, np.round(foot, 5).tolist()))
    out = [mesh_object('FlcsBushing', verts, faces, fuv, 'f22_switch')]
    for name, _, R, t in CC.GUARDS:          # the same base under the other guarded toggles (the switch's mesh, moved)
        Rm, tv = np.array(R), np.array(t)
        out.append(mesh_object(name + 'Bushing', [tuple(Rm @ np.array(v) + tv) for v in verts], faces, fuv, 'f22_switch'))
    return out


def _nozzle_fire(objs, mesh_object):
    import nozzle_fire_f22
    return nozzle_fire_f22.objects(objs, mesh_object, TURBINE_AXES)


def _formation_panels(objs, mesh_object, X, tex_dir):
    """Formation light panels: the painted strip texels mapped onto the skin through its UVs -> oriented rectangle in
    3D (the UV islands are sheared: a rectangle in texture space came out tilted) -> laid on the skin, lifted."""
    import numpy as np
    img = X.load_image(X.find_texture(tex_dir, 'f-22a_default'))[..., :3]      # rows bottom-up = Blender UV v
    h, w = img.shape[:2]
    tris, uvs = [], []
    for o in objs:
        if o.get('edm_material', '') != 'F22A_FUSE' or o.get('edm_anim_args', ''):
            continue
        me = o.data
        me.calc_loop_triangles()
        uvl = me.uv_layers.active
        if uvl is None:
            continue
        M = np.array(o.matrix_world)
        co = np.array([v.co[:] for v in me.vertices]) @ M[:3, :3].T + M[:3, 3]
        for t in me.loop_triangles:
            tris.append(co[list(t.vertices)])
            uvs.append([uvl.data[i].uv[:] for i in t.loops])
    tris, uvs = np.array(tris), np.array(uvs)
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12

    def outward_score(pts, outward):
        if outward is None:          # nose: outward from the centreline on the triangle's own side
            hint = np.c_[np.zeros(len(pts)), np.sign(pts[:, 1]) * 0.82, np.full(len(pts), -0.57)]
        else:
            hint = np.broadcast_to(np.array(outward, float), pts.shape)
        return (nrm[sel] * hint).sum(1)

    out = []
    for i, (box, near, outward) in enumerate(FORMATION_STRIPS):
        near = np.array(near)
        (x0, y0), m = _strip_mask(img, box)
        ys, xs = np.nonzero(m)
        tex_uv = np.c_[(xs + x0 + 0.5) / w, (ys + y0 + 0.5) / h]
        # skin triangles of this strip: UV overlapping the box, near the strip, facing outward
        u0, u1, v0, v1 = box
        sel = np.nonzero((uvs[..., 0].max(1) >= u0) & (uvs[..., 0].min(1) <= u1) &
                         (uvs[..., 1].max(1) >= v0) & (uvs[..., 1].min(1) <= v1) &
                         (np.linalg.norm(tris.mean(1) - near, axis=1) < 1.2))[0]
        sel = sel[outward_score(tris[sel].mean(1), outward) > 0.3]
        T, U = tris[sel], uvs[sel]
        a, b_, c_ = U[:, 0], U[:, 1], U[:, 2]
        e0, e1 = b_ - a, c_ - a
        den = e0[:, 0] * e1[:, 1] - e0[:, 1] * e1[:, 0]
        pts = []
        for q in tex_uv:
            d = q - a
            bv = (d[:, 0] * e1[:, 1] - d[:, 1] * e1[:, 0]) / den
            bw = (e0[:, 0] * d[:, 1] - e0[:, 1] * d[:, 0]) / den
            k = np.nonzero((bv >= -1e-4) & (bw >= -1e-4) & (bv + bw <= 1 + 1e-4))[0]
            if len(k):
                k = k[0]
                pts.append(T[k, 0] + bv[k] * (T[k, 1] - T[k, 0]) + bw[k] * (T[k, 2] - T[k, 0]))
        pts = np.array(pts)
        if len(pts) < 20:
            raise SystemExit('formation strip %d: only %d texels found on the skin' % (i, len(pts)))
        ctr = pts.mean(0)
        n = nrm[sel][np.argmin(np.linalg.norm(T.mean(1) - ctr, axis=1))]
        q = pts - ctr
        q -= np.outer(q @ n, n)                       # into the tangent plane
        evals, evecs = np.linalg.eigh(np.cov(q.T))
        ax_l, ax_w = evecs[:, 2], evecs[:, 1]         # long axis, across (evecs[:, 0] ~ normal)
        sl, sw = q @ ax_l, q @ ax_w
        l0, l1 = sl.min() - PANEL_MARGIN, sl.max() + PANEL_MARGIN
        w0, w1 = sw.min() - PANEL_MARGIN, sw.max() + PANEL_MARGIN
        # lay every grid point on the skin: ray along -n against the strip's triangles
        verts = []
        for k in range(PANEL_SEGMENTS + 1):
            for t_ in (w0, w1):
                p0 = ctr + (l0 + (l1 - l0) * k / PANEL_SEGMENTS) * ax_l + t_ * ax_w + 0.05 * n
                e1_, e2_ = T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
                pv = np.cross(-n, e2_)
                det = (e1_ * pv).sum(1)
                tv = p0 - T[:, 0]
                with np.errstate(divide='ignore', invalid='ignore'):
                    uu = (tv * pv).sum(1) / det
                    qv = np.cross(tv, e1_)
                    vv = (qv @ -n) / det
                    tt = (qv * e2_).sum(1) / det
                ok = (uu >= -1e-3) & (vv >= -1e-3) & (uu + vv <= 1 + 1e-3) & (tt > 0) & (tt < 0.15)
                dist = tt[ok].min() if ok.any() else 0.05     # off the strip's triangles: stay on the plane
                verts.append(p0 - (dist - PANEL_LIFT) * n)
        faces, fuv = [], []
        for k in range(PANEL_SEGMENTS):
            f = [2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2]
            if np.cross(verts[f[1]] - verts[f[0]], verts[f[3]] - verts[f[0]]) @ n < 0:
                f = f[::-1]
            faces.append(f)
            fuv.append([((j // 2) / PANEL_SEGMENTS, float(j % 2)) for j in f])
        out.append(mesh_object('FORMATION_PANEL_%d' % i, [tuple(v) for v in verts], faces, fuv, 'lamp_formation'))
        print('formation panel %d: %.3f x %.3f m from %d texels' % (i, l1 - l0, w1 - w0, len(pts)))
    return out


def _icp_patch(objs, mesh_object):
    """ICP plate: the labelled UV grid (2026-10-30) shows no plate at all in the game over part of its upper right (the wheel
    behind it shows, and the hood), while the .tgi has these faces whole and front facing: not reproduced offline, and a part of its
    own did not help (2026-10-23). The cause is not known. A second skin of the same faces, each split in four, 0.2 mm nearer the
    pilot, is drawn (first over that corner only: smaller gaps remained beyond it): now the whole plate."""
    import numpy as np
    verts, faces, fuv = [], [], []
    for o in objs:
        if o.type != 'MESH' or not o.data.uv_layers.active:
            continue
        names = [m.name if m else '' for m in o.data.materials] or [o.get('edm_material', '')]
        mw, uvs = o.matrix_world, o.data.uv_layers.active.data
        for p in o.data.polygons:
            if (names[min(p.material_index, len(names) - 1)] or o.get('edm_material', '')) != 'F22_UFC':
                continue
            co = [np.array(mw @ o.data.vertices[i].co) for i in p.vertices]
            c = sum(co) / len(co)
            if not (7.62 < c[0] < 7.66 and abs(c[1]) < 0.11 and 1.0 < c[2] < 1.18):
                continue
            uv = [np.array(uvs[li].uv) for li in p.loop_indices]
            for k in range(1, len(co) - 1):
                a, b, d = co[0], co[k], co[k + 1]
                n = np.cross(b - a, d - a)
                if np.linalg.norm(n) < 1e-9 or n[0] > -0.8 * np.linalg.norm(n):
                    continue
                n = n / np.linalg.norm(n)
                ua, ub, ud = uv[0], uv[k], uv[k + 1]
                mid = lambda s, t: (s + t) / 2
                for tri, tuv in (((a, mid(a, b), mid(a, d)), (ua, mid(ua, ub), mid(ua, ud))),
                                 ((mid(a, b), b, mid(b, d)), (mid(ua, ub), ub, mid(ub, ud))),
                                 ((mid(a, d), mid(b, d), d), (mid(ua, ud), mid(ub, ud), ud)),
                                 ((mid(a, b), mid(b, d), mid(a, d)), (mid(ua, ub), mid(ub, ud), mid(ua, ud)))):
                    base = len(verts)
                    verts += [tuple(q + 0.0002 * n) for q in tri]
                    faces.append((base, base + 1, base + 2))
                    fuv.append([tuple(t) for t in tuv])
    print('ICP patch: %d triangles' % len(faces))
    return [mesh_object('ICPPatch', verts, faces, fuv, 'f22_ufc')] if faces else []


def BURNER_TEXTURE(name):
    import nozzle_fire_f22
    return nozzle_fire_f22.texture(name)


def BURNER_COLD(name):
    import nozzle_fire_f22
    return nozzle_fire_f22.cold(name)


# 3x5 digits for the diagnostic UV grid
_GRID_FONT = {'0': '111101101101111', '1': '010110010010111', '2': '111001111100111', '3': '111001111001111', '4': '101101111001001',
              '5': '111100111001111', '6': '111100111101111', '7': '111001010010010', '8': '111101111101111', '9': '111101111001111',
              'A': '111101111101101', 'B': '110101110101110', 'C': '111100100100111', 'D': '110101101101110', 'E': '111100111100111',
              'F': '111100111100100', '-': '000000111000000'}


def _uv_grid(X, out_dir, name):
    """Each cell labelled <column>-<row> in hex: column = u * cells, row = v * cells, cell 00-00 at u 0 v 0."""
    import numpy as np
    n, cells = 2048, UV_GRID_CELLS
    size = n // cells
    img = np.zeros((n, n, 3), np.float32)
    for row in range(cells):
        for col in range(cells):
            shade = (0.75, 0.75, 0.2) if (row + col) % 2 else (0.2, 0.55, 0.75)
            y0, x0 = n - (row + 1) * size, col * size
            img[y0:y0 + size, x0:x0 + size] = shade
            text = '%02X-%02X' % (col, row)
            cx = x0 + (size - len(text) * 12) // 2
            for j, ch in enumerate(text):
                for i, bit in enumerate(_GRID_FONT[ch]):
                    if bit == '1':
                        py, px = y0 + 24 + 3 * (i // 3), cx + j * 12 + 3 * (i % 3)
                        img[py:py + 3, px:px + 3] = 0.0
    X.save_png(os.path.join(out_dir, name + '_color.png'), img[::-1])      # save_png writes array row 0 at the bottom


# ---- stores (stage 6, stores_f22.py, REFERENCES.md): AIM-120C x6 in the main bay, AIM-9X on the side-bay trapezes,
# the 600 gal ferry tanks with their pylons and collision hulls. Wear and paint tone from the mod's own skin.
STORE_MAPS = {}


def _orient_outward(bm):
    """Reverse every connected piece of a bmesh whose faces point into it (signed volume about its centroid < 0)."""
    import bmesh
    bm.faces.index_update()
    seen = set()
    for f in bm.faces:
        if f.index in seen:
            continue
        piece, stack = [], [f]
        seen.add(f.index)
        while stack:
            g = stack.pop()
            piece.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        pts = [l.vert.co for g in piece for l in g.loops]
        c = sum(pts, pts[0] * 0) / len(pts)
        vol = 0.0
        for g in piece:
            p = [l.vert.co - c for l in g.loops]
            vol += sum(p[0].dot(p[i].cross(p[i + 1])) for i in range(1, len(p) - 1))
        if vol < 0:
            bmesh.ops.reverse_faces(bm, faces=piece, flip_multires=False)


def _spread_flat_uvs(bm, layer, span=0.02):
    """Faces whose UVs have no area (a fin or lug on one swatch point, a pylon end cap or bottom on a line of its
    side projection) leave the game no texture direction for the bump map: they drew black or not at all. Give each
    a small planar projection (span in UV) around its UVs' centre - the same swatch colour, now with an area."""
    bm.normal_update()
    for f in bm.faces:
        uv = [l[layer].uv.copy() for l in f.loops]
        area = sum(uv[i].x * uv[i - 1].y - uv[i - 1].x * uv[i].y for i in range(len(uv))) / 2
        if abs(area) > 1e-9:
            continue
        n = f.normal
        a = n.orthogonal().normalized()
        b = n.cross(a)
        c = f.calc_center_median()
        pa = [(l.vert.co - c).dot(a) for l in f.loops]
        pb = [(l.vert.co - c).dot(b) for l in f.loops]
        k = span / max(max(pa) - min(pa), max(pb) - min(pb), 1e-6)
        mu = sum((t for t in uv), uv[0] * 0) / len(uv)
        mu.x = min(max(mu.x, span), 1.0 - span)                    # the projection stays inside the texture
        mu.y = min(max(mu.y, span), 1.0 - span)
        for l, x, y in zip(f.loops, pa, pb):
            l[layer].uv = (mu.x + k * x, mu.y + k * y)


def _store_objects(X, tex_dir):
    import bpy
    import bmesh
    import numpy as np
    import stores_f22 as S
    skin = X.load_image(X.find_texture(tex_dir, 'F-22A_Default'))[::-1, :, :3]       # rows top-down
    S.set_skin(skin)
    objs = []

    def make(name, verts, faces, uvs, smooth, material, part, nodes='', args=''):
        bm = bmesh.new()
        vs = [bm.verts.new(v) for v in verts]
        layer = bm.loops.layers.uv.new('UV')
        for f, fu, sm in zip(faces, uvs, smooth):
            try:
                face = bm.faces.new([vs[i] for i in f])
            except ValueError:                       # degenerate (repeated vertex) - skip
                continue
            face.smooth = sm
            for lp, uv in zip(face.loops, fu):
                lp[layer].uv = uv
        # stores_f22 winds its faces clockwise seen from outside; Aerofly draws front faces only (Blender both, so the
        # previews looked right). Weld coincident vertices (a fin's sharp leading edge) so every piece is closed, make
        # the winding agree across every edge (one side of each fin and the pylon's end caps ran the other way), then
        # turn each piece outward by its signed volume about its own centre (the loop UVs go with the faces)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        _orient_outward(bm)
        _spread_flat_uvs(bm, layer)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name, me)
        o['aerofly_material'] = material
        o['aerofly_part'] = part
        o['edm_anim_nodes'] = nodes
        o['edm_anim_args'] = args
        return o

    for d in S.aircraft_stores():
        STORE_MAPS[d['material']] = d['maps']
        objs.append(make(d['name'], d['verts'], d['faces'], d['uvs'], d['smooth'], 'store:' + d['material'], d['part'],
                         d['nodes'], d['args']))
        # the ferry tanks twice (breakage_f22.tank_addon): 'Stores_TankK<side>' drawn on the fuselage while the tank
        # holds - its sprung joint gives centimetres under load, a gap at the wing - 'Stores_Tank<side>' on its own
        # body once it is jettisoned. One geometry cannot be drawn by two graphics objects: two parts
        if d['part'].startswith('Stores_Tank'):
            objs.append(make(d['name'] + 'K', d['verts'], d['faces'], d['uvs'], d['smooth'], 'store:' + d['material'],
                             'Stores_TankK' + d['part'][-1], d['nodes'], d['args']))
    for side, y in (('L', S.CONN['Pylon2'][1]), ('R', S.CONN['Pylon10'][1])):
        v, f = S.tank_hull(y)
        objs.append(make('ColStoreTank' + side, v, f, [tuple((0.5, 0.5) for _ in q) for q in f], [False] * len(f),
                         'store:store_tank', 'ColStoreTank' + side))
    print('stores: %d objects (%s)' % (len(objs), ', '.join(sorted({o['aerofly_part'] for o in objs}))))
    return objs


# selection previews of the load repaints (render_preview2.py): the stores seen from above-front-left; the missiles of
# "combat" sit in the shut bays, so its preview is the plain aircraft
PREVIEW_PARTS = {'ferry': ('Stores_TankL', 'Stores_TankR')}


def PREVIEW_OBJECTS(repaint):
    """Mesh objects of the repaint's stores for the preview, textured by the exported store_<material>_color.png."""
    import json
    import bpy
    import stores_f22 as S
    out = []
    for d in S.aircraft_stores():
        if d['part'] not in PREVIEW_PARTS.get(repaint, ()):
            continue
        me = bpy.data.meshes.new(d['name'])
        keep = [k for k, f in enumerate(d['faces']) if len(set(f)) == len(f)]      # no degenerate faces
        me.from_pydata([tuple(v) for v in d['verts']], [], [d['faces'][k] for k in keep])
        uv = me.uv_layers.new(name='UV')
        for poly, k in zip(me.polygons, keep):
            for li, t in zip(poly.loop_indices, d['uvs'][k]):
                uv.data[li].uv = t
            poly.use_smooth = bool(d['smooth'][k])
        o = bpy.data.objects.new(d['name'], me)
        o['edm_textures'] = json.dumps({'0': d['material']})
        bpy.context.scene.collection.objects.link(o)
        out.append(o)
    return out


def STORE_TEXTURES(out_dir, name, X):
    """Maps of a store material (stores_f22 Maps): colour, height, gloss, metal -> the Aerofly channel set (through
    the skin writer, so the colour gets the skin's scale); our height map is the bump."""
    import os
    import numpy as np
    m = STORE_MAPS[name]
    rgba = np.concatenate([m['colour'], np.ones(m['colour'].shape[:2] + (1,), np.float32)], axis=2)
    roughmet = np.stack([np.ones_like(m['gloss']), 1.0 - m['gloss'], m['metal']], axis=2)
    X.write_material_textures(out_dir, name, rgba, None, roughmet, size=m['colour'].shape[0])
    X.save_png(os.path.join(out_dir, name + '_bump.png'), m['height'], limit=m['height'].shape[0])

# ---- live displays and HUD from the stock F/A-18 (make_f22.py copies its display objects; they draw into the render
# targets display_light / hud_light). Screens laid on the DCS indicator connectors (Cockpit device_init.lua: centre,
# bottom-edge middle, right-edge middle); region = the F/A-18 display's place in the 2048 atlas (its TargetPosition /
# TargetSize x 2, from the bottom-left), brightness = the F/A-18 graphics_input_color of that display.
DISPLAY_TEXTURE = 'display'
DISPLAYS = {
    'DisplayLeftMFD': dict(quad=('LEFT-MFD-CENTER', 'LEFT-MFD-DOWN', 'LEFT-MFD-RIGHT'), region=(36, 1228, 780, 780),
                           donor='DDILeft', brightness='DDILeftBrightness'),
    'DisplayRightMFD': dict(quad=('RIGHT-MFD-CENTER', 'RIGHT-MFD-DOWN', 'RIGHT-MFD-RIGHT'),
                            region=(840, 1228, 780, 780), donor='DDIRight', brightness='DDIRightBrightness'),
    # MPCD: its menu row reaches above the 864 px square (cut at the top in the first test)
    # (user 2026-11-06: not filling its screen) the DCS quad is 182 mm square, the glass (F22_SCREEN faces in the pose,
    # flat in the connectors' plane) 196 x 192 mm: the picture spans the glass, 2 % wider than tall
    # (user 2026-11-07: filling the glass, the menu labels stood off their keys - the F/A-18 menu draws them at fixed
    # places in the image) warped. The MPCD draws 864 px square (graphics_animation_display MPCD: TargetPosition 365 100,
    # TargetSize 432 x 2) inside the 884 px region: the picture ends at t_x = +-0.977, t_y = -1 .. +0.955 (the gaps the
    # user saw: "empty margins, make it full screen") - those edges go to the glass opening (bezel inner edge = quad,
    # +-97.5 x +-95.5 mm, scratchpad pmfd_hole2.py). Labels in the image (pmfd_fit.py, a homography on the 20 keys of the
    # user's screenshot): top / bottom slots t_x = -0.654 + 0.315 k, side slots t_y = 0.537 - 0.327 k; keys (connectors
    # PMFD_n_PNT) u = -0.0574 + 0.0287 k, v = 0.0502 - 0.0287 k. Uniform over the glass the outer labels miss by up to
    # 8 mm, exactly on the keys the picture's middle shrinks 6.5 / 8 % (the user: "why smaller?"). The user's choice, half
    # way: the outer label slots set 2.7 / 2.5 mm off their keys (the inner ones closer), linear between them, the strips
    # beyond them stretched to the glass edges (x 1.21 / 1.05, y 1.12 / 1.35 of the middle's scale).
    'DisplayPMFD': dict(quad=('PMFD-CENTER', 'PMFD-DOWN', 'PMFD-RIGHT'), region=(720, 200, 884, 884),
                        donor='MPCD', brightness='MPCDBrightness', half=(0.0975, 0.0955),
                        warp=(((-0.977, -0.0975), (-0.654, -0.0601), (0.606, 0.0602), (0.977, 0.0975)),
                              ((-1.0, -0.0955), (-0.771, -0.0672), (0.537, 0.0527), (0.955, 0.0955)))),
}
# The F-22's other screens draw into a second render target (display2_light, the first one is full): the lower SMFD
# (a fourth F/A-18 DDI, cloned from the right one), the two up-front displays (UFD, built in make_f22.py) and the
# ICP (the F/A-18 up-front controller text: five option lines and the scratchpad). The ICP glass is six 59 x 11 mm
# windows (cockpit F22_SCREEN faces in the merged pose, x 7.6298 facing aft): five option windows beside the option
# buttons, the scratchpad left of the first one - one quad each, the bezel between them stays visible.
DISPLAY_TEXTURES = {'display': 'DisplayTexture', 'display2': 'DisplayTexture2'}
ICP_X, ICP_HW, ICP_HH = 7.6298, 0.0294, 0.00565
ICP_ROWS = [1.14775, 1.1301, 1.1125, 1.0949, 1.07725]          # option windows, top to bottom (z)
DISPLAYS.update({
    'DisplayLowerMFD': dict(quad=('MFD-CENTER', 'MFD-DOWN', 'MFD-RIGHT'), region=(36, 1228, 780, 780),
                            texture='display2', donor='DDILower', brightness='DDILowerBrightness'),
    'DisplayLeftUFD': dict(quad=('LEFT-PFD-CENTER', 'LEFT-PFD-DOWN', 'LEFT-PFD-RIGHT'), region=(860, 1260, 740, 570),
                           texture='display2', donor='UFDLeft', brightness='UFDLeftBrightness'),
    'DisplayRightUFD': dict(quad=('RIGHT-PFD-CENTER', 'RIGHT-PFD-DOWN', 'RIGHT-PFD-RIGHT'),
                            region=(860, 640, 740, 570), texture='display2', donor='UFDRight', brightness='UFDRightBrightness'),
    'DisplayICPScratch': dict(rect=([ICP_X, 0.0477, ICP_ROWS[0]], [0.0, -ICP_HW, 0.0], [0.0, 0.0, ICP_HH]),
                              region=(30, 584, 460, 86), texture='display2', donor='ICPScratch',
                              brightness='ICPBrightness'),
})
for i_, z_ in enumerate(ICP_ROWS):
    DISPLAYS['DisplayICP%d' % (i_ + 1)] = dict(rect=([ICP_X, -0.0335, z_], [0.0, -ICP_HW, 0.0], [0.0, 0.0, ICP_HH]),
                                               region=(40, 488 - 112 * i_, 430, 80), texture='display2',
                                               donor='ICPLines', brightness='ICPBrightness')
# worn screen glass (user 2026-11-17, after the stock F/A-18's DDIs): fingerprints by the keys, dust at the bezel, wipe
# marks, a few scratches - in each screen's own colour map, no reflection (tools/aerofly_tex.py screen_wear_map, our
# own procedural map; a separate glass with the instrument shader reflected the spawn point's scenery). Value: how the
# one map is turned on that screen (1 mirror u, 2 mirror v, 4 swap) so the screens differ
DISPLAY_WEAR = {'DisplayLeftMFD': 0, 'DisplayRightMFD': 3, 'DisplayPMFD': 5, 'DisplayLowerMFD': 6,
                'DisplayLeftUFD': 1, 'DisplayRightUFD': 2}
# display caps: from outside the live screens show nothing useful (and the second render target showed garbage), so a
# still picture of each screen's start page lies 2 mm in front of it, drawn outside the pilot's own view only
# (make_f22.py ShowInside) and lit by the screen's brightness - dark without power. Pages: mfd_pages.py
DISPLAY_CAPS = {'DisplayLeftMFD': 'eng', 'DisplayRightMFD': 'fuel', 'DisplayPMFD': 'sa', 'DisplayLowerMFD': 'fcs',
                'DisplayLeftUFD': 'ufd_left', 'DisplayRightUFD': 'ufd_right', 'DisplayICPScratch': 'icp_scratch'}
DISPLAY_CAPS.update({'DisplayICP%d' % (i_ + 1): 'icp%d' % (i_ + 1) for i_ in range(len(ICP_ROWS))})


def CAP_TEXTURES(out_dir, name, X):
    """Display cap cap_<page>: dark screen glass (DISPLAY_SURFACE) with the page as its light map (the screen's
    luminance), square at a power of two (the cap's UVs span the page, any aspect)."""
    import os, subprocess
    import bpy
    import numpy as np
    here = os.path.dirname(os.path.abspath(__file__))
    pages = os.path.join(here, 'work', 'mfd_pages')
    src = os.path.join(pages, name + '.png')
    script = os.path.join(here, 'mfd_pages.py')
    if not os.path.exists(src) or os.path.getmtime(src) < os.path.getmtime(script):
        subprocess.run([bpy.app.binary_path, '--background', '--factory-startup', '--python', script, '--', pages],
                       check=True, stdout=subprocess.DEVNULL)
    img = X.load_image(src)[..., :3].astype(np.float32)
    n = 1024 if max(img.shape[:2]) > 600 else 512
    yi = (np.arange(n) + 0.5) * img.shape[0] / n
    xi = (np.arange(n) + 0.5) * img.shape[1] / n
    y0, x0 = np.clip(yi.astype(int), 0, img.shape[0] - 1), np.clip(xi.astype(int), 0, img.shape[1] - 1)
    y1, x1 = np.clip(y0 + 1, 0, img.shape[0] - 1), np.clip(x0 + 1, 0, img.shape[1] - 1)
    fy, fx = (yi - y0)[:, None, None], (xi - x0)[None, :, None]
    sq = (img[y0][:, x0] * (1 - fx) + img[y0][:, x1] * fx) * (1 - fy) + (img[y1][:, x0] * (1 - fx) + img[y1][:, x1] * fx) * fy
    base = os.path.join(out_dir, name)
    surf = DISPLAY_SURFACE
    X.save_png(base + '_color.png', np.full((64, 64, 3), 0.015, np.float32))
    X.save_png(base + '_light.png', sq, limit=n)
    X.save_png(base + '_bump.png', np.full((64, 64), 0.5, np.float32))
    X.save_png(base + '_specular.png', np.full((64, 64, 3), surf['specular'], np.float32),
               np.full((64, 64), surf['gloss'], np.float32))
    X.save_png(base + '_reflection.png', np.full((64, 64, 3), surf['reflection'], np.float32))
    X.save_png(base + '_ambient.png', np.ones((64, 64), np.float32))


# head-up display: the F/A-18 symbology (collimated, F/A-18 scale) on the combiner plate of the cockpit's HUD glass
HUD_GLASS = 'CP_HUD_GLASS'
HUD_DONOR = dict(texture='HUDTexture', centre='HUDCenter', hud='HUDDisplay')
HUD_SCALE = 0.70         # F/A-18 symbology at 70 % (0.55 left much empty glass, 0.75 cut the top) - not conformal
HUD_LAYERS = 2           # the HUD drawn twice (export_parts.hud_projection): at full brightness it looked half as
                         # bright as the F/A-18's by day, and the renderer clamps the brightness at 1
# display glass: little sky reflection (the green screens showed bright diagonal bands)
DISPLAY_SURFACE = dict(specular=0.06, gloss=0.6, reflection=0.01)
# cockpit model normals bent more than this (deg) off their triangle are flattened (MFD button caps: dark crosses)
# (flattening normals bent > 30 deg off their triangle, tried for the MFD button crosses, shattered the knob tops into
# facets and darkened sliver triangles: off. The dissolved MFD faces get sharp edges above 30 deg instead.)
COCKPIT_NORMAL_CREASE = None
# coplanar faces merged before export (MFD button caps / bezels: triangle fans drew dark crosses)
COCKPIT_DISSOLVE = re.compile(r'^F22_MFD$')

# ---- cockpit clicks (make_f22.py moves the stock F/A-18 click volumes onto the F-22 cockpit)
# MFD bezel buttons: F/A-18 control name prefix -> DCS button connectors <points>1..20_PNT of that screen
CLICK_MFDS = [
    dict(f18='LeftMFDButton', points='L_MFD_', quad=('LEFT-MFD-CENTER', 'LEFT-MFD-DOWN', 'LEFT-MFD-RIGHT')),
    dict(f18='RightMFDButton', points='R_MFD_', quad=('RIGHT-MFD-CENTER', 'RIGHT-MFD-DOWN', 'RIGHT-MFD-RIGHT')),
    dict(f18='MPCDButton', points='PMFD_', quad=('PMFD-CENTER', 'PMFD-DOWN', 'PMFD-RIGHT')),
    # lower SMFD: the right DDI's buttons with its messages renamed (make_f22.py clones the right DDI as LowerMFD)
    dict(f18='RightMFDButton', points='B_MFD_', quad=('MFD-CENTER', 'MFD-DOWN', 'MFD-RIGHT'), rename=('RightMFD', 'LowerMFD')),
]
# ICP keys (push into the panel, +x): (DCS connector or [x, y, z], F/A-18 UFC template, message, value, qualifier).
# The function keys open UFC pages (make_f22.py: ICP.* messages); MRK = ENT (enter the scratchpad), UNDO = ON/OFF of
# the selected function (the F-22 ICP has neither key, the Hornet UFC needs both). IFF has no DCS connector: between
# STPT and ALT on the top row.
ICP_KEY = 'MenuKeyAP'
CLICK_ICP = [
    ('ICP_COM1_PNT', ICP_KEY, 'Communication.COM1ChannelEdit', 1.0, 'event'),
    ('ICP_COM2_PNT', ICP_KEY, 'Communication.COM2ChannelEdit', 1.0, 'event'),
    ('ICP_NAV_PNT', ICP_KEY, 'ICP.Nav', 1.0, 'event'),
    ('ICP_STPT_PNT', ICP_KEY, 'ICP.Steerpoint', 1.0, 'event'),
    ([7.6277, -0.0089, 1.1657], ICP_KEY, 'UpFront.Page', 2.0, 'event'),
    ('ICP_ALT_PNT', ICP_KEY, 'ICP.Altitude', 1.0, 'event'),
    ('ICP_HUD_PNT', ICP_KEY, 'ICP.HUD', 1.0, 'event'),
    ('ICP_OTHR_PNT', ICP_KEY, 'ICP.Other', 1.0, 'event'),
    ('ICP_AP_PNT', ICP_KEY, 'UpFront.Page', 1.0, 'event'),
    ('ICP_MRK_PNT', 'MenuKeyEnter', 'UpFront.Enter', 1.0, 'event'),
    ('ICP_UNDO_PNT', 'MenuKeyONOFF', 'UpFront.OnOff', 1.0, 'toggle'),
    ('ICP_CLR_PNT', 'MenuKeyClear', 'UpFront.Key', 8.0, 'value'),
] + [('ICP_%d_PNT' % k, 'MenuKeyOne', 'UpFront.Key', 48.0 + k, 'value') for k in range(10)] + \
    [('ICP_OP%d_PNT' % (k + 1), 'OptionSelectButton%d' % k, 'OptionButtons.Button', float(k), 'event') for k in range(5)]
# brightness thumbwheel left of the ICP (UFD and ICP; DCS ICP_WHEELUP / ICP_WHEELDWN mark its ends): a knob as the
# F/A-18 MFD brightness knobs - scroll or drag, one step = one of 21 positions (first try: push boxes sending 0.05 of a
# position, nothing visible happened)
CLICK_ICP += [([7.6346, 0.0977, 1.122], 'LeftMFDBrightnessKnob', 'UFD.Brightness', 1.0, 'step', 0.010, 0.004)]
# thumbwheels right of the ICP (no DCS connectors; mirror of the left one, heights from a screenshot: the upper beside
# A/P - MRK, the lower beside the rocker): the upper = HUD brightness (our choice, as the F-16 ICP's HUD symbology
# wheel), the lower = voice volume
CLICK_ICP += [([7.6346, -0.0966, 1.1256], 'LeftMFDBrightnessKnob', 'HUD.Brightness', 1.0, 'step', 0.010, 0.004)]
# (the lower one was the voice volume - out 2026-11-07: the RADIO VOL panel's VOX knob is the only volume control)
# (sizes: Aerofly showed the hover zone ~1 cm beyond each of these volumes on every side - 9 mm rocker halves and a
# 20 mm wheel cylinder hovered 30-40 mm tall - so the volumes are about half the parts)
# rocker at the lower right of the ICP (DCS ICP_KNEXT / ICP_KPREV): map range of the SA / HSI pages, up = larger. Our
# choice - on the F-22 it most likely steps the steerpoints, which Aerofly's route sequences by itself
CLICK_ICP += [('ICP_KNEXT_PNT', ICP_KEY, 'ICP.MapRangeUp', 1.0, 'event', 0.005, 0.005),
              ('ICP_KPREV_PNT', ICP_KEY, 'ICP.MapRangeDown', 1.0, 'event', 0.005, 0.005)]
ICP_KEY_SIZE = 0.015     # key face (the F/A-18 UFC keys 17-18 mm)
# the ICP keys with a DCS click point (function keys, digits, CLR, UNDO, A/P, MRK, the five round option keys): parts
# of their own, pushed forward while held (PRESS_PARTS below). 'UpFront.Key' / 'UpFront.Page' / 'OptionButtons.Button'
# tell their keys apart by the value
PRESS_PARTS_ICP = [dict(part='P_' + p[:-4], point=p, message=m, value=(v if m in ('UpFront.Key', 'UpFront.Page', 'OptionButtons.Button') else None), axis='x')
                   for p, tpl, m, v, *_ in CLICK_ICP if isinstance(p, str) and (tpl.startswith('MenuKey') or tpl.startswith('OptionSelect'))
                and p not in ('ICP_KNEXT_PNT', 'ICP_KPREV_PNT')]
# the two upper thumbwheels beside the ICP turn with their value (2026-10-22: they stood still - static in the DCS
# model, merged into larger F22_ACC2 objects; arg 918 of the DCS clicks drives nothing). Faces in the box become a
# part of their own (tools/export_parts.py extract_knobs, pivot fitted to the wheel rim). The DCS wheel is a 270 deg
# arc only (-134 .. +134 deg from aft, the 90 deg facing into the panel left open): turned 4 rad over the range (first
# build) the open side came out - part of the wheel missing and a hole beside it (user). The wheel turns within one
# ridge pitch instead (7.7 deg, measured on the rim vertices): each of the 21 detents a quarter pitch on, so the
# ridges roll while the arc stays in place. (x from 7.631: three faces of the ICP housing, CP__4.001, sat in the box)
# OPEN (2026-10-23): a see-through band on the ICP plate beside the first option window, OTHR / DVR and A/P in the
# game (already in the first screenshots of 2026-10-22), while the export is whole there: geometry, winding, normals,
# UVs, maps (no alpha), one front-facing triangle per point, converter in = out (647 419), no 'stripping problem'.
# Ruled out in the game: shadows, the HUD glass / ICP display quads (hidden), the size of the Fuselage mesh (the plate
# drawn as a part of its own, STATIC_PARTS = {'P_ICP': r'^CP_edm_obj\.008$'}: no change), a converter weld (simulated).
# Next step planned: a labelled UV grid on f22_ufc (one conversion) to see what the game draws there. README.md.
# the fans at the end of the intake ducts, seen through the bend: blades and spinner in the big airframe object, their fixed ring stays
# (fitted 2026-11-01, centres from the spinner tips: disc r < 0.33, fixed ring from 0.34, x -0.134 .. 0.006)
FAN_PARTS = [dict(part='K_Fan' + side, material=r'^F22A_FUSE$', box=((-0.14, min(y - 0.34, y + 0.34), -0.26), (0.012, max(y - 0.34, y + 0.34), 0.43)),
                  radius=((y, z), 0.333), axis=(1.0, 0.0, 0.0), pivot=(-0.07, y, z), spin=True)
             for side, y, z in (('Left', 0.6441, 0.0824), ('Right', -0.6458, 0.0807))]
# the ball and rods behind the nozzle turn with the turbine wheel (user, 2026-11-01: fixed ones in front of a turning wheel looked wrong, though
# on the real engine such struts stand still). Centres from the ball's tip; all of the DCS object at this depth is ball and rods
TURBINE_AXES = {'Left': (0.6647, 0.2728), 'Right': (-0.6647, 0.274)}
TURBINE_HUBS = [dict(part='Turbine_' + side, material=r'^F22A_FUSE$', box=((-3.76, min(y - 0.43, y + 0.43), z - 0.43), (-3.395, max(y - 0.43, y + 0.43), z + 0.43)),
                     axis=(1.0, 0.0, 0.0), pivot=(-3.38, y, z), spin=True) for side, (y, z) in TURBINE_AXES.items()]
KNOB_PARTS = FAN_PARTS + TURBINE_HUBS + [dict(part='K_WheelUFD', material=r'^F22_ACC2$', box=((7.631, 0.090, 1.103), (7.664, 0.106, 1.152)),
                   axis=(0.0, 1.0, 0.0), source='UFDBrightnessWheel', pitch=7.7, phases=4, positions=21),
              dict(part='K_WheelHUD', material=r'^F22_ACC2$', box=((7.631, -0.106, 1.103), (7.664, -0.090, 1.152)),
                   axis=(0.0, 1.0, 0.0), source='HUDBrightnessKnob', pitch=7.7, phases=4, positions=21)]
# Static console controls made working parts (user 2026-11-04: "real logic in the physics and the behaviour, not
# empty switching"). In the DCS model they are all one F22_SWITCH object (CP__3.005, 13.5 k faces, no arguments): each
# control's faces are cut out by a box around it and the height their top vertex reaches above the panel (above: the
# nut and the red guards stay), and turned about a pivot fitted to the geometry (scratchpad fit2.py, 2026-11-04: the stem's lowest faces ->
# the ball's centre gives the bat; every toggle stands in its aft position in the model, the rotaries centred). Map:
# (value, degrees about the axis); toggles turn about the panel's lateral axis (+ = top forward) or, LAMP TEST, its
# fore-aft axis (+ = top to the right); rotaries about the panel normal (+ = anticlockwise from above).
def _switch(part, box, normal, base, above, pivot, axis, source, angles, island=None):
    d = dict(part=part, material=r'^F22_SWITCH$', box=box, above=(normal, base, above), pivot=pivot, axis=axis,
             source=source, angles=angles)
    if island is not None:
        d['island_top'] = island
    return d


# toggles: whole loose pieces of the bat (stem, ball: tops 17-27 mm above the panel) - the nut's dome pieces reach 9.7 mm
# (export_parts.island_filter; the first cut by each face's top vertex at 7 mm took some of them: black holes in the nut)
_BAT = 0.012


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


FLCS_FRAME_ORIGIN = (7.17904, 0.37914, 0.6113)


def _guard_part():
    """FLCS BIT guard: the red lid over the switch's forward positions (the toggle stands aft of it, at STOP) lifts about
    its hinge pins at the lid's forward end. Geometry (scratchpad guard.py, 2026-11-05), in the switch's frame (origin
    the bat's pivot, fwd = lateral x normal, h above the panel): frame walls |lat| 8.5-8.9 mm and the base plate h 1.7 mm
    stay, the slot rails |lat| 2-4 mm stay; the lid is |lat| <= 6.3 mm, fwd -4.4 .. +20 mm, up to h 6.1 mm, its rolled
    hinge end at fwd 18-20 mm; the frame's hinge pins at fwd 16 mm, h 3.8 mm."""
    k = next(x for x in SWITCH_PARTS if x['part'] == 'K_FlcsBit')
    n, base, _ = k['above']
    lat = _LAT_L
    fwd = (lat[1] * n[2] - lat[2] * n[1], lat[2] * n[0] - lat[0] * n[2], lat[0] * n[1] - lat[1] * n[0])
    piv = FLCS_FRAME_ORIGIN       # the frame's measures (guard.py) are from the bat's first pivot
    hp = _dot(piv, n) - base

    def local(v):
        d = (v[0] - piv[0], v[1] - piv[1], v[2] - piv[2])
        return _dot(d, fwd), _dot(d, lat), _dot(v, n) - base

    def lid(verts):
        L = [local(v) for v in verts]
        if not all(abs(l) <= 0.0063 and -0.0046 <= f <= 0.0202 for f, l, _ in L):
            return False
        if min(h for _, _, h in L) < 0.0014:
            return False
        rail = all(0.0019 <= abs(l) <= 0.0041 and -0.0006 <= f <= 0.0052 and h <= 0.0047 for f, l, h in L)
        return not rail
    hinge = tuple(round(piv[i] + fwd[i] * 0.0161 + n[i] * (0.0038 - hp), 5) for i in range(3))
    box = (tuple(piv[i] - 0.03 for i in range(3)), tuple(piv[i] + 0.03 for i in range(3)))
    return dict(part='K_FlcsGuard', material=r'^F22_SWITCH$', box=box, select=lid, pivot=hinge, axis=lat,
                source='F22FlcsGuard', angles=[(0.0, 0.0), (1.0, 105.0)])


_NL, _NR = (-0.0752, -0.1742, 0.9818), (-0.0760, 0.1855, 0.9797)        # left / right console normals
_LAT_L, _LAT_R = (0.0, 0.98460, 0.17480), (0.0, 0.98254, -0.18606)      # their lateral axes (n x forward)
SWITCH_PARTS = [
    # FLCS BIT: STOP (aft, as modelled) / OFF / START; the red guard is its own part (K_FlcsGuard). The bat turns about
    # its base between the slot's rails (user 2026-11-06: about a point 6 mm up the stem its foot swung, and under the
    # lifted guard it rose bare out of the panel - a bushing added, _flcs_bushing): bat axis measured on the geometry
    # (scratchpad bat_axis.py) 22.0 deg aft of the panel normal, its foot centred between the rails; pivot on the axis
    # at 3 mm (half the rails' height)
    _switch('K_FlcsBit', ((7.1703, 0.3738, 0.6049), (7.18386, 0.38246, 0.62509)), _NL, -0.01181, 0.0075,
            (7.18064, 0.37971, 0.60839), _LAT_L, 'F22FlcsBitSwitch', [(-1.0, 0.0), (0.0, 22.0), (1.0, 44.0)], _BAT),
    # ALT FLAPS: NORM (forward) / EXTEN (aft, as modelled, 36 deg)
    _switch('K_AltFlaps', ((7.21309, 0.33773, 0.60365), (7.23135, 0.3472, 0.6224)), _NL, -0.01517, 0.0072,
            (7.22815, 0.34333, 0.60628), _LAT_L, 'F22AltFlapsSwitch', [(0.0, 61.0), (1.0, 0.0)], _BAT),
    # CNI and AUX/ACP: OFF (aft, as modelled) / ON
    _switch('K_CNI', ((7.2411, -0.3099, 0.59787), (7.25404, -0.30104, 0.61826)), _NR, -0.0285, 0.0072,
            (7.25063, -0.30707, 0.60122), _LAT_R, 'F22CNISwitch', [(0.0, 0.0), (1.0, 39.4)], _BAT),
    _switch('K_ACP', ((7.24006, -0.34426, 0.60442), (7.253, -0.3354, 0.62482)), _NR, -0.01892, 0.0072,
            (7.24959, -0.34143, 0.60777), _LAT_R, 'F22ACPSwitch', [(0.0, 0.0), (1.0, 39.6)], _BAT),
    # LAMP TEST / (off, upright as modelled) / NVG: the labels stand forward and aft of it (user 2026-11-05: the first
    # turned it to the right); forward = the F/A-18 annunciator test, aft = NVG (annunciators dimmed for goggles)
    _switch('K_LampTest', ((7.31038, 0.43093, 0.62706), (7.31751, 0.43957, 0.64852)), _NL, -0.00767, 0.0072,
            (7.31464, 0.43674, 0.63105), _LAT_L, 'LightTestSwitch', [(-1.0, -22.0), (0.0, 0.0), (1.0, 22.0)], _BAT),
    # YAW TRIM (F22YawTrim -1 left .. +1 right, into the F/A-18 controller's rudder trim) and FADEC (L off / NORM / R off):
    # pointer knobs
    _switch('K_YawTrim', ((7.2265, 0.29754, 0.5946), (7.23932, 0.30946, 0.61808)), _NL, -0.01389, -1.0,
            (7.23315, 0.30305, 0.59949), _NL, 'F22YawTrim', [(-1.0, 40.0), (1.0, -40.0)]),
    _switch('K_Fadec', ((7.2819, 0.37463, 0.6127), (7.29487, 0.38655, 0.63605)), _NL, -0.00911, -1.0,
            (7.28866, 0.38012, 0.61755), _NL, 'F22FadecSelector', [(-1.0, 35.0), (0.0, 0.0), (1.0, -35.0)]),
    # RADIO VOL, VOX: the voice warnings' volume (F22VoiceVolume 0 .. 1, 20 clicks): OFF pointing left, loudest right, clockwise
    # over the top (user 2026-11-07). The pointer as modelled looks 45 deg below outboard (scratchpad vox_dir.py: its white
    # faces, 0 = outboard, 90 = forward), + = anticlockwise: angle = direction + 45. (Guessed tables before: 135 .. -135 put
    # OFF up, 45 .. -225 put the loudest up)
    _switch('K_VoxVolume', ((7.45989, -0.44449, 0.63606), (7.48303, -0.42009, 0.66069)), _NR, -0.04987, -1.0,
            (7.47019, -0.43153, 0.64998), _NR, 'F22VoiceVolume', [(0.0, 225.0), (1.0, 45.0)]),
]
SWITCH_PARTS.append(_guard_part())
KNOB_PARTS += SWITCH_PARTS
# the controls without a function yet (2026-11-16): parts, click zones and states of their own, cockpit_controls.py
import cockpit_controls as CC
KNOB_PARTS += CC.KNOBS


def _up(p, n, d):
    return [round(a + b * d, 5) for a, b in zip(p, n)]


# their click volumes: (F/A-18 template, point, cylinder axis, drag / turn direction for a rising value, message,
# (radius, length) or None). Toggles: a cylinder along the panel normal over the bat's swing; rotaries: the
# template's knob, turned about -normal (rising value clockwise); buttons: pushed into the panel
_FWD = (1.0, 0.0, 0.0)
CLICK_SWITCHES = [
    ('HUDRejectSelect', _up((7.17904, 0.37914, 0.6113), _NL, 0.010), _NL, _FWD, 'FCS.F22Bit', (0.007, 0.022)),
    ('APUMaster', _up((7.22815, 0.34333, 0.60628), _NL, 0.010), _NL, (-1.0, 0.0, 0.0), 'Controls.F22AltFlaps',
     (0.007, 0.022)),
    ('APUMaster', _up((7.25063, -0.30707, 0.60122), _NR, 0.010), _NR, _FWD, 'Avionics.F22CNI', (0.007, 0.022)),
    ('APUMaster', _up((7.24959, -0.34143, 0.60777), _NR, 0.010), _NR, _FWD, 'Avionics.F22ACP', (0.007, 0.022)),
    ('LightTest', _up((7.31464, 0.43674, 0.63105), _NL, 0.010), _NL, _FWD, None, (0.007, 0.022)),
    ('RudderTrimKnob', _up((7.23315, 0.30305, 0.59949), _NL, 0.012), tuple(-x for x in _NL), None, 'Controls.F22YawTrim',
     None),
    ('WarningCautionLight', _up((7.28866, 0.38012, 0.61755), _NL, 0.012), tuple(-x for x in _NL), None,
     'Engines.F22Fadec', (0.010, 0.022)),
    ('CommICSVolumeKnob', _up((7.47019, -0.43153, 0.64998), _NR, 0.004), tuple(-x for x in _NR), None, 'Voice.Volume',
     (0.012, 0.022)),
    # ENGINES MOTOR (red button, 24 mm) and, beside the gear handle, DN LOCK OVERRIDE (panel plane normal to the pilot,
    # point from a ray cast on the RESET / DN LOCK OVERRIDE labels, 2026-11-04)
    ('TakeoffTrim', _up((7.2900, 0.3150, 0.6080), _NL, 0.009), tuple(-x for x in _NL), None, 'Engines.F22Motor',
     (0.012, 0.010)),
    ('TakeoffTrim', (7.6440, 0.3460, 0.6950), (0.92, 0.10, -0.38), None, 'Gear.F22DownLockOverride', (0.009, 0.010)),
]


CLICK_SWITCHES += CC.CLICKS
CLICK_ICP += CC.CLICK_KEYS


# up-front display buttons: the left of the three under the left UFD = master caution acknowledge (DCS L_SMFD_2-4 are
# the buttons under the screen; L_SMFD_1 is on the hood above it, by the map light)
CLICK_UFD = [('L_SMFD_2_PNT', 'MenuKeyAP', 'Warnings.MasterCautionPilot', 1.0, 'event'),
             # right UFD (2026-11-07): top = SFI / TIME page, lower left = ST/SP, lower right = RST; the middle = the
             # next page as well, its legend on the screen (2026-11-17)
             ('R_SMFD_1_PNT', 'MenuKeyAP', 'UFD.RightPage', 1.0, 'event'),
             ('R_SMFD_2_PNT', 'MenuKeyAP', 'UFD.RightKey1', 1.0, 'event'),
             ('R_SMFD_4_PNT', 'MenuKeyAP', 'UFD.RightKey3', 1.0, 'event'),
             # the UFD keys without a function yet (2026-11-16: every control prepared for later logic - clickable,
             # moving, with a message of its own that nothing hears so far; release/COCKPIT_CONTROLS.md): left UFD top,
             # lower middle and lower right; right UFD lower middle (since 2026-11-17 the next page, make_f22.py)
             ('L_SMFD_1_PNT', 'MenuKeyAP', 'UFD.LeftPage', 1.0, 'event'),
             ('L_SMFD_3_PNT', 'MenuKeyAP', 'UFD.LeftKey2', 1.0, 'event'),
             ('L_SMFD_4_PNT', 'MenuKeyAP', 'UFD.LeftKey3', 1.0, 'event'),
             ('R_SMFD_3_PNT', 'MenuKeyAP', 'UFD.RightKey2', 1.0, 'event')]
# Keys that are objects of their own in the DCS cockpit but stand still there (the mod gives them click points, no
# animation): the 20 bezel keys of each MFD, the 4 keys of each UFD, the ICP keys. Each becomes a part of its own
# (tools/export_parts.py press_parts: the cockpit object at the click point) and goes in while it is held
# (make_f22.py, as the stock F/A-18's UFC keys: 1.5 mm). (part, click point, message, value or None, direction: 'x' =
# forward into the ICP, or the three connectors of the screen the key belongs to - pushed along the screen's normal)
PRESS_DEPTH = 0.0015
# the lettering of the ICP keys: flat objects of their own just over the key faces - they go with their keys
# (export_parts.attach_legends; user 2026-11-17: the lettering stayed in the air while the key went in)
LEGEND_MATERIAL = r'^F22_SCREEN$'
_QUADS = {'L_MFD_': ('LEFT-MFD-CENTER', 'LEFT-MFD-DOWN', 'LEFT-MFD-RIGHT'), 'R_MFD_': ('RIGHT-MFD-CENTER', 'RIGHT-MFD-DOWN', 'RIGHT-MFD-RIGHT'),
          'PMFD_': ('PMFD-CENTER', 'PMFD-DOWN', 'PMFD-RIGHT'), 'B_MFD_': ('MFD-CENTER', 'MFD-DOWN', 'MFD-RIGHT'),
          'L_SMFD_': ('LEFT-PFD-CENTER', 'LEFT-PFD-DOWN', 'LEFT-PFD-RIGHT'), 'R_SMFD_': ('RIGHT-PFD-CENTER', 'RIGHT-PFD-DOWN', 'RIGHT-PFD-RIGHT')}
_MFD_MESSAGE = {'L_MFD_': 'LeftMFD.Select', 'R_MFD_': 'RightMFD.Select', 'PMFD_': 'MPCD.Select', 'B_MFD_': 'LowerMFD.Select'}


def _mfd_value(point):
    """F/A-18 bezel key number of DCS point 1..20 (make_f22.py make_controls: 15-19 top row left to right = points
    1-5, 10-14 right column top down = 6-10, 0-4 bottom row left to right = 15-11, 5-9 left column top down = 20-16)."""
    return 14 + point if point <= 5 else point + 4 if point <= 10 else 15 - point if point <= 15 else 25 - point


PRESS_PARTS = [dict(part='P_%s%d' % (pre, n), point='%s%d_PNT' % (pre, n), message=msg, value=float(_mfd_value(n)), axis=_QUADS[pre])
               for pre, msg in _MFD_MESSAGE.items() for n in range(1, 21)]
PRESS_PARTS += [dict(part='P_' + p[:-4], point=p, message=m, value=None, axis=_QUADS[p[:7]]) for p, _, m, _, _ in CLICK_UFD]
PRESS_PARTS += PRESS_PARTS_ICP
PRESS_PARTS += CC.PRESSES        # pieces of larger objects (cut: True), pushed along their own axis
# (F/A-18 control, DCS cockpit argument of the F-22 part it is put on, kind: toggle / knob / lever)
CLICK_PARTS = [
    ('BatteryOverride', 700, 'toggle'), ('APUMaster', 701, 'toggle', 'Engines.F22Apu'),
    ('Engine1Generator', 702, 'toggle'), ('Engine2Generator', 703, 'toggle'),
    # LDG / OFF / TAXI: the F/A-18 three-position HUD reject switch as the template (its landing light switch is a
    # two-way toggle volume), drag forward = LDG, aft = TAXI
    ('MasterArmSafe', 708, 'toggle'), ('HUDRejectSelect', 709, 'toggle', 'Controls.Lighting.Landing'),
    ('ParkingBrakeHandle', 710, 'toggle'),
    ('DayNightSwitch', 718, 'toggle'), ('GearLever', 83, 'lever'),
    ('LeftMFDBrightnessKnob', 704, 'knob'), ('InstrumentPanelBrightness', 705, 'knob'),
    ('ConsolesBrightness', 706, 'knob'), ('FloodLighting', 707, 'knob'), ('FormationLight', 714, 'knob'),
    ('PositionLight', 715, 'knob'),
    # AAR panel (stage 6): door switch and receptacle light knob, F-22 messages on F/A-18 templates
    ('APUMaster', 712, 'toggle', 'Fuel.AARDoor'), ('FloodLighting', 713, 'knob', 'Fuel.AARLight'),
    ('Throttle1Lever', 768, 'lever'), ('Throttle2Lever', 766, 'lever'),
]
# push buttons without an animated part: (name, F/A-18 button template, connector, offset, push direction, box size
# along the push / lateral / fore-aft, message, value). (The engine crank buttons on the throttle grips are gone: an
# F-22 engine starts by itself when its throttle leaves cut-off with APU air - make_f22.py, as the DCS mod.)
# EMER JETT (DCS JETT_PNT, its cap animated by 711): the F/A-18 left its own volume commented out (its tanks do not
# drop); the F-22's kicks the ferry tanks off (breakage_f22.tank_release). An F/A-18 panel button as the template,
# with the donor's message and qualifier for this button; the cap faces aft, pushed forward. Optional 9th: qualifiers
CLICK_BUTTONS = [
    ('EmergencyJettisonButton', 'JettisionSelectCenterButton', 'JETT_PNT', (-0.008, 0.0, 0.0), (1.0, 0.0, 0.0),
     (0.012, 0.032, 0.030), 'Controls.EmergencyJettision', 1.0, ' event '),
]
# click volumes that turn with their lever: volume -> (dynamics output, DCS arguments of the lever animation). The
# DCS throttles rest at mid travel (arguments 0), the F/A-18 volumes stayed there while the levers sat at cut-off on a
# cold start, ~28 deg (8-10 cm at the grip) further aft. Left mouse drag moves one lever, right drag both (group).
CLICK_FOLLOW = {
    'Throttle1Lever': ('Engine1ThrustLeverPosition', (768, 767)),
    'Throttle2Lever': ('Engine2ThrustLeverPosition', (766, 765)),
    # the gear handle swings 50 deg about its pivot behind the panel (user 2026-11-05: the click zone stood still, half
    # off the handle once it was up); GearLever 0 up .. 1 down, read from its published output (a control_input reads
    # dynamics outputs, as the throttles' Engine<n>ThrustLeverPosition)
    'GearLever': ('GfxOutGearLever', (83,), (0.0, 1.0)),
}
# lever click volumes on the grip instead of the middle of the whole part: (centre at the part's rest pose, (radius,
# length along the cylinder)). The gear handle's wheel: the vertices 2-3 cm in from the far end of its part (CP__7.003,
# rest = handle down), 30 mm across, 16 mm wide (scratchpad gear_knob.py, 2026-11-05) - the first volume sat 2 cm
# towards the pivot, at the middle of pivot and wheel
CLICK_GRIPS = {'GearLever': ((7.611, 0.3075, 0.7013), (0.017, 0.020))}
# click volumes without an animated part: (F/A-18 control, connector or connectors (midpoint), cylinder axis, drag
# direction (None: the control's own), (radius, length) or None)
CLICK_POINTS = [
    # canopy: the grab rails along both sills of the canopy frame (cockpit object edm_obj.001, y +-0.50, sloping from
    # z 0.96 at x 6.85 to z 0.87 at x 7.55): drag up = open, down = close (first try sat 3 cm above the rail)
    ('Canopy', [7.2, -0.50, 0.915], (0.992, 0.0, -0.127), (0.0, 0.0, -1.0), (0.035, 0.75)),
    ('Canopy', [7.2, 0.50, 0.915], (0.992, 0.0, -0.127), (0.0, 0.0, -1.0), (0.035, 0.75)),
]

# ---- visible breakage (block 3 of docs/reference/FAILURES.md, 2026-11-11). The DCS model's damage layers
# (F-22A.lua Damage, read with tools/edm_vis.py): each wing breaks at the root (arg 225 left / 215 right: everything
# outboard of y ~2.5 hides, stubs WING_x_IN_DAM + INSIDE_DAM show), again mid-span (224 / 214, not used: one physical
# break) and never at the tip; each fin above its base (243 / 242: the fin and rudder hide, FIN_x_BOTTOM swaps for
# FIN_x_BOTTOM_DAM). The root break matches the physical one (breakage_f22.py: console body outboard of y 2.6), so the
# pieces the DCS model hides with a part ride that part's body (export '<part>__B<body>', drawn on it by make_f22.py)
# and fly away with it; the stubs and the fin bases are parts of their own on the fuselage, swapped on the loss
# (breakage_f22.damage_graphics).
BREAK_BODIES = {225: 'LeftWing', 215: 'RightWing', 243: 'LeftVerticalStabilizer', 242: 'RightVerticalStabilizer'}
STATIC_PARTS = {'D_FinLeftBase': r'^FIN_L_BOTTOM$', 'D_FinRightBase': r'^FIN_R_BOTTOM$'}
HIDDEN_PARTS = {r'^WING_L_(IN|INSIDE)_DAM$': 'D_WingLeftStub', r'^(WING_R_IN_DAM|WINR_INSIDE_DAM)$': 'D_WingRightStub',
                r'^FIN_L_BOTTOM_DAM$': 'D_FinLeftStub', r'^FIN_R_BOTTOM_DAM$': 'D_FinRightStub'}


def PART_BODY(o, vis):
    """The physics body an exported object rides (None: the fuselage). DCS objects: an 'intact' visibility range (it
    ends at 1.0) of a break argument. Our formation panels (no EDM node): by place - wing tips beyond the console
    break, the fins' strips above their base."""
    if o.name.startswith(('FIN_L_BOTTOM', 'FIN_R_BOTTOM')) or o.get('aerofly_keep_all'):
        return None
    for arg, ranges in vis:
        if arg in BREAK_BODIES and any(lo < 0.0 and hi <= 1.0 for lo, hi in ranges):
            return BREAK_BODIES[arg]
    if o.name.startswith('FORMATION_PANEL_'):
        from mathutils import Vector
        c = sum((o.matrix_world @ v.co for v in o.data.vertices), Vector()) / len(o.data.vertices)
        if abs(c.y) > 2.6 and c.z < 1.0:
            return 'LeftWing' if c.y > 0 else 'RightWing'
        if c.z > 1.3 and abs(c.y) > 1.5:
            return 'LeftVerticalStabilizer' if c.y > 0 else 'RightVerticalStabilizer'
    return None
