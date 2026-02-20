#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  PIF DXF Material Adjuster — TEST SUITE                         ║
║                                                                  ║
║  Run ALL tests before launching:                                 ║
║    python test_suite.py                                          ║
║                                                                  ║
║  Tests cover:                                                    ║
║    ✓ Line pair (slot/dado) detection & adjustment                ║
║    ✓ Polyline rectangle (tab) detection & adjustment             ║
║    ✓ Circle/arc (relief cut) detection & adjustment              ║
║    ✓ Mixed geometry files                                        ║
║    ✓ Thicker material (expanding slots)                          ║
║    ✓ Thinner material (shrinking slots)                          ║
║    ✓ Metric material sizes                                       ║
║    ✓ Tolerance edge cases                                        ║
║    ✓ Empty / no-match files                                      ║
║    ✓ Complex files with many features                            ║
║    ✓ File I/O (save / load round-trip)                           ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import math
import tempfile
from pathlib import Path

import ezdxf
from pif_dxf_adjuster import DXFMaterialAdjuster, COMMON_THICKNESSES


# ─────────────────────────────────────────────────────────────
# TEST HELPERS
# ─────────────────────────────────────────────────────────────

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name):
        self.passed += 1
        print(f"    ✅ {name}")

    def fail(self, name, expected, got):
        self.failed += 1
        self.errors.append((name, expected, got))
        print(f"    ❌ {name}")
        print(f"       Expected: {expected}")
        print(f"       Got:      {got}")

    def summary(self):
        total = self.passed + self.failed
        print()
        print("  ═══════════════════════════════════════════")
        print(f"  Results: {self.passed}/{total} passed", end="")
        if self.failed:
            print(f"  ·  {self.failed} FAILED")
        else:
            print("  ·  ALL PASS ✓")
        print("  ═══════════════════════════════════════════")

        if self.errors:
            print()
            print("  Failed tests:")
            for name, exp, got in self.errors:
                print(f"    • {name}: expected {exp}, got {got}")

        return self.failed == 0


def assert_close(results, name, value, expected, tolerance=0.001):
    if abs(value - expected) <= tolerance:
        results.ok(name)
    else:
        results.fail(name, f"{expected:.4f}", f"{value:.4f}")


def make_line_pair_dxf(distance, length=5.0):
    """Create a DXF with two parallel horizontal lines separated by `distance`."""
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_line((0, 0), (length, 0))
    msp.add_line((0, distance), (length, distance))
    return doc


def make_rect_dxf(width, height):
    """Create a DXF with a closed rectangular polyline."""
    doc = ezdxf.new()
    msp = doc.modelspace()
    points = [(0, 0), (width, 0), (width, height), (0, height)]
    msp.add_lwpolyline(points, close=True)
    return doc


def make_circle_dxf(radius):
    """Create a DXF with a single circle."""
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_circle((5, 5), radius)
    return doc


def save_and_adjust(doc, design, actual, tolerance=0.02):
    """Save doc to temp file, run adjuster, return adjuster instance."""
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
        doc.saveas(f.name)
        path = f.name
    adj = DXFMaterialAdjuster(path, design, actual, tolerance)
    adj.load()
    adj.adjust()
    os.unlink(path)
    return adj


# ─────────────────────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────────────────────

