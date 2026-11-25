#!/usr/bin/env bash
# The TAS5825M eval-board hero render, end to end.
#
#     render/pipeline/run.sh [--draft]
#
# Reads the KiCad project this folder sits in (never writes it), renders in a
# temp dir, and writes render/tas5825m_eval_hero.png (the master) and
# render/tas5825m_eval_hero_2400x1800.jpg (the published 4:3 crop).
# --draft: 2 MP, 64 samples, written to the temp dir only -- to judge a change.
#
# Needs: kicad-cli (KiCad 10), the system python3 with pcbnew, Blender >= 4.2
# (`blender` on PATH), and a Python with CadQuery + numpy + Pillow
# (CQ_PYTHON, default ~/miniforge3/bin/python).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
proj="$(cd "$here/../.." && pwd)"
py="${CQ_PYTHON:-$HOME/miniforge3/bin/python}"
draft=0; [ "${1:-}" = "--draft" ] && draft=1
work="$(mktemp -d "${TMPDIR:-/tmp}/tas5825m_render.XXXXXX")"
echo "work dir: $work"

"$py" "$here/gen_models.py" "$work/gen"
/usr/bin/python3 "$here/render_prep.py" "$proj" "$work/gen" "$work/board" 2>&1 | grep -v -E "assert|Font '"
kicad-cli pcb export glb -f -o "$work/board.glb" --subst-models --no-dnp --include-tracks \
  --include-pads --include-zones --include-silkscreen --include-soldermask \
  "$work/board/tas5825m_eval.kicad_pcb" | grep -v RWGltf_CafWriter

"$py" - "$work" "$draft" <<'PY'
import json, sys
work, draft = sys.argv[1], sys.argv[2] == "1"
holes = json.load(open(f"{work}/board/render_info.json"))["holes"]
job = {"glb": f"{work}/board.glb", "beauty": f"{work}/beauty.png", "matte": f"{work}/matte.png", "holes": holes}
if draft:
    job.update(px=2e6, samples=64, adaptive=0.03)
json.dump(job, open(f"{work}/job.json", "w"))
PY
blender -b --factory-startup --python "$here/scene.py" -- "$work/job.json" | grep -E "^(DEVICE|HIDDEN|ENIG|BEAUTY|MATTE)"

if [ "$draft" = 1 ]; then
  "$py" "$here/compose.py" "$work/beauty.png" "$work/matte.png" "$work/hero.png" --jpg "$work/hero_2400x1800.jpg"
  echo "draft: $work/hero_2400x1800.jpg"
else
  "$py" "$here/compose.py" "$work/beauty.png" "$work/matte.png" "$proj/render/tas5825m_eval_hero.png" \
    --jpg "$proj/render/tas5825m_eval_hero_2400x1800.jpg"
  rm -rf "$work"
fi
