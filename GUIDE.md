# F-22A: cockpit guide

*(untested)* marks things that follow the logic of the F/A-18 the aircraft is built on, but were not tried in the
F-22 yet.

## Displays

| Display | Shows |
|---|---|
| Upper left (UFD) | engines L/R: state (a burning engine shows L FIRE / R FIRE in red), RPM (%), EGT (°C), FF (fuel flow, lb/h), NOZ (nozzle, %), OIL (psi); below it ICAWS, the caution list |
| Upper right (UFD) | standby attitude indicator (speed left, altitude right), fuel (lb, coloured: green, amber under JOKER, red under BINGO) with time and range to BINGO, local time; the lower middle key (the next page's name over it) cycles SFI → TIME → NAV |
| ICP (top centre) | control panel: scratchpad on the left, 5 option lines at the arrow keys on the right |
| PMFD (centre) | map: route, airports, beacons (HSI) |
| Left / right / lower MFD | ENG / FUEL / FCS by default; the MENU key (bottom, middle) lists the pages |

**MFD pages** (MENU), in groups: along the top navigation and flying - HSI, SA, ADI, HUD (repeater), APPR (approach);
on the right the aircraft's systems - ENG, FUEL, FCS (flight controls), SYS (automation and power) and the hidden FAIL
(see Failures); on the left the mission - SMS (stores: bays, missiles, tanks), STAT (status), FPAS (range), CHK
(checklists); MENU at the bottom. There are no dummy keys on the pages: what has a label works. On the right MFD's
menu, **AUTO** (bottom, right of MENU; boxed when on, off at start) lets that screen follow the flight: the checklist
when parked with the brake set, APPR when the gear goes down in the air, FUEL when it comes up.

- **FUEL:** the upper two arrows on the right set BINGO, the lower two JOKER (shown beside them), 100 lb a press.
  JOKER is the fuel to end the fight and turn for home (5000 lb at start, BINGO 3000).
- **FPAS:** at the present fuel flow and ground speed: fuel (in the fuel colour), JOKER, BINGO, fuel above BINGO, flow,
  time and range to BINGO, miles per 1000 lb; below it the next waypoint with distance, time and fuel there; at the
  bottom the wind (direction and speed, *untested*).
- **ENG:** either side of the title a round N2 gauge per engine (the figure inside, the arc full at 100 %); below, each engine's state (OFF, MOTOR, START, RUN, FADEC = stopped by its FADEC switch, WMILL = windmilling,
  SEIZED; FIRE in red while it burns), N1 %, EGT °C, fuel flow lb/h, thrust kN, nozzle %, oil psi, vibration;
  below, the APU and the inlet temperature, and the aircraft as a whole: GW (gross weight, lb: empty + fuel + missiles
  and tanks), THR (both engines' thrust, kN) and T/W (thrust to weight). Top keys: L FIRE / R FIRE.
- **STAT:** the systems in one grid - BATT, APU, GEN L/R, HYD, A/T, AP, GCAS, VEC, DIR, BAY, GEAR, HOOK, P BRK,
  CANOPY, NAV, FORM, LDG, TAXI, BIT. White = off, green = on, amber = fault (a generator or hydraulics down, running
  on the battery, the canopy open in the air; DIR is amber whenever it is on).
- **APPR:** IAS, angle of attack, pitch, flight path angle, vertical speed, radar altitude; on the right the angle of
  attack cue against the 8.5° the autothrottle holds with the gear down - FAST (below 7.5°), ON SPD, SLOW (above
  9.5°); below, gear (UP / TRANS / DOWN), speed brake, A/T, hook.
- **FCS:** each surface left and right: deflection in degrees and status (OK, DEGD = one hydraulic system, HYD = no
  pressure, JAM, LOST); hydraulic pressure; FCS mode, vectoring, nozzle angle, vector authority, pitch rate; g limit,
  angle of attack, g and its peak. Keys on the left: DIR (direct FCS mode), VEC (thrust vectoring on / off).
- **SYS:** autothrottle (mode, target, step), Auto-GCAS (on / off, floor), generators, APU, battery, alternate gear.
  Keys on the left: GCS (Auto-GCAS), ALT GR (alternate gear extension); on the right A/T and the arrows and step for
  its target.
- **HSI:** TCN, ILS, WPDSG, SCALE; link to SA. **ADI:** link to HSI. **SA:** scale and compass, no other aircraft and
  no map; link to HSI.
- **CHK:** four lists picked by the left keys - START (cold start), T/O, LAND, SHUT. A line whose switch the
  aircraft can read turns from white to green once it is done (BATT on, APU running, canopy closed, CNI / ACP,
  display modes and HUD, generators, FLCS BIT, lamp test, lights, gear down, ICAWS clear...); notes are grey, what is
  automatic (TRIM AUTO) is green at once.

**ICAWS** (only what is active is lit): FUEL LOW, BINGO, JOKER, OVERSPD, GEAR SPD, L GEN, R GEN, PARK BRK, CANOPY,
SPD BRK, FLAPS, AP OFF, ANTISKID, BAY OPEN, BRK ACC, FCS, PULL UP, OVER G, AOA, GCAS, A/T and the failure cautions.
OVERSPD comes faster than 780 KCAS (the structure's limit is 800, rudder flutter starts over it); GEAR SPD with a gear
down faster than 280 KCAS (it is damaged from 300). A new caution blinks
until you acknowledge it with the left one of the three keys under the left UFD (MASTER CAUTION reset, RESET on the screen); then it is
steady until its cause is gone. SPD BRK, FLAPS, PARK BRK, BAY OPEN, PULL UP, AOA, GCAS, A/T, JOKER are advisories and do
not blink. On a cold start L GEN / R GEN blink at once: that is normal, acknowledge them.

**NAV** (right UFD, third page): the local time top left; the next waypoint of the Aerofly route (name, distance in NM, time in minutes), the
selected course (CRS) and heading (HSEL); RCV - whether the ILS and TACAN receivers are on (ICP: NAV → ILS / TCN →
UNDO). The boxed TCN / ILS on the HSI are another thing: they only pick what the HSI shows.

## Cold start

The aircraft stands as on the ramp: canopy open, every weapon bay open, the nozzles parked wide open (they stay
open on the ground until the engine reaches idle, and close as it does; in the air they never park). Close the bays
on the SMS page once the engines run (the doors need hydraulic pressure).

1. BATT on (two positions, ON / OFF; with engines and APU off, OFF takes all power from the aircraft).
2. APU on, about 4 s to come up: the displays get power, ICAWS shows L GEN / R GEN.
3. Displays on: on a cold start every display is off - the right knob at each MFD and UFD (its mode) stands at OFF.
   Turn it to DAY (two clicks) or NIGHT (one). The UFDs also run on the battery alone. HUD: the SYM thumbwheel, upper
   right of the ICP.
4. GEN L, GEN R on (they only connect the generators; a generator comes on line by itself at about 55 % RPM).
5. Left throttle from cut-off to idle: the engine starts by itself (air from the APU). L GEN goes out.
6. The same with the right throttle. APU off.
7. FLCS BIT (left console, the switch under the red guard - the guard lifts by itself): START - for 40 s the control
   surfaces run through their travel, stick and pedals do nothing, FLCS BIT on ICAWS; when BIT PASS shows, back to
   STOP. It needs power and hydraulic pressure and does not run in the air.

Throttles with the mouse: left button moves one lever, right button both (ranges: "Throttle and engine ratings").
On a cold start the cockpit lights (CONSOLE, INST PNL, FLOOD) are at zero: at night turn them up once there is power.

## Flaps and trim

The flaps are automatic, the flap keys do nothing: gear down gives the take-off / landing position (FLAPS on ICAWS),
gear up and the flight control system moves flaps and leading-edge flaps with angle of attack and speed. Pitch trim
is handled by the flight control system as well; leave it alone: in flight the stick at neutral holds 1 g. Lift-off:
about 135 kt with the stick fully back, more when heavy (ferry tanks).

## ICP: how it works

A key at the top selects a function → its options appear on the right → the arrow at an option selects it (a colon
`:` = selected / on). Numbers: type the digits (they show in the scratchpad) → **MRK = enter (ENT)**. **CLR** deletes
a character. **UNDO = ON/OFF** of the selected function (the F-22 panel has no ENT and ON/OFF keys, and the Hornet's
logic needs them). A page goes back to the empty one by itself after 30 s.

| Key | Options |
|---|---|
| A/P | autopilot: ATTH, HSEL, BALT, RALT, CPL |
| NAV | ILS, TCN (TACAN), ADF, CRS (course), HDG (selected heading) |
| IFF | **XPDR** - transponder on / off (colon = on; as UNDO); the code: digits → MRK |
| ALT | BALT, RALT (as under A/P); ALOW: threshold of the ALTITUDE call, digits in feet → MRK |
| HUD | NORM / REJ1 / REJ2 - declutter levels of the HUD; BARO / RALT - which altitude the HUD shows *(untested)* |
| OTHR | **LOAD** (the load, see Stores), **A/T** (the autothrottle, see Autothrottle), ADF2 (second ADF); failure codes (see Failures): digits → MRK |
| COM1 / COM2 | frequency: digits → MRK (the `:FREQ` hint) *(radios change almost nothing in Aerofly)* |

STPT and DVR do nothing: Aerofly sequences the route by itself.

## Autopilot

1. Level the aircraft at the altitude you want.
2. A/P → arrow at **BALT** holds the present altitude; **ATTH** holds bank and pitch.
3. **HSEL** holds the selected heading (HSEL lower left on the HSI, the bug on the HUD heading tape): the lower left ICP
   thumbwheel (1° a click) or NAV → HDG → digits → MRK. It does not follow the course line (CSEL) or the route.
   **CPL** shows as the fifth line only while TACAN or ILS is received (right UFD NAV: RCV ON): it flies the TACAN
   radial (CRS) or the ILS localizer. It does not follow the Aerofly route. *(untested)*
4. **RALT** holds the height above ground.
5. Off: the arrow at the mode again (the colon goes) or the autopilot disconnect key. *(untested)*

## ILS approach

Fly the needles by hand. With the ILS received, the autopilot's CPL follows the localizer, perhaps the glide slope too
*(untested)*; it does not land the aircraft.

1. Find the ILS frequency and the runway course (airport chart, e.g. airnav.com, or the Aerofly map).
2. **Frequency:** NAV → arrow at **ILS** → type the 5 digits without the point (110.90 → `11090`) → **MRK**.
   1-3 digits instead of a frequency are a channel number.
3. **Receiver on:** on the same page **UNDO** (ON/OFF): the scratchpad shows `ON`.
4. **Runway course:** NAV → arrow at **CRS** → type the course (e.g. `248`) → **MRK**. This is the course arrow of the HSI.
5. Fly to the extended centreline (handy: NAV → HDG → intercept heading → MRK, then A/P → HSEL).
6. Inside ILS coverage the needles appear on the HUD and the HSI: the vertical one is the deviation from the
   centreline, the horizontal one from the glide slope. Keep both centred; switch the autopilot off before the glide
   slope comes in. Vertical needle to the left - the centreline is to your left: turn left 10-20°, at the centre take
   up the runway course. Horizontal needle above the centre - you are below the glide slope: hold altitude until it
   centres, then descend at about 3° (vertical speed ≈ 5 × ground speed in knots, ft/min: 150 kt → about 750 ft/min).
7. Put the airport and runway into the Aerofly route (navigation menu): route and runway then show on the PMFD map.

**VOR / TACAN:** NAV → arrow at **TCN** → VOR frequency as 5 digits (114.70 → `11470`) or a TACAN channel as 1-3
digits → **MRK** → **UNDO** (ON). The HSI shows bearing and distance to the beacon.

## Fuel

The fuel burn is real (Aerofly has none, it is built into the aircraft): the fuselage tanks (TK1/TK4) empty first,
then the wing tanks, the feed tanks last; at zero the engines stop. Remaining fuel: FUEL page and right UFD; FUEL
LOW / BINGO on ICAWS. Changing the fuel in the menu during a flight restarts the count. The aircraft's mass does not
change as internal fuel burns (the simulator sets it).

Typical fuel flow: cruise M 0.85 at 40 000 ft - about 6900 PPH (71 nm per 1000 lb); supercruise M 1.5 at 34 500 ft -
about 20 700 PPH (42 nm); full afterburner M 2.2 at 34 000 ft - about 160 000 PPH (all internal fuel in 7 minutes).

## Throttle and engine ratings

The POWER ring of the game's interface shows the throttle position, not thrust and not RPM.

| POWER | Lever | Rating |
|---|---|---|
| 0-61 % | moves forward | N2 from 65 to about 98 % |
| **61-66 %** | **stays at the detent** | **military power, N2 100 %** |
| 66-97 % | moves forward | afterburner from minimum up, N2 100-101 % |
| 97-100 % | at the stop | full afterburner |

RPM hardly rises in afterburner, as on the real engine: read the afterburner from fuel flow FF, nozzle NOZ and the
flame. Speeds: military power at 34 000 ft gives about M 1.5 (no afterburner, slow to get there), afterburner M 2.2-2.25;
low down the afterburner holds about 800 kt (M 1.21 at sea level).

## Thrust vectoring and direct mode

The nozzles follow the stick by themselves, ±20° in pitch. On the ground with thrust the vectoring comes in between
95 and 125 kt and fades out towards 10° of pitch; at idle the nozzles follow the stick at any speed (a check). You
can see the nozzles from outside: stick back, the flap ends go up.

**Direct mode** (a wish of ours; the real F-22 has nothing like it): the DIR key on the FCS page. The stick bypasses
the F/A-18's laws and their protections: at low speed it commands pitch rate, at high speed it also moves the
stabilators directly. It comes in and goes out smoothly over 2 s; FCS is lit on ICAWS. At high speed full back stick
breaks the aircraft: the wings come off at 13.5 g (see "Structure").

## Autothrottle and Auto-GCAS

**Autothrottle.** Gear up it holds the speed at engagement: Mach from M 0.7 up, calibrated airspeed below. Gear down
it holds 8.5° angle of attack. Dry thrust only; the levers in the cockpit follow. It disengages when you move the
throttle by more than 3 % (thrust goes to the lever position at once), in afterburner and at touchdown.

ICP page **OTHR → A/T**:
- **A/T** - on / off (colon = on), as the A/T key on SYS.
- **MACH 0.85** and **KCAS 450** - the targets; the colon marks the one held. While the autothrottle is off the lines
  show the speed of the moment. Pressing a line holds it from the speed of the moment; digits typed first set the
  target (139 = M 1.39, 450 = 450 kt). Both engage the autothrottle.
- **SYNC** - both targets to the speed of the moment.
- **MRK** after digits sets the target held.
- While this page is open and the autothrottle is on, the ▲▼ rocker at the bottom right of the ICP steps the target
  by ±1 kt / ±M 0.01.

Coarse steps: the INC / DEC rocker at the upper left of the ICP or the arrows on SYS (the step: STEP, 1 / 5 / 10 /
50 kt, M 0.01 - 0.20).

**Auto-GCAS** (our choice; nothing is published about such a system on the F-22). On by default, the GCS key. It
works out the height margin from flight path, bank and speed and steps in at the last moment, as a pilot would: rolls
the wings level and pulls hard (about 8 g); the stick in the cockpit moves. While you already pull more than 2 g it
leaves you alone. GCAS is lit on ICAWS. Gear up only. Cancel: stick beyond half travel, or GCS. Diving fast from a
ridge into a valley it can still step in before you needed it.

**Voices:** PULL UP with the HUD arrow, ALTITUDE once when descending below the
ALOW threshold gear up (200 ft by default), BINGO, OVER G. Over the ILS markers a tone sounds where the game's data
has markers for the airport. When Auto-GCAS triggers a short tone sounds *(untested)*. The VOX knob on the RADIO VOL
panel (right console) sets their volume; at OFF it mutes voices and tones.

**Cockpit noise:** a soft airflow with airspeed, buffet at high angle of attack and g *(untested)*.

## Map

The terrain map is on the centre MFD (PMFD) only, HSI page, MODE key. The side MFDs have none: the engine keeps one
map. The ▲▼ rocker at the bottom right of the ICP is the map scale on the SA / HSI pages (the F-16 has its FLIR
rocker there, which this aircraft does not need); on the OTHR → A/T page with the autothrottle on it steps its target.

## Night lighting

INTERIOR LIGHTS panel on the left console: **MFD** - brightness of all MFDs, **INST PNL** - lettering of the front
panel and the ICP keys, **CONSOLE** - lettering of the side consoles, **FLOOD** - general cockpit light. Needs power
(battery). The game's cockpit light commands turn the same knobs.

## Brightness

Each screen (4 MFDs, 2 UFDs) has two knobs. The left one is its brightness. The right one is its mode, three
positions: OFF (screen off), NIGHT (0.3 of the day brightness) and DAY. Over them the masters: for all MFDs the MFD
knob of the INTERIOR LIGHTS panel, for both UFDs and the ICP the BRT thumbwheel by the ICP.

## ICP thumbwheels and rockers

The real F-22's ICP is not public; its thumbwheels and rockers work as the F-16's, which has the same ones. Turn a
thumbwheel with the mouse wheel or by dragging, 20 clicks over its range:

- **BRT** (upper left) - brightness of the UFDs and the ICP.
- **SYM** (upper right) - HUD brightness; at the very bottom the HUD is off, the first click turns it on at 0.3.
- **HDG** (lower left) - the selected heading (HSEL), **CRS** (lower right) - the selected course (CSEL), 1° a
  click; turning one opens the ICP's HDG / CRS page with the value (as the F-16's HDG and CRS knobs on the HSI).
- **▲▼ rocker, upper left** (INC / DEC) - steps the autothrottle target up / down, as the SYS page's arrows (the step
  size: STEP on the same page).