def run_all_tests():
    results = TestResults()

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  PIF DXF Material Adjuster — TEST SUITE                 ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # ── TEST 1: Basic line pair detection ──
    print("\n  ── Line Pair Tests ──")
    doc = make_line_pair_dxf(0.75)
    adj = save_and_adjust(doc, 0.75, 0.72)
    assert_close(results, "TEST 1: Line pair shrink 0.75→0.72", adj.log.stats["lines_adjusted"], 1, 0)

    # ── TEST 2: Line pair expand ──
    doc = make_line_pair_dxf(0.75)
    adj = save_and_adjust(doc, 0.75, 0.78)
    assert_close(results, "TEST 2: Line pair expand 0.75→0.78", adj.log.stats["lines_adjusted"], 1, 0)

    # ── TEST 3: Verify adjusted distance ──
    doc = make_line_pair_dxf(0.75)
    adj = save_and_adjust(doc, 0.75, 0.72)
    msp = adj.doc.modelspace()
    lines = [e for e in msp if e.dxftype() == "LINE"]
    dist = abs(lines[1].dxf.start.y - lines[0].dxf.start.y)
    assert_close(results, "TEST 3: Adjusted distance = 0.72", dist, 0.72)

    # ── TEST 4: No match (wrong thickness) ──
    doc = make_line_pair_dxf(0.50)
    adj = save_and_adjust(doc, 0.75, 0.72)
    assert_close(results, "TEST 4: No match for wrong thickness", adj.log.stats["lines_adjusted"], 0, 0)

    # ── TEST 5: Vertical line pair ──
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_line((0, 0), (0, 5))
    msp.add_line((0.75, 0), (0.75, 5))
    adj = save_and_adjust(doc, 0.75, 0.72)
    assert_close(results, "TEST 5: Vertical line pair detected", adj.log.stats["lines_adjusted"], 1, 0)

    # ── TEST 6: Rectangle tab detection ──
    print("\n  ── Polyline Rectangle Tests ──")
    doc = make_rect_dxf(2.0, 0.75)
    adj = save_and_adjust(doc, 0.75, 0.72)
    assert_close(results, "TEST 6: Rectangle tab detected", adj.log.stats["polylines_adjusted"], 1, 0)

    # ── TEST 7: Rectangle expand ──
    doc = make_rect_dxf(2.0, 0.75)
    adj = save_and_adjust(doc, 0.75, 0.80)
    assert_close(results, "TEST 7: Rectangle expand", adj.log.stats["polylines_adjusted"], 1, 0)

    # ── TEST 8: Rectangle — verify adjusted dimension ──
    doc = make_rect_dxf(2.0, 0.75)
    adj = save_and_adjust(doc, 0.75, 0.72)
    msp = adj.doc.modelspace()
    polys = [e for e in msp if e.dxftype() == "LWPOLYLINE"]
    pts = list(polys[0].get_points(format='xy'))
    # Check the short dimension (height)
    heights = set()
    for i in range(len(pts)):
        p1 = pts[i]
        p2 = pts[(i + 1) % len(pts)]
        edge_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        heights.add(round(edge_len, 4))
    assert_close(results, "TEST 8: Rect adjusted to 0.72", min(heights), 0.72, 0.005)

    # ── TEST 9: Square polyline (both edges match) ──
    doc = make_rect_dxf(0.75, 0.75)
    adj = save_and_adjust(doc, 0.75, 0.72)
    assert_close(results, "TEST 9: Square polyline (one adjustment)", adj.log.stats["polylines_adjusted"], 1, 0)

    # ── TEST 10: Non-matching rectangle ──
    doc = make_rect_dxf(3.0, 2.0)
    adj = save_and_adjust(doc, 0.75, 0.72)
    assert_close(results, "TEST 10: Non-matching rect ignored", adj.log.stats["polylines_adjusted"], 0, 0)

    # ── TEST 11: Circle relief cut ──
    print("\n  ── Circle / Arc Tests ──")
    doc = make_circle_dxf(0.375)  # radius = 3/4" / 2
    adj = save_and_adjust(doc, 0.75, 0.72)
    assert_close(results, "TEST 11: Circle relief detected", adj.log.stats["circles_adjusted"], 1, 0)

    # ── TEST 12: Circle adjusted radius ──
    msp = adj.doc.modelspace()
    circles = [e for e in msp if e.dxftype() == "CIRCLE"]
    assert_close(results, "TEST 12: Circle radius → 0.36", circles[0].dxf.radius, 0.36)

    # ── TEST 13: Arc relief cut ──
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_arc((5, 5), 0.375, 0, 180)
    adj = save_and_adjust(doc, 0.75, 0.72)
    assert_close(results, "TEST 13: Arc relief detected", adj.log.stats["circles_adjusted"], 1, 0)

    # ── TEST 14: Non-matching circle ignored ──
    doc = make_circle_dxf(1.5)
    adj = save_and_adjust(doc, 0.75, 0.72)
    assert_close(results, "TEST 14: Non-matching circle ignored", adj.log.stats["circles_adjusted"], 0, 0)

    # ── TEST 15: Mixed geometry ──
    print("\n  ── Mixed & Edge Case Tests ──")
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_line((0, 0), (5, 0))
    msp.add_line((0, 0.75), (5, 0.75))
    points = [(10, 0), (12, 0), (12, 0.75), (10, 0.75)]
    msp.add_lwpolyline(points, close=True)
    msp.add_circle((20, 5), 0.375)
    adj = save_and_adjust(doc, 0.75, 0.72)
    total = adj.log.stats["lines_adjusted"] + adj.log.stats["polylines_adjusted"] + adj.log.stats["circles_adjusted"]
    assert_close(results, "TEST 15: Mixed geometry (3 features)", total, 3, 0)

    # ── TEST 16: Thinner material (1/2" → 0.47") ──
    doc = make_line_pair_dxf(0.50)
    adj = save_and_adjust(doc, 0.50, 0.47)
    assert_close(results, "TEST 16: Half-inch material adjust", adj.log.stats["lines_adjusted"], 1, 0)

    # ── TEST 17: Metric-ish (18mm = 0.7087") ──
    doc = make_line_pair_dxf(0.7087)
    adj = save_and_adjust(doc, 0.7087, 0.6929, tolerance=0.02)
    assert_close(results, "TEST 17: Metric 18mm→17.6mm", adj.log.stats["lines_adjusted"], 1, 0)

    # ── TEST 18: Tolerance boundary — just inside ──
    doc = make_line_pair_dxf(0.769)  # 0.75 + 0.019 = clearly inside tolerance
    adj = save_and_adjust(doc, 0.75, 0.72, tolerance=0.02)
    assert_close(results, "TEST 18: Inside tolerance boundary (0.769 vs 0.75)", adj.log.stats["lines_adjusted"], 1, 0)

    # ── TEST 19: Tolerance boundary — just outside ──
    doc = make_line_pair_dxf(0.78)  # 0.75 + 0.03 = outside default
    adj = save_and_adjust(doc, 0.75, 0.72, tolerance=0.02)
    assert_close(results, "TEST 19: Outside tolerance (0.78 vs 0.75)", adj.log.stats["lines_adjusted"], 0, 0)

    # ── TEST 20: Empty file ──
    doc = ezdxf.new()
    adj = save_and_adjust(doc, 0.75, 0.72)
    assert_close(results, "TEST 20: Empty file — no crash", adj.log.stats["entities_modified"], 0, 0)

    # ── TEST 21: Complex file (many features) ──
    doc = ezdxf.new()
    msp = doc.modelspace()
    for i in range(5):
        y = i * 3
        msp.add_line((0, y), (5, y))
        msp.add_line((0, y + 0.75), (5, y + 0.75))
    adj = save_and_adjust(doc, 0.75, 0.72)
    assert_close(results, "TEST 21: 5 line pairs detected", adj.log.stats["lines_adjusted"], 5, 0)

    # ── TEST 22: File save/load round-trip ──
    print("\n  ── File I/O Tests ──")
    doc = make_line_pair_dxf(0.75)
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
        doc.saveas(f.name)
        path = f.name

    adj = DXFMaterialAdjuster(path, 0.75, 0.72)
    adj.load()
    adj.adjust()

    out_path = path.replace(".dxf", "_adjusted.dxf")
    adj.save(out_path)

    # Reload and verify
    doc2 = ezdxf.readfile(out_path)
    msp2 = doc2.modelspace()
    lines2 = [e for e in msp2 if e.dxftype() == "LINE"]
    dist2 = abs(lines2[1].dxf.start.y - lines2[0].dxf.start.y)
    assert_close(results, "TEST 22: Save/reload round-trip", dist2, 0.72)

    os.unlink(path)
    os.unlink(out_path)

    # ── SUMMARY ──
    all_passed = results.summary()

    if all_passed:
        print()
        print("  🚀 Ready to deploy!")
        print()
    else:
        print()
        print("  ⚠️  Fix failures before deploying.")
        print()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
