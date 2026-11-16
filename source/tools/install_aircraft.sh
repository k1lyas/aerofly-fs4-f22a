#!/bin/bash
# Assemble a converted Aerofly FS 4 aircraft and install it into the user aircraft folder.
#
#   install_aircraft.sh <src_dir> <converted_dir> <new_name> [display_name]
#
#   src_dir        source aircraft folder (text .tmc/.tmd configs)
#   converted_dir  converter output (.tmb/.ttx/.tsb)
#   new_name       folder/file base name in the game (must not clash with stock aircraft)
#   display_name   optional DisplayName / DisplayNameFull override
set -euo pipefail

SRC="$1"; CONV="$2"; NEW="$3"; DISPLAY="${4:-}"
OLD="$(basename "$SRC")"
GAME_USER="$HOME/Library/Application Support/Aerofly FS 4/aircraft"
STOCK="$HOME/Library/Application Support/Steam/steamapps/common/Aerofly FS 4 Flight Simulator/aircraft"

[ -d "$STOCK/$NEW" ] && { echo "name '$NEW' clashes with a stock aircraft"; exit 1; }
pgrep -xq "Aerofly FS 4" && { echo "close Aerofly FS 4 first"; exit 1; }

STAGE="$(mktemp -d)"
cp -R "$CONV/." "$STAGE/"
# text configs are not copied by the converter; model.tmc is converter-only
for f in "$SRC"/*.tmc "$SRC"/*.tmd; do
    [ "$(basename "$f")" = "model.tmc" ] && continue
    cp "$f" "$STAGE/"
done
# repaint/add-on descriptions (<src>/<sub>/option.tmc, add-on parameters/system.tmd) are text too
for f in "$SRC"/*/option.tmc "$SRC"/*/*.tmd; do
    [ -e "$f" ] || continue
    d="$(basename "$(dirname "$f")")"; mkdir -p "$STAGE/$d"; cp "$f" "$STAGE/$d/"
done
# rename <old>*.ext -> <new>*.ext (tmb/tmc/tmd follow the folder name)
for f in "$STAGE/$OLD".* "$STAGE/$OLD"_*; do
    [ -e "$f" ] || continue
    b="$(basename "$f")"; mv "$f" "$STAGE/$NEW${b#"$OLD"}"
done
if [ -n "$DISPLAY" ]; then
    sed -i '' -E "s#(<\[string8\]\[DisplayName(Full)?\]\[)[^]]*#\1$DISPLAY#" "$STAGE/$NEW.tmc"
fi

mkdir -p "$GAME_USER"
if [ -d "$GAME_USER/$NEW" ]; then
    /usr/bin/trash "$GAME_USER/$NEW"   # previous build goes to Trash, not deleted
fi
mv "$STAGE" "$GAME_USER/$NEW"
chmod 755 "$GAME_USER/$NEW"
echo "installed: $GAME_USER/$NEW ($(du -sh "$GAME_USER/$NEW" | cut -f1))"