- **▲▼ rocker, lower right** - map scale (see Map); on the A/T page with the autothrottle on, its target ±1.

## Landing and taxi light

LDG/TAXI LIGHT switch (left console, at the gear handle): forward LDG, middle OFF, aft TAXI. Drag with the mouse.
The lights work only with the nose gear down.

## Stores: bays, missiles, tanks, refuelling

**The livery** is chosen in the aircraft menu: USAF and six community liveries (USAF squadrons and fictional schemes;
authors in CREDITS.md). The aircraft starts clean.

**The load** is chosen in the cockpit, four of them: **CLEAN** - empty bays; **COMBAT** - 6 AIM-120C in the main bay
and 2 AIM-9X in the side bays (157 / 85 kg each); **FERRY** - two 600 US gal tanks on pylons; **FULL** - both.
- **ICP: OTHR → LOAD** - the arrow at a load sets it at once, anywhere, in the air too (colon = the current one): the
  way to start with a load on the runway or in the air.
- **SMS → LOAD** (right column) - round CLEAN → COMBAT → FERRY → FULL, on the ground with the parking brake set only
  (the engines may run), as the ground crew would.

Missiles fired and tanks jettisoned do not come back either way: to rearm, choose the livery again (the aircraft
reloads where it is, clean), then LOAD. Tanks hung where there were none come full; tanks already hanging (FERRY →
FULL) keep what is in them.

