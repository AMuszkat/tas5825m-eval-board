---
name: schematic-readability
description: >
  Make a KiCad schematic readable by finding and fixing overlaps and text
  collisions — symbol bodies crowding neighbours, Reference/Value/field text
  piled on top of each other, labels running back across pin names. Triggers
  on: "schematic is unreadable", "things overlap", "overlapping symbols",
  "text collision", "tidy the schematic", "de-overlap", "make the schematic
  readable", "labels overlap", "values overlap", "clean up the schematic".
  Works on this project through the Konnect MCP server only.
argument-hint: "[sheet or area, e.g. AMP_CH1 | root | MCU]"
---

# Schematic readability — de-overlap and legibility

Goal: a person opening the sheet sees every part, value and net without two
strings or two bodies landing on each other. Connectivity is already correct —
this skill changes **layout and text placement only**, through Konnect MCP tools.

Read `.claude/CLAUDE.md` for the project map. Never edit `.kicad_sch` by hand.

## 0. Load toolsets

```
load_toolset(["sch_analysis", "sch_components"])   # diagnose
load_toolset(["sch_wiring", "sch_batch", "sch_export"])   # fix + verify
```

`list_toolboxes` first if unsure; `get_active_toolsets` to see what is loaded.

## 1. Diagnose — three layers, in order

Overlap has three distinct causes and each has its own detector. Do all three;
fixing one layer leaves the others visible.

**a. Symbol bodies** (a part physically sitting on another):

```
check_schematic_overlaps { schematic }
```
Returns `overlap_count` and, per pair, both refs, both bounds (`x_min/x_max/
y_min/y_max`), the overlap in mm and the detection method. `bounds_unresolved`
is normally empty — if not, that symbol fell back to its origin and its pairs
are suspect. This check **excludes free text**, so a clean result here does not
mean the sheet is readable (the MCU sheet is 0 and still cluttered).

**b. Text** (References, Values, extra fields, labels). No MCP tool measures
text boxes, so use both of these:

```
render_schematic_png { schematic, inline: true, width_px: 3200 }
export_schematic_svg { schematic, output }   # geometry source
```
`export_schematic_svg` writes every string a **second time** as an invisible
`<text opacity="0">` element carrying `x`, `y`, `textLength`, `font-size` and
`text-anchor`. Diff those boxes against each other and against the symbol bounds
from step (a) to find collisions precisely; `render_schematic_png` inline lets
you *look* at the result. Do both — the SVG tells you where, the image confirms.

**c. Spatial context** — who is near whom, what is free space:

```
get_schematic_layout { schematic, include_wires: true, include_labels: true }
get_schematic_pin_locations { schematic, reference }   # pin coords + orientation_degrees
```

## 2. Fix — safest move first

Stop as soon as the sheet reads cleanly; do not restyle for its own sake. Work
top-to-bottom in this order because each step is more destructive than the last.

### 2.1 Reset field text (non-destructive, biggest win)

Ref/Value/field text a previous editor dragged off the library anchor is the
usual cause of piled-up strings — and the MCU sheet's whole problem.

```
reset_schematic_field_positions { schematic, dry_run: true }        # preview
reset_schematic_field_positions { schematic }                        # apply
```
Omit `references` to do the whole sheet, or pass a list to work in batches.
Fields a symbol's library gives no anchor for are left alone. Re-render and
look; a handful of parts will still need attention.

### 2.2 Move labels (non-destructive)

Labels crossing pin names or each other:

```
rotate_schematic_label { schematic, net, x, y, rotation }   # rotation from orientation_degrees
batch_rotate_labels    { schematic, labels: [{net, x, y, rotation}, ...] }
move_labels_by_offset  { schematic, net, dx, dy }
```
Take the rotation from the pin's `orientation_degrees` (0 = east) so the text
reads **away** from the symbol body. This is the fix for a label whose text
runs back across the pin names.

### 2.3 Move symbols into free space (destructive to wiring — read first)

`move_schematic_component` / `bulk_move_schematic_components` / `move_region`
move the symbol **and leave every connected wire where it is**. On a fully wired
sheet that silently opens circuits. So:

- Prefer moving a symbol that has **no wires** (a free-standing connector row),
  or a whole cluster where you will re-wire.
- Prefer `bulk_move_schematic_components` for a uniform shift of a group.
- `move_region` shifts every symbol inside a bounding box by one offset — good
  for opening a gap between two blocks.
- Afterwards the junctions are re-judged for you, but **wires are not
  stretched**: expect to re-run wiring (`connect_pins` / `connect_to_net`) and
  to run `fix_connectivity` + `validate_wire_connections`.

Keep every new position on the **1.27 mm grid**:
`x, y = round(v / 1.27) * 1.27`.

### 2.4 Last resorts

- `set_schematic_page { schematic, size }` — a genuinely over-full sheet. A page
  that is too small is a silent defect (content outside the frame still nets up).
- Reduce clutter by turning a symbol's extra display field off, or move it with
  `edit_schematic_component { fields: {...} }` / `batch_edit_schematic_components`.
- `add_schematic_text` for a section title where a block needs a label.

## 3. Verify every pass — do not skip

```
check_schematic_overlaps { schematic }          # symbol level back to 0
find_orphan_items { schematic }                 # no new floating ends
validate_wire_connections { schematic }         # wires still land on pins
run_erc { schematic }                           # no new electrical errors
render_schematic_png { schematic, inline: true } # LOOK at it
```
`compare_visual_baseline { schematic }` reports drift against the render you
stored with `set_visual_baseline` before the pass, with a changed-region box —
use it to confirm the edit did what you meant and nothing else moved.

See the **`schematic-verify`** skill for what each check must return and how to
read a failure. A pass is done only when the sheet renders clean **and** the
connectivity checks are as clean as before the pass.

## Guardrails

1. Never edit KiCad files directly — MCP only.
2. One sheet per pass; verify before moving to the next.
3. Never guess a pin number or grid position — query it.
4. Do not move a wired symbol without repairing its wires.
5. Connectivity before beauty: if a check regresses, revert the step, do not
   paper over it.
6. Checkpoint before a batch: `snapshot_project`, `set_visual_baseline`.

`references/overlap-toolkit.md` has the tool-by-tool recipe and the field
semantics for each detector.
