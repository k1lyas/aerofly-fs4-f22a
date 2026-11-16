# Sources of the F-22A add-on (GPL-3)

The part we wrote, as the GPL asks for with every copy: the scripts that turn the original model into the files in
`../aircraft/f22`, the configuration generator, the sound scripts and the release tooling. Only what the build uses.

- `aircraft/f22/build.sh`, `tools/build_lib.sh` - the build: import of the DCS model into Blender, export of parts and
  textures (`ac_f22.py`, `tools/export_parts.py`, ...), the IPACS Aircraft Converter, installation. Written for macOS
  with Blender and the converter under CrossOver; paths are at the top of the two scripts. The converter also wants a
  `build/config.tmc` naming your output folder (see the IPACS aircraft SDK).
- `aircraft/f22/make_f22.py` and the modules it imports - the configuration generator (the copy the installer runs is
  in `../generator/`).
- `aircraft/f22/make_cockpit_sounds.py`, `make_voices_kokoro.py`, `mfd_pages.py` - cockpit sounds, voice warnings,
  the still pictures of the screens.
- `aircraft/f22/make_release.py`, `tools/clean_check.py` - release packaging and the check that no IPACS file is in a
  package. The installer and the documents it packs are the files at the top of this package.

Not here: the original model (EDM files and textures of the Grinnelli Designs F-22A mod, GPL-3): https://github.com/grinnellidesigns/f-22a ;
the Blender importer io_EDM (MIT): https://github.com/ndevenish/Blender_ioEDM and its forks; Blender; the IPACS
Aircraft Converter; the game.
