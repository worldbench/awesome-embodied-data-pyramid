#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
SRC_ROOT="${SRC_ROOT:?Set SRC_ROOT to the ABC-130k source}"
OUTPUT_BASE="${OUTPUT_BASE:?Set OUTPUT_BASE to a new destination}"
WORK_ROOT="${WORK_ROOT:-${OUTPUT_BASE}/.abc130k_fast}"
WORKERS="${WORKERS:-8}"
EPISODES_PER_TASK="${EPISODES_PER_TASK:-16}"
export FFMPEG_BIN="${FFMPEG_BIN:-ffmpeg}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export ENCODER_THREADS="${ENCODER_THREADS:-1}" ENCODER_QUEUE="${ENCODER_QUEUE:-8}"
[[ "${MODE:-}" == full ]] || { echo 'Set MODE=full explicitly; this launcher converts train AND val.'; exit 2; }
FFMPEG_BIN="$(command -v "$FFMPEG_BIN")"
[[ -x "$FFMPEG_BIN" ]] || { echo "Missing executable: $FFMPEG_BIN"; exit 2; }
mkdir -p "$WORK_ROOT"
exec 9>"$WORK_ROOT/run.lock"
flock -n 9 || { echo 'Another ABC fast run holds the lock.'; exit 2; }
for split in train val; do
    output="$OUTPUT_BASE/ABC-130k-$split"
    work="$WORK_ROOT/$split"
    if [[ -f "$work/FINALIZED" && -f "$output/meta/info.json" ]]; then
        echo "Already finalized: $output"
        continue
    fi
    if [[ -f "$output/meta/info.json" ]]; then
        if [[ "${RESUME_AGGREGATION:-0}" == 1 && -d "$work/logs/completions" ]]; then
            "$PYTHON_BIN" - "$output" <<'PYBACKUP'
from pathlib import Path
import sys,time
p=Path(sys.argv[1]);backup=p.with_name(p.name+f".partial_aggregate_backup_{time.time_ns()}")
p.rename(backup)
print(f"Preserved unfinished aggregation: {backup}")
PYBACKUP
        else
            echo "Refusing to overwrite existing dataset/unfinished aggregation: $output. Inspect before retrying."
            exit 2
        fi
    fi
    mkdir -p "$work"
    "$PYTHON_BIN" -u "$SCRIPT_DIR/abc_mcap_fast.py" \
        --src-root "$SRC_ROOT" --output-path "$output" \
        --work-dir "$work/extract" --split "$split" \
        --workers "$WORKERS" --episodes-per-task "$EPISODES_PER_TASK" \
        --resume-dir "$work/logs" --keep-temp --missing-ee-policy fill
    touch "$work/FINALIZED"
    echo "Finalized: $output (check *_reports for skipped episodes; temporary shards retained)"
done
