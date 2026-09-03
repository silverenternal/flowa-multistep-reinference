#!/bin/bash
# Auto-install GenEval into geva_venv. Documented outcome in install.log.
set -u
GEVA_VENV=/home/hugo/codes/flowa-multistep-reinference/.venvs/geva_venv
LOG=$GEVA_VENV/logs/install.log
: > "$LOG"
echo "[geva-install] $(date -Is) start (pid=$$)" >> "$LOG"

cd /home/hugo/codes/flowa-multistep-reinference

echo "--- step 1: torch 2.7 + cu128 (matching hidream_venv) ---" >> "$LOG"
"$GEVA_VENV/bin/pip" install --quiet --index-url https://download.pytorch.org/whl/cu128 \
    torch==2.7.0 torchvision==0.22.0 >> "$LOG" 2>&1
echo "torch exit=$?" >> "$LOG"

echo "--- step 2: clone upstream geneval repo (depth=1) ---" >> "$LOG"
if [ ! -d "$GEVA_VENV/repo" ]; then
    git clone --depth 1 https://github.com/djghosh13/geneval.git "$GEVA_VENV/repo" >> "$LOG" 2>&1
    echo "git clone exit=$?" >> "$LOG"
fi

echo "--- step 3: minimal Python deps (numpy, pandas, open_clip_torch, einops) ---" >> "$LOG"
"$GEVA_VENV/bin/pip" install --quiet numpy pandas open_clip_torch einops >> "$LOG" 2>&1
echo "deps exit=$?" >> "$LOG"

echo "--- step 4: mmcv-full 1.7.2 (will likely fail on torch 2.7) ---" >> "$LOG"
timeout 480 "$GEVA_VENV/bin/pip" install --quiet mmcv-full==1.7.2 >> "$LOG" 2>&1
RC=$?
echo "mmcv-full exit=$RC" >> "$LOG"

echo "--- step 5: mmdet 2.28.2 (will fail if step 4 failed) ---" >> "$LOG"
timeout 480 "$GEVA_VENV/bin/pip" install --quiet mmdet==2.28.2 >> "$LOG" 2>&1
RC2=$?
echo "mmdet exit=$RC2" >> "$LOG"

echo "--- final state ---" >> "$LOG"
"$GEVA_VENV/bin/pip" list 2>/dev/null | grep -iE "torch|mmcv|mmdet|open_clip|pandas|numpy|einops" >> "$LOG"

echo "[geva-install] $(date -Is) done (mmcv_rc=$RC, mmdet_rc=$RC2)" >> "$LOG"