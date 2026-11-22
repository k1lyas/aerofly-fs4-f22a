# Shared build steps for an aircraft port (sourced by aircraft/<name>/build.sh after it sets its parameters):
#   NAME        aircraft name = folder / file base name in the game (su35, f22)
#   SRC         mod folder (aircraft/<name>/source/<mod>)          EDM        model file (.edm)
#   DONOR       stock aircraft folder used as physics/systems donor DONOR_LABEL  name for messages
#   LIVERY_DIR  livery textures (looked up first)                  TEX_DIRS   array of further texture folders
#   POSE_ARGS   EDM argument pose for the export (gear down: "0=1,3=1,5=1")
#   COCKPIT_EDM, COCKPIT_OFFSET (optional) separate DCS cockpit model and its CockpitLocalPoint (Aerofly x,y,z)
#   DONOR_FILES (optional) further donor files installed with the configs (sprite textures ...)
# Layout under aircraft/<name>/: source/ work/ build/<name>/ converted/ logs/  (see README.md, docs/PORTING_GUIDE.md)
A="$PWD"
W="$(cd ../.. && pwd)"
T="$W/tools"
B=/Applications/Blender.app/Contents/MacOS/Blender
IOEDM="$T/ioEDM_dart/io_EDM"
TEXALL="$A/source/tex_all"
I="$A/work"
BD="$A/build/$NAME"                        # converter model folder (build/config.tmc names the output folder)
OUT="$A/converted/aircraft/$NAME"
LOG="$A/logs/convert.log"
GAME_AC="$HOME/Library/Application Support/Aerofly FS 4/aircraft/$NAME"
CX=/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin
CONV='C:\users\crossover\AppData\Local\Programs\Aerofly FS 4 Aircraft Converter'
export AC="ac_$NAME" AC_DIR="$A"

# One converter start per build. Killing the converter (it can hang on the preview render under CrossOver)
# used to leave Wine services of the bottle running, and the next start then ignored the Convert button. So the
# whole bottle is shut down cleanly (wineserver -k) before the start and after the conversion.
# converted/aircraft/<name> is kept: the converter then only redoes changed files and skips the preview render.
stop_bottle() {
    # the whole bottle, not only the converter: services, explorer, rpcss and the wineserver itself. Started while they were still going down, the new converter
    # hung and ignored the Convert button (wineserver -k returns at once)
    local bottle='winewrapper|bin/wineserver|C:.windows.system32|aerofly_fs_4_aircraft_converter'
    pkill -f aerofly_fs_4_aircraft_converter || true
    WINEPREFIX="$HOME/Library/Application Support/CrossOver/Bottles/Aerofly" "$CX/wineserver" -k 2>/dev/null || true
    for _ in $(seq 1 20); do
        pgrep -f "$bottle" >/dev/null || return 0
        sleep 1
    done
    pkill -9 -f "$bottle" || true    # left-over processes: force them down
    sleep 2
}

