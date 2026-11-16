#!/bin/bash
# F-22A (DCS mod by Grinnelli Designs, GPL-3 -> Aerofly FS 4, physics/systems donor: stock F/A-18). Status: README.md.
#
#   ./build.sh            import -> measure -> export (parts, textures) -> animation tables -> previews -> configs ->
#                         converter (one start; user presses Convert) -> install
#   ./build.sh export     export + animation tables + configs (geometry / texture changes, then ./build.sh convert)
#   ./build.sh bake       bake the cockpit ambient occlusion / flood light / wear maps into work/bake (Cycles, ~35 min;
#                         after cockpit geometry or flood lamp changes, then ./build.sh export)
#   ./build.sh configs    regenerate .tmd/.tmc only and copy them into the game (no converter)
#   ./build.sh convert    converter + install only
#   ./build.sh install    install the last converted aircraft + donor sounds
set -euo pipefail
cd "$(dirname "$0")"
NAME=f22
SRC="$PWD/source"
EDM="$SRC/Shapes/F-22A.EDM"
DONOR="$HOME/Library/Application Support/Steam/steamapps/common/Aerofly FS 4 Flight Simulator/aircraft/f18"
DONOR_LABEL=F/A-18
DONOR_FILES="display_source_light.ttx"   # F/A-18 LCD digits (UFD engine numbers, fuel, clock)
EXTRA_WAVS="$PWD/sounds/cockpit"       # own cockpit sounds, make_cockpit_sounds.py: the converter makes the .tsb
LIVERY_DIR="$SRC/Liveries/${LIVERY:-Default}"
TEX_DIRS=("$SRC/Textures/F-22A" "$SRC/Textures/F-22A_Cockpit")
POSE_ARGS="0=1,3=1,5=1"
COCKPIT_EDM="$SRC/Cockpit/Shape/Cockpit_F-22A.EDM"
COCKPIT_OFFSET="6.958,0,1.36"     # Views.lua CockpitLocalPoint {6.958, 1.36, 0} (DCS y up)
source "$(cd ../.. && pwd)/tools/build_lib.sh"
