# TAS5825M evaluation board — working notes

Evaluation board for the **TAS5825M** Class-D audio amplifier (thermal-benchmark
focus). KiCad 10 project, hierarchical schematic.

## Hard rule: never hand-edit KiCad files

`.kicad_sch`, `.kicad_pcb`, `.kicad_pro`, `.kicad_prl`, `.kicad_sym`,
`.kicad_mod` and `sym-lib-table` are serialized object graphs with UUIDs and
cross-references. A text edit corrupts them.

**Every change goes through the Konnect MCP server** (registered in `.mcp.json`;
`.claude/settings.json` also denies `Edit` on those paths as a backstop). See the
global `konnect` skill for the full operating rules. Reads for analysis are fine
(exported netlist/PDF/SVG, or `kicad-cli`), editing is not.

## Project layout

| Path | What |
|---|---|
| `tas5825m_eval.kicad_sch` | Root sheet: headers, buck regulator, output connectors, PVDD decoupling |
| `tas5825m_eval_mcu.kicad_sch` | Sub-sheet **MCU** — LPC11U68, USB, reset/clock, 3V3 LDO |
| `tas5825m_eval_amp.kicad_sch` | Sub-sheet **AMP_CH1** — TAS5825M, output filter, I2C address straps |
| `tas5825m_eval_main/amp/mcu.kicad_sym` | The three project symbol libraries (see `sym-lib-table`) |
| `tas5825m_eval.kicad_pcb` | Board |
| `render/pipeline/` | Blender/3D hero-render pipeline |
| `schematic/` | Exported schematic PDF |

Symbols come from the **project libraries**, not stock KiCad — search those first
(`tas5825m_eval_amp:*`, etc.) before reaching for `Device:*`.

## Current focus: schematic readability

The sheets render correctly and net up, but they are **not pleasant to read**:
component References, Values and extra field text pile on top of each other,
labels run back across pin names, and a number of symbol bodies crowd their
neighbours.

Use the **`schematic-readability`** skill to diagnose and fix this, and the
**`schematic-verify`** skill after every pass. `/tidy-schematic` runs the whole
loop on one sheet.

Measured starting point (Konnect `check_schematic_overlaps`, symbol-body level):

| Sheet | Symbol overlaps |
|---|---|
| root | 4 |
| AMP_CH1 | 21 |
| MCU | 0 (text-only problem — fix via field positions) |

## Every session

1. `load_toolset` the schematic toolsets you need — `list_toolboxes` first.
2. Take a checkpoint before a batch of edits: `snapshot_project` and
   `set_visual_baseline`.
3. Look at the sheet — `render_schematic_png` with `inline: true` — before and
   after. Geometry checks do not catch text collisions.
4. Never move a **wired** symbol casually: `move_schematic_component` moves the
   symbol and leaves its wires behind. Prefer field/label moves, or re-verify
   connectivity afterwards.
5. Run ERC on the **root** schematic only — `run_erc` rejects a sub-sheet and ERC
   covers the whole hierarchy anyway.
6. Undo is `git checkout -- <sheet>.kicad_sch`: the schematics are tracked, and
   Konnect rewrites produce a huge normalized diff you should not hand-edit.

## Conventions

- **1.27 mm grid**, always — off-grid pins break wire connections silently.
- Rails as **power symbols** (`add_power_symbol`), named signals as **net labels**.
- Label rotation follows the pin's `orientation_degrees` (from
  `get_schematic_pin_locations`) or the text reads back over the symbol.
- Keep changes scoped to one sheet and verify before moving on.
