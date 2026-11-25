---
name: schematic-verify
description: >
  Verify a KiCad schematic after any edit: symbol-level overlap, orphaned
  wires/labels, wire-to-pin landing, ERC, and a visual render — and judge
  whether a change is done or must be reverted. Triggers on: "verify the
  schematic", "did that break anything", "check connectivity after the edit",
  "run ERC", "validate the schematic", "is the sheet still clean", "regression
  check". Project-scoped; Konnect MCP only.
argument-hint: "[sheet to verify]"
---

# Verify a schematic edit

Run after every readability or layout pass, and after any wiring change. The
question is always: **did the change do what I meant and nothing else?**

Read `.claude/CLAUDE.md`. Never edit KiCad files by hand.

## Load

```
load_toolset(["sch_analysis", "sch_export"])
```

## The five checks

Run all five on the sheet you touched. Record the *before* values at the start of
a pass (`set_visual_baseline`, and note the `check_schematic_overlaps` counts) so
you can tell improvement from regression.

| # | Tool | Pass looks like | What a failure means |
|---|---|---|---|
| 1 | `check_schematic_overlaps` | count **≤** the starting count; 0 is the goal | a move landed a body on another |
| 2 | `find_orphan_items` | same or fewer items than before | a symbol move left a wire/label floating |
| 3 | `validate_wire_connections` | no **new** floating endpoints | a symbol moved off its wires |
| 4 | `run_erc` | no **new** errors vs. before | a connection opened or shorted |
| 5 | `render_schematic_png { inline: true, width_px: 3200 }` | text no longer collides | the geometry checks cannot see text — you must look |

Supporting checks when relevant:
- `validate_component_connections` — every connectable pin still attached.
- `find_single_pin_nets` / `find_shorted_nets` — after moving or re-wiring.
- `compare_visual_baseline { schematic, inline_diff: true }` — pixel drift against
  the stored baseline, with the changed region's bounding box and whether the
  source changed since the baseline. Use it to confirm nothing *else* moved.

## Reading a result

- **Improvement, no regression** → keep it, take a new checkpoint
  (`snapshot_project`, `set_visual_baseline`) and continue.
- **Improvement, new regression** → fix the regression in the same pass
  (`fix_connectivity`, re-wire with `connect_pins`/`connect_to_net`) before
  moving on. Do not stack a second change on an unverified one.
- **No improvement or worse** → revert that one step
  (`git diff` shows nothing for KiCad files — Konnect wrote them — so undo by
  applying the inverse move, or restore the checkpoint from `snapshot_project`).
- **Dangling / floating after a symbol move** — expected: `move_schematic_component`
  does not stretch wires. Re-run `fix_connectivity` (it snaps near-miss
  endpoints), then re-check 2 and 3; if the gap is larger than `snap_tolerance`,
  re-wire explicitly.

## ERC note

`run_erc` reports violations filtered by severity. Compare against the baseline
run, not against zero: this design has intentional no-connects and ERC warnings
that predate your change. A **new** error is the signal.

## Done means

1. `check_schematic_overlaps` count did not rise.
2. `find_orphan_items` and `validate_wire_connections` show nothing new.
3. `run_erc` shows no new errors.
4. The inline render reads cleanly to the eye — no string over a string.
5. `compare_visual_baseline` (if a baseline was set) shows the drift is exactly
   the area you edited.
