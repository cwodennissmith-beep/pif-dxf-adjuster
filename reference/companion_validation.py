#!/usr/bin/env python3
"""
Companion-relationship validation hook  (PIF-Trigamma Layer 4 — companion subset).

╔══════════════════════════════════════════════════════════════════════════╗
║  TWO MODES — and why this file implements only ONE of them                 ║
║                                                                            ║
║  AUTO mode (NOT implemented here):                                         ║
║    Given a functional GROUP of pieces that the grammar knows are "used     ║
║    together" (e.g. a living-room set: couch + coffee_table + end_table),   ║
║    iterate the companion table and check every applicable pair             ║
║    automatically. This requires the grammar to (a) model pieces as parts   ║
║    with named role + dimension fields, and (b) have a GROUPING / assembly  ║
║    concept tying pieces into a set.                                        ║
║                                                                            ║
║  OPT-IN mode (implemented here):                                           ║
║    The caller supplies the two roles plus the two raw dimension VALUES     ║
║    (a reference value from piece A and the related value from piece B).    ║
║    The hook looks up the rule and returns an advisory finding. No part     ║
║    object, no grouping, and no schema field is required.                   ║
║                                                                            ║
║  WHY OPT-IN: the VALIDATION-OF-PIF-01 schema read found this repo has NO   ║
║  PIF-Trigamma grammar at all — no part types, no role/dimension fields,    ║
║  and Q3 (grouping) = NO. Per the dispatch guardrail ("if Q3 = no, do NOT   ║
║  fake a grouping concept"), AUTO mode cannot be honestly built yet. This   ║
║  module therefore operates purely on supplied scalar values and invents    ║
║  zero grammar fields. It is standalone reference code, NOT wired into any  ║
║  part schema or the website assistant. See                                 ║
║  docs/decisions/VALIDATION-OF-PIF-01-schema-read.md.                       ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

_TABLE_PATH = os.path.join(os.path.dirname(__file__), "companion_relationships.json")


# ─────────────────────────────────────────────────────────────
# Findings (local, minimal — there is no grammar Finding type yet)
# ─────────────────────────────────────────────────────────────

# Severity tiers from the scope (§2). Companion checks are ADVISORY.
TIER_HARD = "HARD"
TIER_SOFT = "SOFT"
TIER_ADVISORY = "ADVISORY"
TIER_NOT_SOURCEABLE = "NOT-SOURCEABLE"


@dataclass
class Finding:
    """A single validation result. Nothing silently passes (§2): an in-band
    check returns status='ok'; an out-of-band check returns status='advisory'."""
    rule_id: str
    status: str            # "ok" | "advisory"
    tier: str              # TIER_* (advisory rules carry TIER_ADVISORY)
    role_a: str
    role_b: str
    ref_dimension: str
    related_dimension: str
    ref_value: float
    related_value: float
    accepted_min: float
    accepted_max: float
    message: str


# ─────────────────────────────────────────────────────────────
# Table loading + lookup
# ─────────────────────────────────────────────────────────────

def load_table(path: str = _TABLE_PATH) -> list[dict]:
    """Load the companion-relationship entries from the JSON data file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["entries"]


def _find_rule(entries: list[dict], role_a: str, role_b: str,
               related_dimension_b: Optional[str] = None) -> Optional[dict]:
    """Find the rule for (role_a, role_b), optionally disambiguated by the
    related dimension (a role pair can have more than one rule, e.g. couch +
    coffee_table has both a height differential and a distance gap)."""
    for e in entries:
        if e["role_a"] == role_a and e["role_b"] == role_b:
            if related_dimension_b is None or e["related_dimension_b"] == related_dimension_b:
                return e
    return None


def _accepted_range(rule: dict, ref_value: float) -> tuple[float, float]:
    """Resolve a rule's band into a concrete [min, max] for the related value."""
    band = rule["value_or_band"]
    if band["basis"] == "offset_from_ref":
        return ref_value + band["min"], ref_value + band["max"]
    # "absolute": the related value (a distance/gap) is compared directly.
    return band["min"], band["max"]


# ─────────────────────────────────────────────────────────────
# OPT-IN hook
# ─────────────────────────────────────────────────────────────

def check_companion(role_a: str, role_b: str,
                    ref_dimension_value: float,
                    related_dimension_value: float,
                    related_dimension_b: Optional[str] = None,
                    entries: Optional[list[dict]] = None) -> Optional[Finding]:
    """Opt-in companion check.

    The caller supplies the governing dimension value from piece A
    (``ref_dimension_value``) and the dimension value on piece B that
    references it (``related_dimension_value``). Returns a Finding
    (status 'ok' or 'advisory'), or None if no rule covers this role pair.

    No part object, grouping, or schema field is touched — values are raw.
    """
    if entries is None:
        entries = load_table()
    rule = _find_rule(entries, role_a, role_b, related_dimension_b)
    if rule is None:
        return None

    lo, hi = _accepted_range(rule, ref_dimension_value)
    in_band = lo <= related_dimension_value <= hi
    note = rule["value_or_band"].get("note", "")

    if in_band:
        msg = (f"{role_b}.{rule['related_dimension_b']}={related_dimension_value:g}\" "
               f"is within the companion band [{lo:g}, {hi:g}]\" for "
               f"{role_a}.{rule['ref_dimension_a']}={ref_dimension_value:g}\". OK.")
        status = "ok"
    else:
        msg = (f"ADVISORY: {role_b}.{rule['related_dimension_b']}={related_dimension_value:g}\" "
               f"falls outside the companion band [{lo:g}, {hi:g}]\" for "
               f"{role_a}.{rule['ref_dimension_a']}={ref_dimension_value:g}\" "
               f"({rule['relationship_type']}: {note}). "
               f"Buildable, but non-standard — acknowledge & record override.")
        status = "advisory"

    return Finding(
        rule_id=rule["id"], status=status, tier=TIER_ADVISORY,
        role_a=role_a, role_b=role_b,
        ref_dimension=rule["ref_dimension_a"], related_dimension=rule["related_dimension_b"],
        ref_value=ref_dimension_value, related_value=related_dimension_value,
        accepted_min=lo, accepted_max=hi, message=msg,
    )


# AUTO mode is intentionally a stub: it cannot be honestly implemented until
# the grammar gains (a) parts with role/dimension fields and (b) a grouping
# concept. Calling it now raises rather than fabricating a group.
def check_group(*_args, **_kwargs):
    raise NotImplementedError(
        "AUTO companion checking needs a grammar grouping/assembly concept "
        "(schema read Q3 = NO). Use check_companion() (opt-in) until the "
        "grammar models pieces and groups."
    )


if __name__ == "__main__":
    # Tiny self-demo on supplied values (no grammar involved).
    tbl = load_table()
    demo = [
        ("couch", "end_table", 25.0, 24.0, "top_height"),     # arm 25, table 24 -> ok
        ("desk", "desk_chair", 18.0, 24.0, "work_surface_height"),  # 24-18=6 < 10 -> advisory
    ]
    for ra, rb, av, bv, dim in demo:
        f = check_companion(ra, rb, av, bv, related_dimension_b=dim, entries=tbl)
        print(f"{f.status.upper():8} {f.message}")