**SMS page** (stores) on any MFD: MENU → upper left key **SMS**.
- Left keys **LFT / CTR / RGT** open and close each bay (boxed = commanded open), **ALL** all of them (if all are
  closed: open, otherwise close).
- Right keys: **120 / 9X** select the missile (boxed), **LOAD** the load (above), **REL** releases the next one, **S-J** jettisons the tanks.
- In the middle: what is still in each bay and its door state (CLSD / MOVE / OPEN), **STATUS**, the tanks, **LOAD** (the load).
- Under the table the aircraft from above (from our model): the bay doors (solid frame closed, dashed moving, thick
  with the doors marked open), each missile while it is aboard, the tanks while they hang. While any bay is not
  closed, ICAWS shows **BAY OPEN**. The side bays swing the AIM-9X out on its launcher with the doors. Needs power.
  Open bays add no drag.

**Missile release (for the pictures - no targets, no guidance):** MASTER ARM (front panel, right of EMER JETT) to
**ARM** (the left MFD turns to SMS; SAFE puts ENG back), in the air, select **120** or **9X**, then **REL** or the key assigned to **Strobe** in the game's control
settings (the F-22 has no strobe lights). The bay opens by itself; an AIM-120C is thrown down by its ejector and lights
its motor a moment later, an AIM-9X leaves its rail forward with the motor lit. The missile flies on along its axis on
its own thrust (about 6 s for the AIM-120C, 5 s for the AIM-9X, estimates) and coasts on level out of sight (it holds
its line as if guided; launched in a dive onto water it would end the flight - the game counts any part of the
aircraft touching water as a crash); the bay closes
again 1.5 s after the launch. You hear the motor light and roar away (muffled in the cockpit). One launch at a time. **STATUS:** SAFE (MASTER ARM off), GND (on the ground), LAUNCH,
EMPTY (none of the selected kind left), READY. The motor glows; there is no smoke trail - the game has nothing to draw
one with.

