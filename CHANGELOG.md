# Changelog

## v0.9.3

On the ramp
- After a cold start on the ground (both engines off) the aircraft stands as it would on the ramp: a boarding ladder,
  wheel chocks, red intake plugs, black exhaust plugs deep in the nozzles, covers on the nose probes, locks on the
  flaperons, ailerons and stabilators, the hook's safety pin, gear pins and AIM-9X seeker caps with REMOVE BEFORE
  FLIGHT streamers, a ground power cart with its cable, a fire extinguisher, a tool cart and a munitions trailer (two
  AIM-120C and two AIM-9X on it with the CLEAN load, empty when the aircraft carries them)
- It goes as you prepare the aircraft: the ladder is laid down 1.5 s after the canopy starts closing; plugs, covers
  and locks come off when the APU starts; the cable once the APU is up; chocks and pins when the parking brake is
  released, which also clears anything still on the aircraft. Everything stays on the ramp when you taxi away
- The power cart is real ground power: with BATT on it feeds the aircraft until the cable comes off

Missiles
- Fixed: after missile launches the game paused again and again as after a crash. A missile now flies about 10 s, or
  until it comes near the ground or water, and then vanishes; one launched in a manoeuvre no longer tumbles

Displays
- HUD drawn once instead of twice: the frame rate no longer stutters while the HUD is in view. The combiner has a
  tinted glass instead, so the symbols read well by day
- The centre MFD has the same black as the side screens (the square around the SMS picture is gone)

## v0.9.2

Stores
- SMS page (was BAY): select AIM-120 or AIM-9X and release them one by one with REL or the key assigned to Strobe -
  for the pictures, no targets: the bay opens by itself, the AIM-120C is ejected down and lights its motor, the AIM-9X
  leaves its rail; each missile flies on its own thrust and its motor glows. MASTER ARM now works (ARM / SAFE) and brings the SMS page up on the left MFD (SAFE: back to ENG)
- The load is chosen in the cockpit, not in the menu: CLEAN, COMBAT (6 AIM-120C + 2 AIM-9X), FERRY (two 600 gal
  tanks) or FULL - at once and anywhere from the ICP (OTHR → LOAD), or round on the SMS page's LOAD key on the ground
  with the parking brake set. The aircraft starts clean; fired or jettisoned stores come back with the livery chosen
  again
- Missiles and tanks weigh what the real ones do and move the centre of gravity; the gross weight on the ENG page
  counts them and drops as missiles go and ferry fuel burns
- Launch sound from a real recording: outside it goes away with the missile, in the cockpit it is muffled and grows
  with the engines' noise, so it is heard at full afterburner too
