#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  PIF DXF Material Adjuster + Showroom — Streamlit app             ║
║  Parametric Interaction Framework                                 ║
║                                                                  ║
║  Two tools in one app:                                            ║
║    • Adjuster — adapt a DXF's slots/tabs/dados to real material.   ║
║    • Showroom — 2D gallery of the projects we offer, with prices;  ║
║      select a product to open it in the 3D configurator.           ║
║                                                                  ║
║  Run:  streamlit run app.py                                        ║
║  © 2026 PIF — Parametric Interaction Framework                   ║
╚══════════════════════════════════════════════════════════════════╝
"""

from io import StringIO
from pathlib import Path

import streamlit as st

from pif_dxf_adjuster import DXFMaterialAdjuster, COMMON_THICKNESSES
import pif_showroom as shop

st.set_page_config(page_title="PIF Studio", page_icon="🛠️", layout="wide")

# Locations the 3D configurator host may live, once it's brought into the repo.
CONFIGURATOR_CANDIDATES = [
    Path(__file__).parent / "configurator_v6.html",
    Path(__file__).parent / "configurator" / "configurator_v6.html",
    Path(__file__).parent / "configurator.html",
]


# ─────────────────────────────────────────────────────────────
# CACHED HELPERS
# ─────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _preview_from_path(path_str: str, mtime: float, width_px: int = 480) -> bytes:
    # mtime is part of the cache key so edits invalidate the cached image.
    return shop.render_dxf_preview(Path(path_str), width_px=width_px)


def product_preview(product: shop.Product, width_px: int = 480):
    path = product.dxf_path
    if path and path.exists():
        try:
            return _preview_from_path(str(path), path.stat().st_mtime, width_px)
        except Exception as exc:
            st.caption(f"⚠️ Preview unavailable: {exc}")
    return None


def find_configurator() -> Path | None:
    return next((p for p in CONFIGURATOR_CANDIDATES if p.exists()), None)


# ─────────────────────────────────────────────────────────────
# ADJUSTER PAGE
# ─────────────────────────────────────────────────────────────

def page_adjuster():
    st.title("🔧 DXF Material Adjuster")
    st.write(
        "Upload a DXF, tell us the thickness it was designed for and the thickness "
        "of your actual material, and we'll resize the slots, tabs, dados and relief "
        "cuts to fit."
    )

    uploaded = st.file_uploader("DXF file", type=["dxf"])

    col1, col2, col3 = st.columns(3)
    labels = list(COMMON_THICKNESSES.keys())
    with col1:
        design_label = st.selectbox("Designed for", labels, index=labels.index('3/4" (18mm)'))
        design = COMMON_THICKNESSES[design_label]
        if st.checkbox("Custom design thickness"):
            design = st.number_input("Design thickness (in)", value=float(design), step=0.001, format="%.4f")
    with col2:
        actual = st.number_input("Actual material thickness (in)", value=0.71, step=0.001, format="%.4f")
    with col3:
        tolerance = st.number_input("Match tolerance (in)", value=0.02, step=0.005, format="%.4f")

    if uploaded is None:
        st.info("Upload a DXF to begin.")
        return

    if st.button("Adjust DXF", type="primary"):
        try:
            text = uploaded.getvalue().decode("utf-8", errors="replace")
            adjuster = DXFMaterialAdjuster("uploaded.dxf", design, actual, tolerance)
            adjuster.load_from_stream(StringIO(text))
            adjuster.adjust()
        except Exception as exc:
            st.error(f"Could not process file: {exc}")
            return

        st.success("Adjustment complete.")
        st.code(adjuster.log.summary_text(design, actual), language="text")

        out = adjuster.save_to_stream()
        st.download_button(
            "⬇️ Download adjusted DXF",
            data=out.getvalue(),
            file_name=uploaded.name.replace(".dxf", "_adjusted.dxf"),
            mime="application/dxf",
        )


# ─────────────────────────────────────────────────────────────
# SHOWROOM — GALLERY
# ─────────────────────────────────────────────────────────────

def page_showroom():
    products = st.session_state.catalog

    # Detail view takes over when a product is selected.
    if st.session_state.get("selected_product"):
        show_product_detail(products)
        return

    st.title("🛋️ Showroom")
    st.write("The projects we offer. Select a product to see specs, pricing, and the 3D view.")

    categories = ["All"] + sorted({p.category for p in products})
    chosen = st.selectbox("Filter by category", categories)
    visible = [p for p in products if chosen == "All" or p.category == chosen]

    if not visible:
        st.info("No products in this category yet.")
        return

    cols_per_row = 3
    for row_start in range(0, len(visible), cols_per_row):
        row = visible[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, product in zip(cols, row):
            with col:
                img = product_preview(product, width_px=360)
                if img:
                    st.image(img, use_container_width=True)
                st.subheader(product.name)
                st.caption(f"{product.category} · {product.material}")
                st.write(f"**{product.price_text}**")
                st.caption(product.dimensions_text)
                if st.button("View details →", key=f"open-{product.id}"):
                    st.session_state.selected_product = product.id
                    st.rerun()


# ─────────────────────────────────────────────────────────────
# SHOWROOM — PRODUCT DETAIL  (+ 3D handoff)
# ─────────────────────────────────────────────────────────────

def show_product_detail(products):
    product = shop.get_product(products, st.session_state.selected_product)
    if product is None:
        st.session_state.selected_product = None
        st.rerun()
        return

    if st.button("← Back to showroom"):
        st.session_state.selected_product = None
        st.rerun()

    st.title(product.name)
    st.caption(f"{product.category} · {product.material} · {product.dimensions_text}")

    left, right = st.columns([3, 2])
    with left:
        img = product_preview(product, width_px=640)
        if img:
            st.image(img, use_container_width=True, caption="2D preview (from DXF cut file)")
    with right:
        st.markdown("### Price")
        st.markdown(f"## {product.price_text}")
        if product.price_note:
            st.caption(product.price_note)

        new_price = st.number_input(
            "Set price (USD)", value=float(product.price), min_value=0.0, step=5.0, format="%.2f"
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 Save price"):
                product.price = round(new_price, 2)
                product.price_note = "Set manually."
                shop.update_product(products, product)
                st.success("Price saved.")
                st.rerun()
        with c2:
            ai_label = "✨ Suggest with AI" if shop.ai_price_available() else "✨ Estimate price"
            if st.button(ai_label):
                price, note = shop.estimate_price_ai(product)
                if price is not None:
                    product.price = price
                    product.price_note = note
                    shop.update_product(products, product)
                    st.rerun()
        if not shop.ai_price_available():
            st.caption(
                "Tip: set an `ANTHROPIC_API_KEY` to let Claude suggest market prices. "
                "Without it, a built-in material/size estimate is used."
            )

        if product.description:
            st.markdown("### Description")
            st.write(product.description)

    st.divider()
    render_3d_section(product)


def render_3d_section(product: shop.Product):
    """The 3D configurator opens here, after a product is selected."""
    st.markdown("### 🧊 3D View")
    host = find_configurator()
    if host is not None:
        try:
            html = host.read_text(encoding="utf-8")
            # Hand the selected product's parameters to the configurator.
            params = (
                f'<script>window.PIF_PRODUCT = {{'
                f'"id":"{product.id}","name":"{product.name}",'
                f'"category":"{product.category}","material":"{product.material}",'
                f'"width":{product.width_in},"height":{product.height_in},'
                f'"depth":{product.depth_in}}};</script>'
            )
            st.components.v1.html(params + html, height=620, scrolling=False)
            st.caption(f"3D configurator: {host.name}")
        except Exception as exc:
            st.warning(f"Configurator found but failed to load: {exc}")
        return

    st.info(
        "**3D view activates once the configurator is added to this repo.**\n\n"
        "The 2D → 3D flow is wired and ready: when a product is selected here, its "
        "parameters are passed to the Three.js configurator. Drop "
        "`configurator_v6.html` (or `configurator/configurator_v6.html`) into the repo "
        "and this panel will render the live 3D model for the selected product."
    )
    st.json({
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "material": product.material,
        "width_in": product.width_in,
        "height_in": product.height_in,
        "depth_in": product.depth_in,
    })
    st.caption("↑ These parameters are what gets handed to the 3D configurator.")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    if "catalog" not in st.session_state:
        st.session_state.catalog = shop.load_catalog()
    if "selected_product" not in st.session_state:
        st.session_state.selected_product = None

    st.sidebar.title("🛠️ PIF Studio")
    page = st.sidebar.radio("Tool", ["Showroom", "Adjuster"], label_visibility="collapsed")
    st.sidebar.caption("Parametric Interaction Framework")

    if page == "Adjuster":
        page_adjuster()
    else:
        page_showroom()


if __name__ == "__main__":
    main()