**Ferry tanks:** their fuel goes first; the FUEL page shows what is left in them under the wing tanks, **EXT L /
EXT R** (lb). **Jettison:** the **EMER JETT** button (left edge of the front panel, left of MASTER ARM), **S-J** on the
SMS page, or the key assigned to **Hook** in the game's control settings (the gliders' tow release) drops both tanks
with their pylons, as on the F-22. In the air and with power only; on the ground it is locked. Each tank is pushed off
by the pylon's ejector and falls by itself with its own mass and drag; its fuel leaves the count. To get the tanks
back change the livery, then LOAD. The aircraft's mass (and GW on the ENG page) goes down with the ferry fuel as it
burns; missiles and tanks weigh what the real ones do, and a jettisoned tank takes its mass with it.

**Air refuelling (for looks):** left edge of the front panel under EMER JETT: the AAR switch opens the receptacle
door behind the cockpit, the knob is its light. Aerofly has no air refuelling.

## Outside view

From outside you see a pilot in the cockpit and pictures of the pages on the screens (live screens are not drawn
from outside). Without power the pictures go dark with the screens.

## Failures (FAIL page)

A hidden instructor page. To open it: on the ICP press **OTHR** (or use the empty ICP page), type **9900** and press
**MRK** - the right MFD shows FAIL at once, and the menu of every MFD keeps a **FAIL** link at the bottom right. In the
same way **9999** switches COND on and off without the FAIL page. Left: ▲▼ cursor, **SEL** breaks
the selected item now (or repairs it). Right: **RAND** - one random failure in 1-15 minutes (you know neither which
nor when), **COND** - failures caused by how you fly (**on from the start**; this key turns it off), **RST** -
repair everything, **PAGE** - second page.

