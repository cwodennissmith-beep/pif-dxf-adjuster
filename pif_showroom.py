#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  PIF Showroom — product catalog, previews & pricing               ║
║  Parametric Interaction Framework                                 ║
║                                                                  ║
║  Powers the 2D showroom: a gallery of the projects we offer.      ║
║  Each product carries specs + a price and renders a preview        ║
║  straight from its DXF cut file. A product can then be opened in    ║
║  the 3D configurator (handoff wired in app.py).                    ║
║                                                                  ║
║  © 2026 PIF — Parametric Interaction Framework                   ║
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent / "data"
DXF_DIR = DATA_DIR / "dxf"
CATALOG_PATH = DATA_DIR / "catalog.json"

PREVIEW_BG = "#0E1117"  # matches .streamlit/config.toml backgroundColor


# ─────────────────────────────────────────────────────────────
# PRODUCT MODEL
# ─────────────────────────────────────────────────────────────

@dataclass
class Product:
    """A single offering in the showroom."""
    id: str
    name: str
    category: str                 # e.g. "Cabinet", "Drawer", "Table", "Shelf"
    material: str                 # e.g. "Maple Plywood"
    width_in: float               # nominal outer dimensions, inches
    height_in: float
    depth_in: float
    price: float = 0.0            # USD; 0 = not yet priced
    currency: str = "USD"
    dxf_file: Optional[str] = None  # filename inside data/dxf/
    description: str = ""
    price_note: str = ""          # how the price was derived (manual / estimate / AI)

    @property
    def dimensions_text(self) -> str:
        return f'{self.width_in:g}" W × {self.height_in:g}" H × {self.depth_in:g}" D'

    @property
    def dxf_path(self) -> Optional[Path]:
        if not self.dxf_file:
            return None
        return DXF_DIR / self.dxf_file

    @property
    def price_text(self) -> str:
        if self.price <= 0:
            return "— (not priced)"
        return f"${self.price:,.2f}"


# ─────────────────────────────────────────────────────────────
# CATALOG PERSISTENCE
# ─────────────────────────────────────────────────────────────

def _ensure_dirs() -> None:
    DXF_DIR.mkdir(parents=True, exist_ok=True)


def load_catalog() -> List[Product]:
    """Load the product catalog from JSON, seeding demo products on first run."""
    _ensure_dirs()
    if not CATALOG_PATH.exists():
        products = _seed_demo_catalog()
        save_catalog(products)
        return products
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Product(**entry) for entry in raw.get("products", [])]


def save_catalog(products: List[Product]) -> None:
    _ensure_dirs()
    payload = {"version": 1, "products": [asdict(p) for p in products]}
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def add_product(products: List[Product], product: Product) -> List[Product]:
    products.append(product)
    save_catalog(products)
    return products


def update_product(products: List[Product], product: Product) -> List[Product]:
    for i, p in enumerate(products):
        if p.id == product.id:
            products[i] = product
            break
    save_catalog(products)
    return products


def get_product(products: List[Product], product_id: str) -> Optional[Product]:
    return next((p for p in products if p.id == product_id), None)


# ─────────────────────────────────────────────────────────────
# DXF PREVIEW RENDERING
# ─────────────────────────────────────────────────────────────

