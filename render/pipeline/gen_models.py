"""Render-only STEP models, made with CadQuery.

    ~/miniforge3/bin/python gen_models.py <out dir>

standoff_m3x10.step  M3 x 10 nylon hex standoff, 5.5 mm across flats, hanging
                     from the board's underside (model z 0 = board top, so the
                     body spans z -1.6 .. -11.6 with no offset needed).
u1_body.step         MP2269GD body: 2.0 x 3.0 mm, 0.9 mm high (ASSUMED height).

Each solid is named with a material prefix (NYLON_ / EPOXY_) that the Blender
scene reads.  Every file is re-imported and must come back as one valid,
non-empty solid: KiCad's GLB export silently skips a model it cannot read.
"""
import sys
from pathlib import Path

import cadquery as cq

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
BOARD = 1.6


def standoff():
    af, length, bore = 5.5, 10.0, 2.6
    z0 = -BOARD - length
    hexa = (cq.Workplane("XY").workplane(offset=z0)
            .polygon(6, af / 0.8660254).extrude(length).edges("|Z").fillet(0.25))
    turned = (cq.Workplane("XY").workplane(offset=z0).circle(af / 0.8660254 / 2).extrude(length)
              .faces(">Z or <Z").chamfer(0.45))         # the turned chamfer at each end
    hole = cq.Workplane("XY").workplane(offset=z0 - 1).circle(bore / 2).extrude(length + 2)
    return hexa.intersect(turned).cut(hole)


def u1():
    w, l, h = 2.0, 3.0, 0.9
    body = (cq.Workplane("XY").workplane(offset=0.02).rect(w, l).extrude(h)
            .edges("|Z").fillet(0.05).faces(">Z").edges().fillet(0.04))
    dimple = cq.Workplane("XY").workplane(offset=0.02 + h).center(-0.55, 1.05).circle(0.14).extrude(-0.03)
    return body.cut(dimple)


def write(name, part, label, colour):
    path = out / name
    asm = cq.Assembly(name=label.split("_")[0])
    asm.add(part, name=label, color=cq.Color(*colour))
    asm.save(str(path), exportType="STEP")
    back = cq.importers.importStep(str(path))
    solids = back.solids().vals()
    vol = sum(s.Volume() for s in solids)
    if not solids or vol <= 0 or not all(s.isValid() for s in solids):
        sys.exit(f"{name}: re-import is not a valid solid (solids={len(solids)}, volume={vol})")
    print(f"{name}: {len(solids)} solid(s), {vol:.2f} mm3")


write("standoff_m3x10.step", standoff(), "NYLON_standoff", (0.93, 0.92, 0.88))
write("u1_body.step", u1(), "EPOXY_u1", (0.04, 0.04, 0.045))