| Failure | What you see | What to do |
|---|---|---|
| L/R GEN | ICAWS L GEN | GEN off and on again: it comes back |
| GEN ARC | L GEN, then HYD | **do not touch GEN**: a restart sets the left side on fire. Land |
| L/R HYD | HYD, pressure falls within a minute | both systems move the surfaces - hardly felt in flight. **R HYD** (utility): the gear does not retract, extension by free fall (lever down), brakes on the accumulator only (about 8 s of full braking), no nose wheel steering: long runway. **L HYD**: the bay doors stay as they are |
| L/R BLEED | ICAWS BLEED; at full power the EGT of that side is about 35° higher | throttle below 70 % (EGT comes back), descend; at full power a fire after a minute |
| OBOGS | ICAWS OBOGS | below 10 000 ft: backup oxygen for 10 min, then OXY LOW |
| L/R OIL | OIL 0; then VIB rises on the ENG page (from about 1.4 to 3+ in 50 s), EGT after it | shut the engine down (FADEC) - about 60 s at full power, 90 s at idle. Seized: L/R SEIZED, RPM 0, a restart is useless |
| L/R AB | no afterburner | fly at MIL |
| NOZZLE | ICAWS NOZZLE | the nozzles are frozen: no vectoring |
| FUEL LK | nothing, the fuel just goes faster | compare FUEL / FPAS, nearest airport |
| L MFD / PMFD | the screen is dark | use the pages on the other screens |
| ANTISKD | ICAWS ANTISKID | brake gently |
| L/R FLAME | L/R ENG, RPM falls | FADEC off (or throttle to cut-off), APU START, FADEC NORM, throttle forward; MOTOR if needed |
| L/R FIRE | red FIRE; the engine runs, after 50 s of fire VIB rises | ENG page: **L FIRE** (left column, top) / **R FIRE** (right column, top). First press shuts this engine's fuel (the engine stops, the key is boxed and reads DSCH), second press fires the bottle: the fire is out. One bottle for both sides; without a bottle the key reads FUEL - a press gives the fuel back (start as after a flameout). Burning: after 40 s no hydraulics on that side, 80 s the engine seizes, 150 s the fire reaches the other hydraulic system. Two fires at once: you can put out one |
| PITOT | the airspeed lies: rises in a climb, falls in a descent (to 0), AIR DATA after 8 s. Every speed display, the A/T and the FCS gains are wrong | fly by angle of attack and thrust, ground speed is on the map; do not engage A/T |
| DUAL ENG | both engines stopped | air start on the APU. Until then the windmilling engines keep the hydraulic pressure but turn the pumps slowly: the surfaces move slowly, the aircraft answers late and can drop a wing; a running APU adds some flow. Out of fuel there is no restart |

