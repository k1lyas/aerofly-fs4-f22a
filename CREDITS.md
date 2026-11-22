# Credits

## 3D model, cockpit and textures

**F-22A Raptor mod for DCS World, "MK II - EFM"** — Copyright (C) 2024 Joseph Grinnelli, **Grinnelli Designs**
(https://grinnellidesigns.com/, https://github.com/grinnellidesigns/f-22a), GNU GPL version 3.
Contributors named by the mod: Branden Hooper (external flight model), Ash Blythe and David McMasters (weapons,
shapes and textures).

This add-on is a **modified** version of that work (changes made October - November 2026): the exterior and cockpit
models were converted from the DCS format to Aerofly FS 4, split into moving parts and re-animated; faces were
repaired, the cockpit merged with the airframe; textures were converted, cockpit lighting and wear were baked,
squadron decor was painted out; missiles, ferry tanks, pylons, engine interior, afterburner, lamps and display caps
were added. The DCS flight model, avionics code and sounds of the mod are **not** used.

## Aerofly FS 4 conversion, systems, displays, failures, flight tuning

**UkrAF**, developed with AI assistance (Claude). GPL version 3; sources in `source/` and `generator/`.

## Built on the Aerofly FS 4 F/A-18C

Flight model, flight control laws and avionics come from the stock F/A-18C of **IPACS** Aerofly FS 4, the engine
sounds from its stock F-15E. None of those files is distributed here: the installer builds the F-22's configuration
from the F/A-18 in the user's own game and copies the F-15E's engine sounds from it. Aerofly FS is a product of
IPACS; this add-on is not affiliated with or endorsed by IPACS.

## Tools

- Blender (https://www.blender.org/)
- IPACS Aerofly FS 4 Aircraft Converter and SDK documentation
- Python (https://www.python.org/): the Windows embeddable package in the folder `python` (unchanged, PSF License,
  its licence text: `python/LICENSE.txt`) runs the installer on Windows
- io_EDM, a Blender importer for DCS model files — Copyright (c) 2016 Nicholas Devenish and contributors, MIT
  licence (not part of this package)

## References for the added parts

Dimensions of the AIM-120C, AIM-9X and the 600 gal tank were measured from public images (Wikimedia Commons, public
domain / CC; USAF fact sheets; designation-systems.net; The War Zone). Cockpit sounds other than the F/A-18's are
synthesised by our own script, except the damage sounds (below).

## Damage sounds

The sounds of a gear leg breaking, the airframe sliding on the runway, an engine seizing, a tyre bursting and a
compressor stall are built by our script (`source/aircraft/f22/make_damage_sounds.py`) from field recordings on
Freesound (https://freesound.org), all released under CC0 (public domain dedication) - thank you to their authors:

- "Car Crash_EXT.wav" by PauliusI (freesound.org/s/346299)
- "kettlebell on concrete rock stone metal drag impact.wav" and "kettlebell concrete drag metal rock stone earth.wav"
  by rsellick (freesound.org/s/545544, freesound.org/s/545562)
- "crowbar metal drag on concrete scrape and handling.wav" and "metal gate open with anchor bar drag on concrete loud
  scrape and drop down hit resonate.flac" by kyles (freesound.org/s/452587, freesound.org/s/450356)
- "BOOMING PUNCHY EXPLOSION - close, big SCHOEPS MK41.wav" by misosound (freesound.org/s/251759)
- "Mossberg 500A - 1 shot and pump" by AnthonyChan0 (freesound.org/s/159710)

## Voice warnings

Spoken with Kokoro-82M (https://huggingface.co/hexgrad/Kokoro-82M, model under the Apache License 2.0), voice
`af_heart`, passed through our intercom filter (`source/aircraft/f22/make_voices_kokoro.py`).

## Names

F-22 and Raptor are names of Lockheed Martin; they are used here only to name the aircraft that is depicted. This is
a fan-made, non-commercial add-on.
