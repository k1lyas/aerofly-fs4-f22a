# F-22A cockpit controls prepared for new functions

Every control below is already a moving, clickable part of the cockpit with a state of its own, but nothing in
the aircraft reacts to it yet. Giving one a function needs the Python scripts only - no model work and no
IPACS converter: run the installer again and the aircraft is rebuilt with your logic.

## How to use a control

1. Find its row. `State` is the name of its dynamics object; read it as `<State>.Output`.
2. In `generator/make_f22.py` (or one of the system modules beside it) feed that output into your logic, the
   same way the working switches do - search for `F22CNISwitch` (a toggle that powers the nav receivers) or
   `F22VoiceVolume` (a knob) for a short worked example.
3. The part already moves with the state (table and angles in `generator/cockpit_controls.py`); change the
   positions, the default or the angles there if your function needs other ones.
4. Run the installer (it will warn that the built files differ from the tested build: expected after a
   change); check `tm.log` in the Aerofly user folder if the aircraft does not load.

Values: toggles and selectors hold the whole numbers listed under `Positions`; knobs and wheels run from 0 to 1
in equal clicks (20 clicks; the FREQ knobs 36); a button is an `input_button` - give it `Events` (see
`push_button()` in make_f22.py for a held state). A rocker holds +1 / -1 while a half is pressed, 0 at rest.