convert() {
    stop_bottle
    if [ -n "${EXTRA_WAVS:-}" ]; then cp "$EXTRA_WAVS"/*.wav "$BD/"; fi    # sounds beside the donor's, for the converter
    echo "== converter started - press Convert in its window (waiting up to 30 min)"
    # no audio device for the converter, it plays nothing: its sound init (tmsyssound_sl) is the known place where the window comes up with a dead Convert button
    ( WINEDLLOVERRIDES="mmdevapi=d" "$CX/wine" --bottle Aerofly --wait-children "$CONV\\bin64\\aerofly_fs_4_aircraft_converter.exe" "dir='$CONV'" \
        "model='Z:$(echo "$BD" | tr / '\\\\')'" > "$LOG" 2>&1 & )
    for i in $(seq 1 360); do
        grep -qE 'all done|converting done' "$LOG" 2>/dev/null && break
        # it can die at start-up under CrossOver (2026-11-21: 'vkAcquireNextImageKHR' assertion) - then say so, not wait 30 min
        if [ "$i" -gt 6 ] && ! pgrep -f aerofly_fs_4_aircraft_converter >/dev/null; then
            echo "converter exited without converting (crashed?), last log lines:"; tail -3 "$LOG"; break
        fi
        sleep 5
    done
    sleep 3
    stop_bottle
    grep -qE 'all done|converting done' "$LOG" || { echo "converter did not finish within 30 min"; exit 1; }
    echo "conversion done"
}

install() {
    stop_bottle
    grep -qE 'all done|converting done' "$LOG" || { echo "converter did not finish (no 'converting done' in "$LOG")"; exit 1; }
    if pgrep -f "Aerofly FS 4.app" >/dev/null; then echo "the game is running - close it, then: $0 install"; exit 1; fi
    "$T/install_aircraft.sh" "$BD" "$OUT" "$NAME"
    cp "$DONOR"/*.tsb "$GAME_AC/"
    donor_files
    stock_copies
    echo "installed with $DONOR_LABEL sounds"
}

stock_copies() {   # STOCK_COPIES: "f15e/jet_00.tsb:f15e_jet_00.tsb ..." - other stock aircraft's files the configs play
    local root; root="$(dirname "$DONOR")"
    for p in ${STOCK_COPIES:-}; do cp "$root/${p%%:*}" "$GAME_AC/${p##*:}"; done
}

donor_files() {    # DONOR_FILES: further donor files the configs read (e.g. display sprite textures)
    for f in ${DONOR_FILES:-}; do cp "$DONOR/$f" "$GAME_AC/"; done
}

configs() {
    (cd "$A" && PYTHONPATH="$T" python3 make_$NAME.py "$DONOR" "$BD/parts.json" "$I/geometry.json" "$I/anim.json" \
        "$I/anim_pivots.json" "$BD" && PYTHONPATH="$T" python3 make_${NAME}_meta.py "$DONOR" "$I/geometry.json" \
        "$BD/parts.json" "$BD" && python3 "$T/check_refs.py" "$BD/$NAME.tmd" | grep -E '^(Graphic|Sound|UNKNOWN|DYNAMICS READS)' || true)
}

# texture lookup folder: livery first, then the mod's base textures and cockpit textures (first name wins)
link_textures() {
    local X="$TEXALL" L="$LIVERY_DIR"
    [ -d "$X" ] && return
    mkdir -p "$X"
    for d in "$L" "${TEX_DIRS[@]}"; do
        find "$d" -type f \( -iname '*.dds' -o -iname '*.png' \) | while read -r f; do
            b=$(basename "$f")
            ls "$X" | tr 'A-Z' 'a-z' | grep -qx "$(echo "$b" | tr 'A-Z' 'a-z')" || ln -s "$f" "$X/$b"
        done
    done
}

import_measure() {
    mkdir -p "$I/renders" "$BD"
    link_textures
    echo "== import DCS EDM (gear down)"
    EDM_ARGS="$POSE_ARGS" EDM_ANIM_JSON="$I/anim_pivots.json" "$B" --background --factory-startup \
        --python "$T/edm_to_blend.py" -- "$IOEDM" "$EDM" "$TEXALL" \
        "$I/${NAME}_pose.blend" "$I/renders/pose" 2>&1 | grep -E 'created|Error|Traceback' || true
    echo "== measure"
    "$B" --background "$I/${NAME}_pose.blend" --python "$T/measure_parts.py" -- "$I/anim_pivots.json" "$I/geometry.json" \
        2>&1 | grep -E 'MEASURE wheel|Error|Traceback' || true
    if [ -n "${COCKPIT_EDM:-}" ]; then      # separate DCS cockpit model, merged after the measurements
        echo "== merge cockpit model"
        "$B" --background "$I/${NAME}_pose.blend" --python "$T/merge_cockpit.py" -- "$IOEDM" "$COCKPIT_EDM" "$TEXALL" \
            "$COCKPIT_OFFSET" 2>&1 | grep -E 'merged|sunk|clipped|Error|Traceback' || true
    fi
}

export_parts() {
    echo "== export parts + textures"
    rm -f "$BD"/*.png "$BD/$NAME.tgi"
    # (the exported triangles as a scene too: the selection previews are rendered from it - what the game draws)
    PREVIEW_BLEND="$I/${NAME}_exported.blend" "$B" --background "$I/${NAME}_pose.blend" --python "$T/export_parts.py" -- "$BD" "$I/geometry.json" \
        2>&1 | grep -E '^parts|textures written|WARNING|Error|Traceback' || true
    echo "== animation tables"
    COCKPIT_EDM="${COCKPIT_EDM:-}" COCKPIT_OFFSET="${COCKPIT_OFFSET:-}" \
        "$B" --background --factory-startup --python "$T/anim_tables.py" -- "$IOEDM" "$EDM" - \
        "$BD/parts.json" "$I/geometry.json" "$I/anim.json" 2>&1 | grep -E 'ANIM parts|Error|Traceback' || true
    holes_check
}

# Does the export show what DCS shows? Back faces are culled in the game, so both are viewed with culling (see
# docs/reference/FIGHTER_LESSONS.md section 2). HOLES should be about 0 (a few on glass / small objects are fine).
holes_check() {
    echo "== hole check (export vs DCS, culled)"
    AC="ac_$NAME" AC_DIR="$A" "$B" --background "$I/${NAME}_pose.blend" --python "$T/diag/cull_diff.py" -- "$BD/$NAME.tgi" 0.1 \
        2>&1 | grep -E '^(source:|export:|HOLES|FARTHER|source objects)|axis [-+][xyz]|Error|Traceback' || true
}

# cockpit ambient occlusion and flood light baked into texture space (ac BAKE_AO / BAKE_FLOOD; slow, Cycles): the maps
# stay in $I/bake and the export reads them - rerun only when the cockpit geometry or the lamps change
bake() {
    echo "== bake cockpit light"
    AC="ac_$NAME" AC_DIR="$A" "$B" --background "$I/${NAME}_pose.blend" --python "$T/bake_cockpit_light.py" -- "$I/bake" \
        2>&1 | grep -E '^BAKE|Error|Traceback' || true
}

previews() {
    # selection previews (as the SDK sample: 4096, nose left, framed) from the converted textures, one per repaint
    "$B" --background "$I/${NAME}_exported.blend" --python "$T/render_preview2.py" -- "$BD/preview_${NAME}.tif" "$BD" \
        2>&1 | grep -E 'PREVIEW|Error' || true
    for r in "$BD"/*/option.tmc; do
        [ -e "$r" ] || continue
        grep -q 'Type.*addon' "$r" && continue            # load add-ons have no selection preview
        "$B" --background "$I/${NAME}_exported.blend" --python "$T/render_preview2.py" -- "$(dirname "$r")/preview_${NAME}.tif" \
            "$BD" "$(dirname "$r")" 2>&1 | grep -E 'PREVIEW|Error' || true
    done
}