def render_dxf_preview(dxf_path: Path, width_px: int = 480) -> bytes:
    """Render a DXF modelspace to a PNG (bytes) on the showroom's dark theme."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import ezdxf
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.properties import LayoutProperties

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    fig = plt.figure(figsize=(width_px / 80.0, width_px / 80.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    try:
        ctx = RenderContext(doc)
        backend = MatplotlibBackend(ax)
        lp = LayoutProperties.from_layout(msp)
        lp.set_colors(PREVIEW_BG)  # background; foreground auto-contrasts (light)
        Frontend(ctx, backend).draw_layout(msp, finalize=True, layout_properties=lp)
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=80, facecolor=PREVIEW_BG, bbox_inches="tight")
        buf.seek(0)
        return buf.read()
    finally:
        plt.close(fig)


def render_dxf_stream_preview(stream, width_px: int = 480) -> bytes:
    """Render a DXF from an in-memory text stream (for freshly-uploaded files)."""
    import tempfile
    data = stream.read()
    if isinstance(data, bytes):
        data = data.decode("utf-8", errors="replace")
    with tempfile.NamedTemporaryFile("w", suffix=".dxf", delete=False, encoding="utf-8") as f:
        f.write(data)
        tmp = f.name
    try:
        return render_dxf_preview(Path(tmp), width_px=width_px)
    finally:
        os.unlink(tmp)


# ─────────────────────────────────────────────────────────────
# PRICING
# ─────────────────────────────────────────────────────────────

# Rough installed material cost per square foot of face area (USD).
MATERIAL_RATE_PER_SQFT: Dict[str, float] = {
    "MDF": 8.0,
    "Melamine": 10.0,
    "Birch Plywood": 12.0,
    "Maple Plywood": 16.0,
    "Maple": 18.0,
    "Red Oak": 16.0,
    "White Oak": 22.0,
    "Walnut": 32.0,
    "Cherry": 26.0,
}
DEFAULT_RATE = 14.0

# Complexity multiplier by product category.
CATEGORY_MULTIPLIER: Dict[str, float] = {
    "Cabinet": 1.0,
    "Drawer": 0.65,
    "Door": 0.5,
    "Shelf": 0.4,
    "Table": 1.2,
    "Desk": 1.25,
    "Bookcase": 1.1,
}
DEFAULT_MULTIPLIER = 1.0

BASE_PRICE = 35.0  # fixed overhead per piece


def estimate_price(product: Product) -> tuple[float, str]:
    """
    Heuristic price estimate from material, face area, depth and category.
    Returns (price, human-readable note). Works fully offline.
    """
    rate = MATERIAL_RATE_PER_SQFT.get(product.material, DEFAULT_RATE)
    mult = CATEGORY_MULTIPLIER.get(product.category, DEFAULT_MULTIPLIER)
    face_sqft = max(product.width_in * product.height_in, 1.0) / 144.0
    depth_factor = 1.0 + (max(product.depth_in, 0.0) / 48.0)  # deeper = more material
    price = (BASE_PRICE + face_sqft * rate) * mult * depth_factor
    price = round(price, 2)
    note = (
        f"Estimate: {face_sqft:.2f} sq ft face × ${rate:.0f}/sq ft "
        f"({product.material}), ×{mult:g} ({product.category}), depth ×{depth_factor:.2f}"
    )
    return price, note


def ai_price_available() -> bool:
    """True if an Anthropic API key is present so AI pricing can be used."""
    return bool(
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("CLAUDE_API_KEY")
        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    )


def estimate_price_ai(product: Product) -> tuple[Optional[float], str]:
    """
    Ask Claude for a market price suggestion. Falls back to the heuristic
    when no API key or SDK is available. Returns (price_or_None, note).
    """
    if not ai_price_available():
        price, note = estimate_price(product)
        return price, "No API key set — used built-in estimate. " + note
    try:
        import anthropic  # lazy import; optional dependency
    except ImportError:
        price, note = estimate_price(product)
        return price, "anthropic SDK not installed — used built-in estimate. " + note

    try:
        client = anthropic.Anthropic()
        prompt = (
            "You are a pricing assistant for a custom cabinetry/furniture shop. "
            "Given the product spec, return a single fair retail price in USD. "
            "Respond with ONLY a JSON object: {\"price\": <number>, \"rationale\": <short string>}.\n\n"
            f"Product: {product.name}\n"
            f"Category: {product.category}\n"
            f"Material: {product.material}\n"
            f"Dimensions: {product.dimensions_text}\n"
            f"Description: {product.description or '(none)'}"
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
        data = json.loads(text[text.index("{"): text.rindex("}") + 1])
        return round(float(data["price"]), 2), "AI: " + str(data.get("rationale", "")).strip()
    except Exception as exc:  # network, parse, auth — degrade gracefully
        price, note = estimate_price(product)
        return price, f"AI pricing failed ({exc.__class__.__name__}) — used built-in estimate. " + note


# ─────────────────────────────────────────────────────────────
# DEMO CATALOG SEEDING
# ─────────────────────────────────────────────────────────────

def _make_sample_dxf(path: Path, kind: str, w: float, h: float) -> None:
    """Generate a simple representative DXF for a demo product."""
    import ezdxf
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (w, 0), (w, h), (0, h)], close=True)  # outer face

    if kind == "two_door":
        mid = h / 2
        for y0, y1 in [(1, mid - 0.5), (mid + 0.5, h - 1)]:
            msp.add_lwpolyline([(1, y0), (w - 1, y0), (w - 1, y1), (1, y1)], close=True)
        msp.add_circle((w - 2, mid - 2), 0.375)
        msp.add_circle((w - 2, mid + 2), 0.375)
    elif kind == "drawer_stack":
        n = 3
        gap = h / n
        for i in range(n):
            y0, y1 = i * gap + 1, (i + 1) * gap - 1
            msp.add_lwpolyline([(1, y0), (w - 1, y0), (w - 1, y1), (1, y1)], close=True)
            msp.add_circle((w / 2, (y0 + y1) / 2), 0.375)
    elif kind == "open_shelf":
        for i in range(1, 4):
            y = h * i / 4
            msp.add_line((0, y), (w, y))
    elif kind == "table":
        msp.add_lwpolyline([(2, 2), (w - 2, 2), (w - 2, h - 2), (2, h - 2)], close=True)
        for cx, cy in [(4, 4), (w - 4, 4), (4, h - 4), (w - 4, h - 4)]:
            msp.add_circle((cx, cy), 1.0)  # legs
    doc.saveas(str(path))


def _seed_demo_catalog() -> List[Product]:
    """Create a handful of demo products (with DXFs) so the showroom isn't empty."""
    _ensure_dirs()
    specs = [
        # id, name, category, material, w, h, d, kind
        ("cab-base-24", "24\" Base Cabinet", "Cabinet", "Maple Plywood", 24, 30, 24, "two_door"),
        ("cab-drawer-18", "18\" 3-Drawer Base", "Drawer", "Birch Plywood", 18, 30, 24, "drawer_stack"),
        ("shelf-open-36", "36\" Open Bookcase", "Bookcase", "Red Oak", 36, 48, 12, "open_shelf"),
        ("tbl-coffee-48", "48\" Coffee Table", "Table", "Walnut", 48, 24, 18, "table"),
        ("cab-wall-30", "30\" Wall Cabinet", "Cabinet", "White Oak", 30, 24, 12, "two_door"),
    ]
    products: List[Product] = []
    for pid, name, cat, mat, w, h, d, kind in specs:
        dxf_name = f"{pid}.dxf"
        _make_sample_dxf(DXF_DIR / dxf_name, kind, float(w), float(h))
        p = Product(
            id=pid, name=name, category=cat, material=mat,
            width_in=float(w), height_in=float(h), depth_in=float(d),
            dxf_file=dxf_name,
            description=f"{mat} {cat.lower()}, {w}\"×{h}\"×{d}\". Demo product — adjust to your spec.",
        )
        price, note = estimate_price(p)
        p.price, p.price_note = price, note
        products.append(p)
    return products