- Tanks can be jettisoned from the SMS page (S-J) and from the key assigned to Hook (the gliders' tow release), so
  you can watch them go from outside
- Six community liveries from DCS World painters (Texac, AsilTurq, Danksley, _BillyTheKid_; names in CREDITS.md): USAF
  ED 005, OT mirror coating test, AK 193; fictional TuAF KAAN, Crimson Squadron, ISAF Mobius One - one menu entry
  each, any load
- The BEFORE TAKEOFF checklist checks the weapon bays are shut; its MASTER ARM line reads the switch itself
- The silhouette on the SMS page shows each missile while it is aboard

Afterburner
- New flame from the 2D nozzles: violet at the exit, through magenta and pink to orange-red, a flat column with four
  shock diamonds - best seen at night; in daylight it is faint, as the real one
- The inside of the nozzles at afterburner: dark red at the exit to yellow-white at the flame holder, brighter, with a
  slow flicker running aft along the duct; the flame starts a little behind the exit so its glow no longer veils it

Displays and controls
- ICP: OTHR holds LOAD, A/T and ADF2. The A/T page shows MACH and KCAS with their targets (the speed of the moment
  while it is off), the one held marked; a line press holds it, digits set it, SYNC catches the speed, and the lower
  right rocker steps it by 1 kt / M 0.01 on that page
- ICP clean-up: the radio lines that did nothing are gone (COM: a :FREQ hint), IFF is one XPDR on / off line, TACAN
  lost its A/A line (it was T/R again), STPT no longer opens an empty page; option lines take 10 characters
- The failure codes (9900 FAIL, 9999 COND) work on the OTHR page too, digits and MRK
- MFD menu in groups: navigation along the top, the aircraft's systems on the right, the mission on the left
- Every screen on the same black background (the side screens had the F/A-18's green)

Flight
- Top speed low down as the real F-22: about M1.21 / 800 kt at sea level on full afterburner (it reached ~1030 kt at
  4000 ft); above 30000 ft unchanged

Cold start
- Parked as on the ramp: every weapon bay open, the nozzles wide open until the engine reaches idle (on the ground
  only)

## v0.9.1

Displays and controls
- New MFD pages: STAT (every system in one grid, white off / green on / amber fault) and APPR (speed, angle of attack
  with a FAST / ON SPD / SLOW cue, pitch, flight path, vertical speed, radar altitude, configuration)
- AUTO on the right MFD's menu: that screen follows the flight - checklist when parked, APPR with the gear down, FUEL
  after take-off
- Checklists come alive: a line turns green once the aircraft sees it done; notes are grey
- ENG: round N2 gauges beside the title, gross weight, total thrust and thrust-to-weight; FIRE shows in the burning
  engine's column (ENG page and left UFD)
- BAY: the aircraft seen from above with its bay doors, missiles and ferry tanks
- Right UFD: a third page, NAV - next waypoint, distance, time to it, selected course and heading, receivers, clock
- Fuel figures turn amber under JOKER and red under BINGO; JOKER is set beside BINGO on the FUEL page
- New warnings before damage: OVERSPD (over 780 KCAS) and GEAR SPD (gear down over 280 KCAS)
- The lower ICP thumbwheels set the selected heading (HDG) and course (CRS), 1° a click
- Fixed: the FPAS page's time and fuel to the next waypoint (the game's arrival time of day was read as a duration)

Flight model
- Altitude hold no longer oscillates at low level above about 645 KIAS: fuselage lift is no longer counted twice under
  the inner wing, the stabilator root has its real 42° sweep, and the F/A-18 pitch laws lose gain with airspeed
- Auto-GCAS steps in at the last moment, as a pilot would: not while you already pull over 2 g, 25 m margin, fly-up
  at about 8 g
- Hydraulics as variable-displacement pumps: the pressure holds, the surface rate follows engine rpm; on windmilling
  engines (both out, out of fuel) the controls are slow
- No more tail shake at 500-650 kt (fin attachment, and the rudders' command eases off at high speed)
- Direct mode: sharper thrust vectoring, the nozzles still within ±20°

Sound
- Engine sound: the stock F-15E's recordings on both engines (copied from your game by the installer)
- Damage sounds from real recordings (CC0): gear collapse, belly scrape, engine seizure, tyre burst, compressor stall

Exterior
- Wingtip navigation lights: the model's own lenses glow and bend with the wing; the red wingtip strobes are gone
  (no source shows them on the F-22)
- Fixed a stray surface beside both UFDs

Installer and documents
- macOS: how to run the installer from Terminal (macOS 15 and newer block install.command the first time)
- GUIDE: lift-off about 135 kt; Auto-GCAS and engine-out hydraulics described
- README: an unofficial way to fly the F-22 on Android in place of a downloaded aircraft (not supported)

## v0.9.0 — public beta

First packaged release, for testing the installer on other computers (Windows above all).

- Installer that builds the aircraft from the user's own F/A-18C; no IPACS files in the package
- Aircraft state: cockpit, displays and ICP pages, cold start with APU, thrust vectoring, autothrottle, Auto-GCAS,
  fuel system, weapon bays and stores, ferry tank jettison, night lighting, failures and damage (FAIL pages 1 and 2)
- Voice warnings spoken by a freely licensed synthesiser (Kokoro-82M)
- Every switch, knob, key, thumbwheel and rocker of the cockpit is a moving, clickable part; those without a
  function yet are listed with their state names in COCKPIT_CONTROLS.md, ready for new logic in the scripts
- Each screen's right knob is its mode (OFF / NIGHT / DAY); a cold start leaves the screens at OFF
- ICP thumbwheels and rockers as the F-16's: BRT (UFDs and ICP), SYM (HUD, now with an OFF at the bottom), INC / DEC
  of the autothrottle target, map scale
- Known limit: altitude hold oscillates at low level above about 645 KIAS subsonic (see README)