**FAIL page 2** (PAGE key; the cursor runs over both pages), landing gear: **L / R / N GR UP** - the up-lock does not
release (a retracted leg stays in its bay; **ALT GR** on the SYS page is the alternate extension: the locks let go,
the gear comes down and stays down until RST); **L / R / N DNLK** - the down-lock does not hold: amber lamp, the leg
folds under weight; **NWS** - nose wheel steering lost, the wheel centres; **L / R BRAKE** - that side's brake and
parking brake are gone; **L / R WHL SZ** - a wheel is seized: it drags, and a long skid at speed bursts the tyre;
**L / R / N TIRE** - the tyre bursts at once. At the bottom TD SIDE: sideways speed of the last touchdown, kt.

**COND** (failures from how you fly): gear down above 300 kt for 3 s - damaged, does not retract (GEAR); less than
-0.5 g for 30 s - both engines stop; more than 60° angle of attack below 60 kt in afterburner for 3 s - one engine
stalls; heavy braking heats the brakes (BRK HOT) and they fade, cooling takes about 10 minutes; above about 820 kt -
rudder flutter (a hum, yaw shake): slow down or a fin comes off; touchdown at more than 600 ft/min (10 ft/s) - HARD
LDG, more than 900 ft/min (15 ft/s) - the leg that took it folds (GEAR); full braking without antiskid or on
overheated brakes bursts a tyre (a bang, the aircraft pulls to that side).

