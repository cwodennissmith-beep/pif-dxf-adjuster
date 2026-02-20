#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  PIF DXF Material Adjuster v1.0                                 ║
║  Parametric Interaction Framework                                ║
║                                                                  ║
║  Adjusts slot/tab/dado features in DXF files to match actual     ║
║  material thickness. Designed for CNC users who purchase DXF     ║
║  files but need to adapt them for real material dimensions.       ║
║                                                                  ║
║  © 2026 PIF — Parametric Interaction Framework                   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import math
import ezdxf
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict


# ─────────────────────────────────────────────────────────────
# COMMON MATERIAL THICKNESSES (inches)
# ─────────────────────────────────────────────────────────────

COMMON_THICKNESSES = {
    "1/8\" (3mm)":   0.125,
    "1/4\" (6mm)":   0.250,
    "3/8\" (9mm)":   0.375,
    "1/2\" (12mm)":  0.500,
    "5/8\" (16mm)":  0.625,
    "3/4\" (18mm)":  0.750,
    "1\" (25mm)":    1.000,
}


# ─────────────────────────────────────────────────────────────
# ADJUSTMENT LOG
# ─────────────────────────────────────────────────────────────

@dataclass
class LogEntry:
    entity_type: str
    layer: str
    description: str
    original_value: float
    new_value: float


@dataclass
class AdjustmentLog:
    entries: List[LogEntry] = field(default_factory=list)
    stats: Dict = field(default_factory=lambda: {
        "entities_scanned": 0,
        "entities_modified": 0,
        "lines_adjusted": 0,
        "polylines_adjusted": 0,
        "circles_adjusted": 0,
    })

    def add_entry(self, entity_type, layer, description, original, new):
        self.entries.append(LogEntry(entity_type, layer, description, original, new))

    def summary_text(self, design_thickness, actual_thickness):
        delta = actual_thickness - design_thickness
        direction = "EXPANDING" if delta > 0 else "SHRINKING"
        lines = [
            "╔══════════════════════════════════════════════════════════╗",
            "║  PIF DXF Material Adjuster — Adjustment Report          ║",
            "╚══════════════════════════════════════════════════════════╝",
            "",
            f"  Design thickness:  {design_thickness:.4f}\"",
            f"  Actual thickness:  {actual_thickness:.4f}\"",
            f"  Delta:             {abs(delta):.4f}\" ({direction})",
            "",
            f"  Entities scanned:  {self.stats['entities_scanned']}",
            f"  Entities modified: {self.stats['entities_modified']}",
            f"    Line pairs:      {self.stats['lines_adjusted']}",
            f"    Polylines:       {self.stats['polylines_adjusted']}",
            f"    Circles/arcs:    {self.stats['circles_adjusted']}",
            "",
            "  ─── Detailed Changes ───",
            "",
        ]
        for e in self.entries:
            lines.append(f"  [{e.entity_type}] Layer: {e.layer}")
            lines.append(f"    {e.description}")
            lines.append(f"    {e.original_value:.4f}\" → {e.new_value:.4f}\"")
            lines.append("")

        if not self.entries:
            lines.append("  No features matched the design thickness.")
            lines.append("  The file may use a different thickness or non-standard geometry.")
            lines.append("")

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# CORE ADJUSTER ENGINE
# ─────────────────────────────────────────────────────────────

