# VALIDATION-OF-PIF — Work Summary / Handoff

**Date:** 2026-05-30 · **Chat:** VALIDATION-OF-PIF · **Owner:** cwodennissmith-beep
**Branch:** `claude/pif-trigamma-validation-constraints-4ptg0`

## The goal
Build the validation + constraint framework for PIF-Trigamma (a general
furniture/project definition language). Six validation layers — (1) relational,
(2) conservation/closure, (3) standards, (4) anthropometric + companion chain,
(5) form/craft, (6) material discretization — with severity tiers
HARD / SOFT / ADVISORY / NOT-SOURCEABLE and an override ledger that travels with
the plan. Prove on cabinets first, generalize to chairs/tables.

## What was asked, in order, + status

| # | Ask | Status |
|---|-----|--------|
| 1 | Capture the validation/constraint scope as the canonical model doc | DONE — `docs/specs/pif-trigamma-validation-model.md` |
| 2 | Run the §7 read-only schema read (6 questions) | DONE *against this repo* — all six = **no** (no grammar here) — `docs/decisions/VALIDATION-OF-PIF-01-schema-read.md` |
| 3 | Save scope doc to `/docs/specs/`, regen `docs-manifest.json`, commit | DONE — commit `6f951b8` |
| 4 | Build companion-relationship layer (data + advisory hook), opt-in form | DONE — commits `ee18ab9`, `f7ba3af` |
| 5 | Verify the 6 seed numbers against real sources | DONE — all verified, bands corrected |
| 6 | Look outside the repo for the real grammar | DONE — located but not readable (see blocker) |

### Verified companion bands (Layer 4 subset)
- `couch.arm → end_table.top` : within **+2 / −4 in** of arm (was ±1)
- `couch.seat → coffee.top` : **0 to −2 in** below seat (was −4..0)
- `couch.front → coffee.edge` : **14–18 in** gap, 12 in min (confirmed)
- `bed.mattress → nightstand.top` : **0 to +2 in**, broad −2..+6 (confirmed)
- `desk.seat → work_surface` : **+8 to +14 in**, ideal 10–12 (was 10–12)
- `dining.apron_underside → seat` : **≥7–7.5 in** thigh clearance (confirmed)

## The blocker
PIF-Trigamma's grammar does **not** live in `pif-dxf-adjuster` — that repo is the
"Parametric Interaction Framework" DXF material-thickness adjuster (~400 lines of
geometry; shares only a *name* with PIF-Trigamma). The grammar is in other private
repos this session cannot read:
- **`E-PIF-ANY`** — "Parametric Interactive Framework for CNC files"
- **`Selection-Connection`** — the "SC" in the spec's "SC house values"

All access paths hard-denied: GitHub MCP ("not configured for this session"),
session git proxy ("repository not authorized", 502), direct github.com (no creds).
Session allowlist = `{pif-dxf-adjuster}` only. The grammar also lives in
chats/local files that never reached this container.

## How to unblock (owner action, outside the container)
- **A:** Launch the next session **on `E-PIF-ANY`**, or add `E-PIF-ANY` +
  `Selection-Connection` to the environment's allowed repositories.
  Docs: https://code.claude.com/docs/en/claude-code-on-the-web
- **B:** Paste the grammar / part-definition text into chat, or upload the file(s)
  (`.py`/`.md`/`.json`) into the session.

## Next steps once the grammar is visible
1. Re-run the §7 schema read against the **real** part-definition source (true
   file:line citations for Q1–Q6).
2. Port the verified companion layer onto the real part schema (replace the
   standalone stub; wire to actual role/dimension fields).
3. If a needed field is missing → report as a schema gap (do not invent it).
4. If grouping (Q3) exists → add the AUTO companion mode; else keep opt-in.

## Artifacts delivered (this repo)
- `docs/specs/pif-trigamma-validation-model.md` — canonical scope (257 ln)
- `docs/decisions/VALIDATION-OF-PIF-01-schema-read.md` — schema-read findings
- `docs-manifest.json` — doc index
- `reference/companion_relationships.json` — 6 verified entries
- `reference/companion_validation.py` — opt-in advisory hook
- Commits: `0b15cec`, `6f951b8`, `ee18ab9`, `f7ba3af` (all pushed)