case "${1:-full}" in
full)
    import_measure
    export_parts
    previews
    echo "== configs"
    configs
    convert
    install
    ;;
import)
    import_measure
    ;;
export)
    export_parts
    configs
    ;;
configs)
    configs
    [ -d "$GAME_AC" ] || { echo "$NAME is not installed in the game yet - run ./build.sh convert"; exit 0; }
    # (copilot.tmc too: the game's own settings for the aircraft - takeoff trim, ratings - were copied only on install)
    for f in "$BD"/$NAME*.tmd "$BD/$NAME.tmc" "$BD/controls.tmd" "$BD/copilot.tmc"; do [ -f "$f" ] && cp "$f" "$GAME_AC/"; done
    stock_copies
    # repaint / load add-on folders: option.tmc and the add-on parameters.tmd / system.tmd
    for f in "$BD"/*/option.tmc "$BD"/*/*.tmd; do
        [ -e "$f" ] || continue
        d="$(basename "$(dirname "$f")")"; mkdir -p "$GAME_AC/$d"; cp "$f" "$GAME_AC/$d/"
    done
    donor_files
    echo "configs copied into $GAME_AC"
    ;;
bake)
    bake
    ;;
previews)
    previews
    ;;
convert)
    convert
    install
    ;;
install)
    install
    ;;
*) echo "usage: $0 [full|import|export|bake|configs|convert|install|previews]"; exit 1 ;;
esac