class DXFMaterialAdjuster:
    """
    Reads a DXF file, identifies features that match a nominal
    material thickness, and adjusts them to the actual thickness.
    
    Detects:
      - Line pairs forming slots/dados
      - Rectangular polylines forming tabs
      - Circles/arcs used as relief cuts (radius = thickness/2)
    """

    def __init__(self, filepath: str, design_thickness: float, actual_thickness: float,
                 tolerance: float = 0.02):
        self.filepath = filepath
        self.design_thickness = design_thickness
        self.actual_thickness = actual_thickness
        self.tolerance = tolerance
        self.delta = actual_thickness - design_thickness
        self.log = AdjustmentLog()
        self.doc = None

    def load(self):
        """Load the DXF file."""
        self.doc = ezdxf.readfile(self.filepath)
        return self

    def load_from_stream(self, stream):
        """Load DXF from a file-like stream (for web app)."""
        self.doc = ezdxf.read(stream)
        return self

    def adjust(self):
        """Run all adjustment passes."""
        if self.doc is None:
            raise RuntimeError("No DXF loaded. Call load() or load_from_stream() first.")

        msp = self.doc.modelspace()
        all_entities = list(msp)
        self.log.stats["entities_scanned"] = len(all_entities)

        # Pass 1: Line pairs (slots, dados)
        self._adjust_line_pairs(msp)

        # Pass 2: Rectangular polylines (tabs)
        self._adjust_polyline_rectangles(msp)

        # Pass 3: Circles and arcs (relief cuts)
        self._adjust_circles_arcs(msp)

        return self

    def save(self, output_path: str):
        """Save the adjusted DXF to a file."""
        self.doc.saveas(output_path)

    def save_to_stream(self):
        """Save adjusted DXF to a BytesIO stream (for web app)."""
        from io import BytesIO
        stream = BytesIO()
        self.doc.write(stream)
        stream.seek(0)
        return stream

    # ── Line Pair Detection ──────────────────────────────────

    def _adjust_line_pairs(self, msp):
        """Find parallel line pairs whose distance matches design thickness."""
        lines = [e for e in msp if e.dxftype() == "LINE"]
        matched = set()

        for i, line_a in enumerate(lines):
            if id(line_a) in matched:
                continue
            for j, line_b in enumerate(lines):
                if i >= j or id(line_b) in matched:
                    continue

                dist = self._parallel_line_distance(line_a, line_b)
                if dist is not None and abs(dist - self.design_thickness) <= self.tolerance:
                    self._shift_line_pair(line_a, line_b, dist)
                    matched.add(id(line_a))
                    matched.add(id(line_b))

    def _parallel_line_distance(self, line_a, line_b) -> Optional[float]:
        """Calculate distance between two parallel lines, or None if not parallel."""
        ax1, ay1 = line_a.dxf.start.x, line_a.dxf.start.y
        ax2, ay2 = line_a.dxf.end.x, line_a.dxf.end.y
        bx1, by1 = line_b.dxf.start.x, line_b.dxf.start.y
        bx2, by2 = line_b.dxf.end.x, line_b.dxf.end.y

        # Direction vectors
        da = (ax2 - ax1, ay2 - ay1)
        db = (bx2 - bx1, by2 - by1)

        len_a = math.hypot(*da)
        len_b = math.hypot(*db)
        if len_a < 1e-9 or len_b < 1e-9:
            return None

        # Normalize
        da_n = (da[0] / len_a, da[1] / len_a)
        db_n = (db[0] / len_b, db[1] / len_b)

        # Check parallel (cross product ≈ 0)
        cross = abs(da_n[0] * db_n[1] - da_n[1] * db_n[0])
        if cross > 0.01:
            return None

        # Check overlap (project onto shared axis)
        # Distance = point-to-line distance from B's start to line A
        nx, ny = -da_n[1], da_n[0]  # normal to line A
        dist = abs(nx * (bx1 - ax1) + ny * (by1 - ay1))

        if dist < 1e-9:
            return None

        # Verify overlap exists
        proj_a1 = da_n[0] * ax1 + da_n[1] * ay1
        proj_a2 = da_n[0] * ax2 + da_n[1] * ay2
        proj_b1 = da_n[0] * bx1 + da_n[1] * by1
        proj_b2 = da_n[0] * bx2 + da_n[1] * by2

        a_min, a_max = min(proj_a1, proj_a2), max(proj_a1, proj_a2)
        b_min, b_max = min(proj_b1, proj_b2), max(proj_b1, proj_b2)

        overlap = min(a_max, b_max) - max(a_min, b_min)
        if overlap < 0.01:
            return None

        return dist

    def _shift_line_pair(self, line_a, line_b, current_dist):
        """Shift line_b to achieve the actual_thickness distance from line_a."""
        ax1, ay1 = line_a.dxf.start.x, line_a.dxf.start.y
        ax2, ay2 = line_a.dxf.end.x, line_a.dxf.end.y
        bx1, by1 = line_b.dxf.start.x, line_b.dxf.start.y

        da = (ax2 - ax1, ay2 - ay1)
        length = math.hypot(*da)
        da_n = (da[0] / length, da[1] / length)

        # Normal pointing from A toward B
        nx, ny = -da_n[1], da_n[0]
        dot = nx * (bx1 - ax1) + ny * (by1 - ay1)
        if dot < 0:
            nx, ny = -nx, -ny

        # How much to shift B
        shift = self.actual_thickness - current_dist

        line_b.dxf.start = (
            line_b.dxf.start.x + nx * shift,
            line_b.dxf.start.y + ny * shift,
            line_b.dxf.start.z,
        )
        line_b.dxf.end = (
            line_b.dxf.end.x + nx * shift,
            line_b.dxf.end.y + ny * shift,
            line_b.dxf.end.z,
        )

        layer = line_b.dxf.layer if hasattr(line_b.dxf, 'layer') else "0"
        self.log.add_entry(
            "LINE PAIR", layer,
            f"Parallel lines — {current_dist:.4f}\" gap adjusted",
            current_dist, self.actual_thickness,
        )
        self.log.stats["entities_modified"] += 2
        self.log.stats["lines_adjusted"] += 1

    # ── Polyline Rectangle Detection ─────────────────────────

    def _adjust_polyline_rectangles(self, msp):
        """Find closed rectangular polylines with an edge matching design thickness."""
        polys = [e for e in msp if e.dxftype() == "LWPOLYLINE"]

        for poly in polys:
            if not poly.closed:
                # Check if first point equals last point (implicitly closed)
                points = list(poly.get_points(format='xy'))
                if len(points) < 4:
                    continue
                if math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1]) > 0.001:
                    continue
                points = points[:-1]  # remove duplicate closing point
            else:
                points = list(poly.get_points(format='xy'))

            if len(points) != 4:
                continue

            # Calculate edge lengths
            edges = []
            for k in range(4):
                p1 = points[k]
                p2 = points[(k + 1) % 4]
                length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                edges.append({"index": k, "length": length, "p1": p1, "p2": p2})

            # Find edges matching design thickness
            for edge in edges:
                if abs(edge["length"] - self.design_thickness) <= self.tolerance:
                    self._adjust_rect_edge(poly, points, edge)
                    break  # one adjustment per polyline

    def _adjust_rect_edge(self, poly, points, edge):
        """
        When a matching edge is found (e.g., 0.75" vertical side), the actual
        slot/tab dimension is the distance between the two PERPENDICULAR edges
        (e.g., horizontal top and bottom). We move those perpendicular edges
        to achieve the actual thickness.
        """
        idx = edge["index"]
        new_length = self.actual_thickness
        shift = (new_length - edge["length"]) / 2.0

        # The matching edge direction
        p1 = points[idx]
        p2 = points[(idx + 1) % 4]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length < 1e-9:
            return

        # Unit direction along matching edge — this IS the direction of the slot dimension
        ux = dx / length
        uy = dy / length

        # We move each pair of adjacent edges (perpendicular to matching edge)
        # Edge at idx uses points idx and idx+1 — these are at one "end" in the slot direction
        # The opposite parallel edge uses points idx+2 and idx+3
        # The perpendicular edges are: idx+1→idx+2 and idx+3→idx
        # We need to shift the two horizontal edges apart/together

        # Simpler approach: move points along the matching edge direction
        # Bottom pair: points idx and (idx+3)%4 — move down by shift
        # Top pair: points (idx+1)%4 and (idx+2)%4 — move up by shift

        new_points = list(points)

        # Points at the "start" of the matching edge direction: move backward
        new_points[idx] = (points[idx][0] - ux * shift, points[idx][1] - uy * shift)
        new_points[(idx + 3) % 4] = (points[(idx + 3) % 4][0] - ux * shift, points[(idx + 3) % 4][1] - uy * shift)

        # Points at the "end" of the matching edge direction: move forward
        new_points[(idx + 1) % 4] = (points[(idx + 1) % 4][0] + ux * shift, points[(idx + 1) % 4][1] + uy * shift)
        new_points[(idx + 2) % 4] = (points[(idx + 2) % 4][0] + ux * shift, points[(idx + 2) % 4][1] + uy * shift)

        # Apply new points
        if poly.closed:
            poly.set_points(new_points, format='xy')
        else:
            new_points.append(new_points[0])
            poly.set_points(new_points, format='xy')

        layer = poly.dxf.layer if hasattr(poly.dxf, 'layer') else "0"
        self.log.add_entry(
            "LWPOLYLINE", layer,
            f"Rectangle slot/tab — {edge['length']:.4f}\" dimension adjusted",
            edge["length"], new_length,
        )
        self.log.stats["entities_modified"] += 1
        self.log.stats["polylines_adjusted"] += 1

    # ── Circle / Arc Detection ───────────────────────────────

    def _adjust_circles_arcs(self, msp):
        """Find circles/arcs whose radius matches design_thickness / 2 (relief cuts)."""
        target_radius = self.design_thickness / 2.0
        new_radius = self.actual_thickness / 2.0

        for entity in msp:
            etype = entity.dxftype()
            if etype == "CIRCLE":
                r = entity.dxf.radius
                if abs(r - target_radius) <= self.tolerance / 2:
                    entity.dxf.radius = new_radius
                    layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else "0"
                    self.log.add_entry(
                        "CIRCLE", layer,
                        f"Relief cut circle — radius adjusted",
                        r, new_radius,
                    )
                    self.log.stats["entities_modified"] += 1
                    self.log.stats["circles_adjusted"] += 1

            elif etype == "ARC":
                r = entity.dxf.radius
                if abs(r - target_radius) <= self.tolerance / 2:
                    entity.dxf.radius = new_radius
                    layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else "0"
                    self.log.add_entry(
                        "ARC", layer,
                        f"Relief cut arc — radius adjusted",
                        r, new_radius,
                    )
                    self.log.stats["entities_modified"] += 1
                    self.log.stats["circles_adjusted"] += 1
