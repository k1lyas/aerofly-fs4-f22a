# F-22A Raptor for Aerofly FS 4 — version 0.9.0

A free, unofficial add-on aircraft for the desktop version of Aerofly FS 4 (Windows, macOS).
Not affiliated with or endorsed by IPACS, Lockheed Martin, Eagle Dynamics or Grinnelli Designs.

**Public beta.** Developed and tested on macOS; the installer has not been run on Windows yet. If you try it on
Windows, please tell us in the forum thread whether it worked - with `f22_install.log` from your Aerofly user folder
if it did not.

- Forum thread (news, questions, bug reports): https://www.aerofly.com/community/forum/index.php?thread/30495-f-22a-raptor-for-aerofly-fs4-work-in-progress-videos-updates-feedback-welcome/
- Source code and new versions: https://github.com/k1lyas/aerofly-fs4-f22a

## What you get

- Exterior and cockpit of the F-22A (model of the Grinnelli Designs DCS World mod, GPL-3), clickable cockpit
- Displays: HUD, moving map / HSI, engine, fuel, FPAS, flight control, systems and weapon bay pages, ICP with radio,
  navigation and autopilot pages, ICAWS warnings
- Cold start with APU, engine start from the throttles, electrical and hydraulic systems
- Thrust vectoring nozzles driven by the flight control laws, autothrottle, Auto-GCAS
- Fuel burn with tank sequencing, afterburner flame, night lighting, formation lights
- Weapon bays with AIM-120C / AIM-9X (combat livery), 600 gal ferry tanks that can be jettisoned (ferry livery)
- Failures and damage: engine, electrical, hydraulic and gear failures by hand, at random or caused by how you fly;
  wings and fins that can be torn off, burst tyres, collapsing gear

How to use the cockpit: see **GUIDE.md**.

## What you need

- Aerofly FS 4 for PC or Mac (Steam). The mobile version cannot load add-on aircraft.
- The stock **F/A-18C** that comes with the game (it does - do not delete it).
- **Python 3.8 or newer** (no extra packages). Windows: https://www.python.org/downloads/ (tick "Add python.exe
  to PATH") or `winget install Python.Python.3.12`. macOS: `xcode-select --install` or python.org.
- About 300 MB of free disk space.

## Why there is an installer

The flight model, systems, displays and engine sounds of this add-on are built on the game's F/A-18C. Those files
belong to IPACS, so they are **not in this package**. The installer reads the F/A-18 of *your own* game, writes the
F-22's configuration files from it on your computer and copies the F/A-18's engine sounds next to them. The game's
own folder is not changed; only `aircraft/f22` in your Aerofly user folder is written.

## Install

1. Get the package: the zip of the latest release (or "Code > Download ZIP" of the repository) and unzip it
   anywhere (not into the game folder).
2. Close Aerofly FS 4.
3. Windows: double click **install.bat**. macOS: right click **install.command** > Open (the first time macOS asks
   for confirmation), or in a terminal: `python3 install.py`.
4. Start the game: the aircraft is listed as **F-22A**.

The installer finds the game in your Steam libraries and your user folder
(`Documents\Aerofly FS 4` on Windows, `~/Library/Application Support/Aerofly FS 4` on macOS). If it cannot:

    python3 install.py --game "<...>/steamapps/common/Aerofly FS 4 Flight Simulator" --user "<your Aerofly FS 4 folder>"

At the end it says whether the files it built are identical to the build that was flight tested
(`verified: ...`). With another game version they may differ; the aircraft is installed all the same.

## Update

Download the new package and run its installer: it replaces the installed F-22. The previous one is moved to
`<user folder>/aircraft_backup/` (the last two are kept; delete them when you like). The installer tells you when a
newer version is out.

A game update does not touch the installed F-22. Reinstall only when a new release of the add-on asks for it.

## Uninstall

    python3 install.py --uninstall

or delete the folder `aircraft/f22` in your Aerofly user folder.

## If something goes wrong

- *Python was not found*: install it (see above), then start the installer again.
- *Aerofly FS 4 was not found*: use `--game` as shown above (Steam: right click the game > Manage > Browse local files).
- *The configuration generator failed*: your F/A-18 files differ from the tested ones in a way the generator cannot
  handle. Please post the file `f22_install.log` from your Aerofly user folder in the forum thread, with your game
  version.
- The aircraft loads but behaves oddly after a game update: look for a newer release; report it in the thread.

Tested with: Aerofly FS 4 Steam build 26705403, macOS. Reports from other systems and game versions are welcome.

## Known limits of this version

- Engine sound is the F/A-18's.
- Altitude hold (BALT and RALT) at low level and high subsonic speed: from about 645 KIAS below roughly 1000 ft the
  aircraft goes into a strong pitch oscillation. Use the hold higher, slower or supersonic; disconnect it if it
  starts. The aircraft makes too much lift per degree of angle of attack for the F/A-18's autopilot; a flight model
  revision is planned.
- The SA page shows no other aircraft; no arresting hook; air refuelling is visual only.
- Aerofly does not change the aircraft mass with internal fuel burn; radios and IFF pages do nothing in the game.
- Items marked *(untested)* in GUIDE.md follow the F/A-18's logic and were not checked in the F-22 yet.

## Want to help?

Many cockpit controls already move and click but have no function yet (ECS, oxygen, AUX COMM, two ICP
thumbwheels, four UFD keys and more). **COCKPIT_CONTROLS.md** lists each of them with the name of its state: a function can be added in
the Python scripts of the folder `generator/` alone - no 3D work and no IPACS converter; run the installer again
to rebuild the aircraft with your change. Ideas and patches: https://www.aerofly.com/community/forum/index.php?thread/30495-f-22a-raptor-for-aerofly-fs4-work-in-progress-videos-updates-feedback-welcome/ or https://github.com/k1lyas/aerofly-fs4-f22a.

## Licence

GNU General Public License version 3 (file LICENSE): you may use, change and share this add-on; if you share it or
a changed version, do it under the same licence and with the sources. The complete sources of our part (conversion
pipeline, configuration generator, installer) are in the folder `source/` of this package and at the address above;
the original model: https://github.com/grinnellidesigns/f-22a. Authors and sources: CREDITS.md. There is no warranty.
