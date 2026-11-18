# Changelog

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
