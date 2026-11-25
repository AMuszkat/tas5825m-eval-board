# Overlap toolkit — detectors, their fields, and the moves

Companion to the `schematic-readability` skill. Every tool below is Konnect MCP;
load `sch_analysis` + `sch_components` (+ `sch_wiring`, `sch_batch` to fix).

## Detectors and what each field means

### `check_schematic_overlaps`
```jsonc
{
  "bounds_resolved": 66,          // symbols whose library geometry resolved
  "bounds_unresolved": [],        // refs that fell back to origin — their pairs are unreliable
  "overlap_count": 21,
  "overlaps": [{
    "a": "Cd0A", "b": "Cd0B",
    "type": "component_overlap",  // or a label-conflict type
    "detection": "symbol_geometry",
    "unit_a": 1, "unit_b": 1,
    "overlap_x_mm": 9.144, "overlap_y_mm": 0.2547,
    "bounds_a": {"x_min": 235.712, "x_max": 244.856, "y_min": 130.556, "y_max": 142.241},
    "bounds_b": { ... }
  }]
}
```
- `overlap_x_mm`/`overlap_y_mm` = the intersection size. Small overlap in **one
  axis only** (e.g. 9.14 × 0.25) is two parts in a row whose courtyards just
  touch — usually cosmetic; a substantial overlap in **both** axes is a real
  pile-up.
- Power symbols (`#PWR…`) overlapping a connector body is common and often
  harmless if the arrow sits outside the drawn body — check the render.
- Excludes free text. Not sufficient on its own.
- `tolerance` (default 0.5 mm) affects label-collision grouping and the origin
  fallback.

### `get_schematic_layout`
Compact spatial summary: component positions and transformed drawing/pin bounds
per symbol, plus (optionally) wires and labels. Use it to find free space and to
see which parts are neighbours before you move anything.

### `get_schematic_pin_locations`
Per pin: schematic-space `x`/`y`, `orientation_degrees` (direction leading
**away** from the symbol body, 0 = east), `length_mm`. The label rotation you
want at a pin is the pin's `orientation_degrees`.

### `export_schematic_svg`
`kicad-cli` writes each string twice: visibly as stroke paths, and again as an
invisible `<text opacity="0" x=… y=… textLength=… font-size=… text-anchor=…>`.
That second copy is a machine-readable text-geometry layer — the only way to
measure text collisions without pixels. Pair it with symbol `bounds_*` from
`check_schematic_overlaps`.

### `render_schematic_png`
`inline: true` returns the PNG base64 so you actually see it. `width_px` up to
4096; 3200+ is needed to read crowded refdes text.

## The moves

| Tool | Touches | Safe on wired sheets? |
|---|---|---|
| `reset_schematic_field_positions` | Ref/Value/field text only | **Yes** |
| `rotate_schematic_label`, `batch_rotate_labels` | label text + rotation | **Yes** |
| `move_labels_by_offset` | all labels of one net | **Yes** |
| `bulk_move_schematic_components` | symbol positions (uniform dx/dy) | No — wires stay |
| `move_schematic_component` | one symbol | No — wires stay |
| `move_region` | every symbol in a bbox | No — wires stay |
| `set_schematic_page` | paper size/orientation | Yes |
| `edit_schematic_component` / `batch_edit_schematic_components` | field values (and custom props) | Yes |
| `add_schematic_text` | free annotation | Yes |

### `reset_schematic_field_positions`
```
{ schematic, references?: ["U2", "C14"], dry_run?: true }
```
Omit `references` for the whole sheet. Moves each Reference/Value back to the
library anchor, carried through the symbol's rotation. Run `dry_run: true`
first to see the list. This is the correct first move on a text-cluttered sheet.

### Grid arithmetic
```
x = round(x / 1.27) * 1.27
y = round(y / 1.27) * 1.27
```

## Worked pattern — a decoupling row

A row of caps whose Values/tolerances overlap, wires intact:
1. `check_schematic_overlaps` → note which caps actually intersect (often only
   the courtyards, which is fine).
2. `render_schematic_png { inline: true, width_px: 3200 }` → the overlap is text.
3. `reset_schematic_field_positions { references: [caps] }`.
4. Still crowded → move alternate caps down/up **only in the unused margin**, or
   widen the row with `bulk_move_schematic_components` on the far group and
   re-wire; keep 1.27 mm.
5. Verify with the `schematic-verify` skill.

## Gotchas learned on this project

Hard-won, verified against these sheets — read before running a pass.

### `reset_schematic_field_positions` touches power symbols

Omit `references` and it resets **every** symbol, including the `#PWR…` power
symbols. Their Reference/Value normally sit *inside* the symbol graphic
(effectively invisible); the reset moves them *outside*, so the sheet suddenly
shows a small `GND` / `AGND` / `#PWR00011` next to every ground and rail. This
is a visible regression.

**Always pass an explicit `references` list of real components** (everything not
starting with `#PWR`). Get the list from `list_schematic_components`:

```jsonc
{"tool":"reset_schematic_field_positions",
 "args":{"schematic":"…","references":["U2","Cdig","Cgvdd", /* … */]}}
```

### It rewrites symbol instances (large, lossy-looking diff)

The rewrite drops `(body_style N)` and `(in_pos_files yes)` from each instance.
KiCad re-defaults them on load and the design is unaffected (exports, ERC and
connectivity are unchanged), but `git diff` shows thousands of lines — do not
read it as damage, and never hand-edit `.kicad_sch` to "restore" them.

### Field text inherits the symbol's rotation

Reset anchors Reference/Value along the symbol's own axis. On a 90°-rotated part
(most vertical capacitors here) the ref/value come out **vertical**. That is
collision-free but reads bottom-to-top; on some sheets it is a wash. There is no
tool to set a field's position to an arbitrary horizontal spot — reset is the
only lever, so accept the rotation or restructure the sheet.

### Clutter reset cannot fix

- Pin **name** text colliding because two pins are adjacent on a small symbol
  body (e.g. the LPC11U68 and TAS5825M pin fans) — a symbol-library geometry
  problem, not a field-position one.
- A symbol's Value and a custom field both anchored at the same place
  (e.g. `SW_MCU_RESET` shows `B3S-1000` over `Cap`).
- Extra visible custom fields (`X7R`, `50V`, `0402`, `1%`) — these are *useful*
  info; the goal is to space them, not hide them.

## Baseline numbers for this project (do not regress these)

Measured before any cleanup; a readability pass must not make them worse.

| Check | root | AMP_CH1 | MCU |
|---|---|---|---|
| `check_schematic_overlaps` (symbol level) | 4 | 21 | 0 |
| `find_orphan_items` | 0 | 2 dangling wire ends | 1 unconnected pin (`ULDO` pin 4, NC) |
| `run_erc` (on the root) | 13 errors, 435 total | — (hierarchy-wide) | — |

## Worked pattern — labels across pin names

1. `get_schematic_pin_locations { reference }` → read `orientation_degrees`.
2. `rotate_schematic_label { net, x, y, rotation = orientation_degrees }` for a
   single label, or `batch_rotate_labels` for a fan-out.
3. Re-render; the text should now read away from the body.
