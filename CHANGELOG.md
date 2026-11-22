# Changelog

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
