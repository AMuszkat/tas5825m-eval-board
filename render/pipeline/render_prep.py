"""Render copy of the TAS5825M board.  Run with the system Python (pcbnew):

    /usr/bin/python3 render_prep.py <project dir> <generated models dir> <out dir>

Copies the board and its 3dmodels/ into <out dir> and changes the COPY only:
  - Cvdd's pads shrink to 0.89 x 0.69 mm (at 0.9 x 0.7 KiCad's GLB export
    drops the solder mask there);
  - the 4 unnamed mounting-hole footprints get the M3 x 10 nylon standoff;
  - U1 (MP2269GD, no vendor model) gets a 2 x 3 x 0.9 mm body; height ASSUMED.
Writes <out dir>/render_info.json (mounting-hole centres, mm, KiCad frame) for
the Blender scene.  The source project is never written.
"""
import json
import shutil
import sys
from pathlib import Path

import pcbnew

src, gen, out = (Path(a).resolve() for a in sys.argv[1:4])
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)
shutil.copytree(src / "3dmodels", out / "3dmodels")
for f in gen.glob("*.step"):
    shutil.copy(f, out / "3dmodels" / f.name)
for f in src.glob("tas5825m_eval.kicad_p*"):
    if f.suffix in (".kicad_pcb", ".kicad_pro"):
        shutil.copy(f, out / f.name)

pcb = out / "tas5825m_eval.kicad_pcb"
board = pcbnew.LoadBoard(str(pcb))


def model(path):
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = path
    return m


done = {"Cvdd": 0, "standoff": 0, "U1": 0}
holes = []
for fp in board.GetFootprints():
    ref = fp.GetReference()
    if ref == "Cvdd":
        for pad in fp.Pads():
            pad.SetSize(pcbnew.F_Cu, pcbnew.VECTOR2I(pcbnew.FromMM(0.89), pcbnew.FromMM(0.69)))
        done["Cvdd"] += 1
    elif ref == "" and len(fp.Pads()) == 1 and fp.Pads()[0].GetDrillSize().x == pcbnew.FromMM(3.0):
        fp.Models().clear()
        fp.Models().push_back(model("${KIPRJMOD}/3dmodels/standoff_m3x10.step"))
        done["standoff"] += 1
        holes.append([pcbnew.ToMM(fp.GetPosition().x), pcbnew.ToMM(fp.GetPosition().y)])
    elif ref == "U1":
        fp.Models().clear()
        fp.Models().push_back(model("${KIPRJMOD}/3dmodels/u1_body.step"))
        done["U1"] += 1

if done != {"Cvdd": 1, "standoff": 4, "U1": 1}:
    sys.exit(f"render_prep: unexpected board contents: {done}")
board.Save(str(pcb))
(out / "render_info.json").write_text(json.dumps({"holes": holes}))
print("render copy:", pcb, done)