**How a failure feels** (without the FAIL page): a damaged engine (oil, fire at its case) "hunts" - thrust wanders
by a few percent, you hear it in the engine tone and feel a slight yaw, stronger towards the seizure, with a low
uneven rumble. A seized engine stops within about 1.5 s with a grinding noise instead of running down. Above about
250 kt the extended gear hums and shakes before it is damaged. When a generator drops, the MFD of its side blinks
for 0.3 s (bus transfer). During its first 40 s a fire shows by FIRE alone; there is no smoke.

## Structure

The wing panels come off at 13.5 g (a 9 g limit with a factor of 1.5 - our estimate, the real strength of the F-22
is not published). With the normal control laws you cannot pull more than 9 g; in DIR (up to 16 g) at high speed you
can overdo it: a wing leaves, the aircraft jerks and is hardly controllable. A light touch of a wingtip on the runway
is a scratch, a hard one tears the wing off. 13.5 g at 500 kt is a little over 80 % of stick travel. After a
break-up start a **new flight from the menu**: time rewind and RST on the FAIL page do not bring a wing back. The
fins stand any flight with the normal laws; flutter breaks them (COND, above about 820 kt) or a tumble in DIR. What is
lost shows on the **FCS** page (surface table): OK, DEGD (one hydraulic system), HYD (no pressure), LOST.

## Controls that do nothing yet

Every switch, knob, key, thumbwheel and rocker in the cockpit moves and can be clicked, but not all of them have a
function yet: AUX GEN, FUEL TANKS, the ECS CABIN panel, the RADIO VOL knobs other than VOX, the AUX COMM panel, the
OXYGEN panel, the ICP's STPT and DVR keys, three of the left UFD's keys and the right UFD's top key. They are prepared for new functions: the list with the name of each control's state is in
**COCKPIT_CONTROLS.md** - a function can be added with the Python scripts alone, no model work and no converter.
The gear handle's wheel glows red while the gear is in transit.