| Panel | Lettering | Kind | State (`.Output`) | Message of the click | Positions | Default |
|---|---|---|---|---|---|---|
| ELECTRIC | AUX GEN | guarded toggle (the red lid lifts by itself) | `F22AuxGen` | `Electrical.F22AuxGen` | 0 = ON, 1 = OFF/RESET | 0 |
| FUEL | TANKS | two-position toggle | `F22FuelTanks` | `Fuel.F22Tanks` | 0 = ALL, 1 = EXT | 0 |
| FLCS | (no lettering, forward of BIT) | guarded toggle (the red lid lifts by itself) | `F22FlcsSwitch2` | `FCS.F22Switch2` | 0 = guarded, 1 = actuated | 0 |
| FLCS | AAR | two-position toggle | `F22FlcsAar` | `FCS.F22Aar` | 0 = AUTO, 1 = OFF | 0 |
| ECS CABIN | TEMP | rotary knob | `F22CabinTemp` | `ECS.F22CabinTemp` | 0 .. 1 (COLD .. HOT) | 0.5 |
| ECS CABIN | ANTIFOG | rotary knob | `F22AntiFog` | `ECS.F22AntiFog` | 0 .. 1 (COLD .. HOT) | 0.5 |
| ECS CABIN | AIR SOURCE | rotary selector | `F22AirSource` | `ECS.F22AirSource` | 0 = OFF, 1 = R, 2 = BOTH, 3 = L, 4 = DUMP | 2 |
| ECS CABIN | MODE | two-position toggle | `F22EcsMode` | `ECS.F22Mode` | 0 = AUTO, 1 = MAN | 0 |
| RADIO VOL | ICS | rotary knob | `F22VolumeICS` | `Communication.F22VolumeICS` | 0 .. 1 (OFF .. INC) | 0.5 |
| RADIO VOL | RWR | rotary knob | `F22VolumeRWR` | `Communication.F22VolumeRWR` | 0 .. 1 (OFF .. INC) | 0.5 |
| RADIO VOL | MDS | rotary knob | `F22VolumeMDS` | `Communication.F22VolumeMDS` | 0 .. 1 (OFF .. INC) | 0.5 |
| RADIO VOL | RCN | rotary knob | `F22VolumeRCN` | `Communication.F22VolumeRCN` | 0 .. 1 (OFF .. INC) | 0.5 |
| RADIO VOL | AUX | rotary knob | `F22VolumeAUX` | `Communication.F22VolumeAUX` | 0 .. 1 (OFF .. INC) | 0.5 |
| AUX COMM | BRT | rotary knob | `F22AuxCommBrightness` | `Communication.F22AuxBrightness` | 0 .. 1 (OFF .. bright) | 0.5 |
| AUX COMM | FREQ (left knob) | rotary knob | `F22AuxCommFreqLeft` | `Communication.F22AuxFreqLeft` | 0 .. 1 | 0 |
| AUX COMM | FREQ (right knob) | rotary knob | `F22AuxCommFreqRight` | `Communication.F22AuxFreqRight` | 0 .. 1 | 0 |
| AUX COMM | ZEROIZE | guarded toggle (the red lid lifts by itself) | `F22Zeroize` | `Communication.F22Zeroize` | 0 = guarded, 1 = ZEROIZE | 0 |
| AUX COMM | MODE | rotary selector | `F22AuxCommMode` | `Communication.F22AuxMode` | 0 = KP, 1 = MAN, 2 = PRESET, 3 = GUARD | 1 |
| OXYGEN | TEST | push button | `F22PressOxygenTest` | `Oxygen.F22Test` | 1 = pressed | 0 |
| OXYGEN | MIXTURE | two-position toggle | `F22OxygenMixture` | `Oxygen.F22Mixture` | 0 = AUTO, 1 = FULL | 0 |
| OXYGEN | FLOW | two-position toggle | `F22OxygenFlow` | `Oxygen.F22Flow` | 0 = BYPASS, 1 = NORMAL | 1 |
| OXYGEN | OBOGS | two-position toggle | `F22Obogs` | `Oxygen.F22Obogs` | 0 = OFF, 1 = ON | 1 |
| right console, far aft | (no lettering) | guarded toggle (the red lid lifts by itself) | `F22AftRightGuarded` | `Controls.F22AftRightGuarded` | 0 = guarded, 1 = actuated | 0 |
| left UFD | lower right knob | rotary knob | `F22LeftUfdKnobRight` | `UFD.F22LeftKnobRight` | 0 .. 1 | 0.5 |
| right UFD | lower right knob | rotary knob | `F22RightUfdKnobRight` | `UFD.F22RightKnobRight` | 0 .. 1 | 0.5 |
| left MFD | upper right knob | rotary knob | `F22LeftMfdKnobRight` | `LeftMFD.F22KnobRight` | 0 .. 1 | 0.5 |
| PMFD (centre) | upper right knob | rotary knob | `F22PmfdKnobRight` | `MPCD.F22KnobRight` | 0 .. 1 | 0.5 |
| right MFD | upper right knob | rotary knob | `F22RightMfdKnobRight` | `RightMFD.F22KnobRight` | 0 .. 1 | 0.5 |
| lower MFD | upper right knob | rotary knob | `F22LowerMfdKnobRight` | `LowerMFD.F22KnobRight` | 0 .. 1 | 0.5 |
| ICP | lower left thumbwheel | thumbwheel | `F22IcpWheelLowerLeft` | `ICP.F22WheelLowerLeft` | 0 .. 1 | 0.5 |
| ICP | lower right thumbwheel | thumbwheel | `F22IcpWheelLowerRight` | `ICP.F22WheelLowerRight` | 0 .. 1 | 0.5 |
| ICP | upper left rocker | rocker | `F22IcpRockerLeft` | `ICP.F22RockerLeftUp / ICP.F22RockerLeftDown` | -1 = lower half held, 1 = upper half held | 0 |
| ICP | DVR key | push button | `F22PressIcpDvr` | `ICP.F22Dvr` | 1 = pressed | 0 |

## Controls that already work

These came from the same static geometry and are wired to systems (see GUIDE.md): FLCS BIT and its guard, ALT FLAPS,
YAW TRIM, FADEC, ENGINES MOTOR, LAMP TEST / NVG, CNI, AUX/ACP, RADIO VOL VOX, DN LOCK OVERRIDE, the screen and ICP
keys, the two upper ICP thumbwheels (UFD and HUD brightness), the lower right ICP rocker (map range) and the
armrest over the right console (a click folds it up against the wall: state `F22Armrest`).
The left knob at each screen (4 MFDs, 2 UFDs) is that screen's brightness (states `F22<Screen>KnobLeft`, 0 .. 1,
default 1), under the master dimmers: the MFD knob of the INTERIOR LIGHTS panel, the wheel left of the ICP for the UFDs.
The keys of the screens and of the ICP all go in while held; the left UFD keys `UFD.LeftPage`, `UFD.LeftKey2` and
`UFD.LeftKey3` are still free (states `F22PressL_SMFD_1`, `F22PressL_SMFD_3`, `F22PressL_SMFD_4`).

Not prepared: the cap at the right sill and the flat round plugs at the lower corners of the MFD frames (not
controls), DN LOCK OVERRIDE and RESET beside the gear handle (painted on the panel: click zone only).
