#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  PIF DXF Adjuster — WEB APP                                     ║
║                                                                  ║
║  Fully automated web service. Customer does everything:          ║
║    1. Uploads their DXF                                          ║
║    2. Selects or enters material thicknesses                     ║
║    3. Clicks "Adjust"                                            ║
║    4. Downloads the corrected file + report                      ║
║                                                                  ║
║  To run locally:                                                 ║
║    pip install streamlit ezdxf                                   ║
║    streamlit run app.py                                          ║
║                                                                  ║
║  To deploy free:                                                 ║
║    Push to GitHub → connect to streamlit.io/cloud                ║
║                                                                  ║
║  © 2026 PIF — Parametric Interaction Framework                   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import tempfile
import json
import zipfile
from pathlib import Path
from io import BytesIO
from datetime import datetime

from pif_dxf_adjuster import DXFMaterialAdjuster, COMMON_THICKNESSES

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="PIF DXF Material Adjuster",
    page_icon="🔧",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

.stApp {
    background: #07080a;
    font-family: 'Plus Jakarta Sans', sans-serif;
}

#MainMenu, footer, header { visibility: hidden; }

.hero {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
    position: relative;
}
.hero::before {
    content: '';
    position: absolute;
    top: 0; left: 50%;
    transform: translateX(-50%);
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(255,209,102,0.06) 0%, transparent 70%);
    pointer-events: none;
}
.hero-badge {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #ffd166;
    background: rgba(255,209,102,0.08);
    border: 1px solid rgba(255,209,102,0.15);
    padding: 5px 14px;
    border-radius: 20px;
    margin-bottom: 1rem;
}
.hero h1 {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #ffd166, #ef476f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0.5rem 0;
}
.hero p {
    color: #888;
    font-size: 0.95rem;
}

.step-box {
    background: #0d0e12;
    border: 1px solid #1a1b20;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}
.step-number {
    background: #2d6a4f;
    color: white;
    width: 28px; height: 28px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.85rem;
    margin-right: 8px;
}

.result-card {
    background: #0d2818;
    border: 1px solid #2d6a4f;
    border-radius: 12px;
    padding: 1.5rem;
    margin-top: 1rem;
}

.app-footer {
    text-align: center;
    padding: 2rem 0;
    color: #444;
    font-size: 0.75rem;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
    <div class="hero-badge">Parametric Interaction Framework</div>
    <h1>DXF Material Adjuster</h1>
    <p>Adjust slots, tabs, and dados in your CNC files<br>to match your actual material thickness.</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# STEP 1: FILE UPLOAD
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="step-box">
    <span class="step-number">1</span>
    <strong style="color: #fff;">Upload Your DXF File</strong>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Choose a DXF file",
    type=["dxf"],
    help="Upload the DXF file you purchased or received. Max 50MB.",
    label_visibility="collapsed",
)


# ─────────────────────────────────────────────────────────────
# STEP 2: THICKNESS INPUTS
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="step-box">
    <span class="step-number">2</span>
    <strong style="color: #fff;">Set Material Thicknesses</strong>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Design Thickness** (what the file was made for)")
    design_preset = st.selectbox(
        "Common sizes",
        options=["Custom"] + list(COMMON_THICKNESSES.keys()),
        key="design_preset",
        label_visibility="collapsed",
    )
    if design_preset == "Custom":
        design_thickness = st.number_input(
            "Design thickness (inches)",
            min_value=0.01, max_value=5.0, value=0.75, step=0.001,
            format="%.4f", key="design_custom",
        )
    else:
        design_thickness = COMMON_THICKNESSES[design_preset]
        st.info(f"→ {design_thickness:.4f}\"")

with col2:
    st.markdown("**Actual Thickness** (measured with calipers)")
    actual_thickness = st.number_input(
        "Actual thickness (inches)",
        min_value=0.01, max_value=5.0, value=0.72, step=0.001,
        format="%.4f", key="actual_custom",
    )

# Show delta
if design_thickness and actual_thickness:
    delta = actual_thickness - design_thickness
    if abs(delta) < 0.0001:
        st.success("✅ Thicknesses match — no adjustment needed!")
    else:
        direction = "thicker" if delta > 0 else "thinner"
        st.warning(f"Material is {abs(delta):.4f}\" {direction} than design → joints will be adjusted")


# ─────────────────────────────────────────────────────────────
# STEP 3: ADJUST
# ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="step-box">
    <span class="step-number">3</span>
    <strong style="color: #fff;">Adjust & Download</strong>
</div>
""", unsafe_allow_html=True)

tolerance = st.slider(
    "Detection tolerance (inches)",
    min_value=0.005, max_value=0.05, value=0.02, step=0.005,
    help="How close a feature must be to the design thickness to be detected. Default 0.02\" works for most files.",
)

if st.button("🔧 Adjust My DXF", type="primary", use_container_width=True, disabled=uploaded_file is None):
    if uploaded_file is None:
        st.error("Please upload a DXF file first.")
    elif abs(design_thickness - actual_thickness) < 0.0001:
        st.info("Thicknesses match — nothing to adjust.")
    else:
        with st.spinner("Analyzing and adjusting your DXF..."):
            try:
                # Save upload to temp file
                with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                # Run adjuster
                adjuster = DXFMaterialAdjuster(
                    tmp_path, design_thickness, actual_thickness, tolerance
                )
                adjuster.load()
                adjuster.adjust()

                # Generate outputs
                output_stream = adjuster.save_to_stream()
                report_text = adjuster.log.summary_text(design_thickness, actual_thickness)

                # Create ZIP with both files
                zip_buffer = BytesIO()
                base_name = Path(uploaded_file.name).stem
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr(f"{base_name}_adjusted.dxf", output_stream.getvalue())
                    zf.writestr(f"{base_name}_report.txt", report_text)
                zip_buffer.seek(0)

                # Results
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                st.markdown("### ✅ Adjustment Complete")

                stats = adjuster.log.stats
                st.markdown(f"""
                - **Entities scanned:** {stats['entities_scanned']}
                - **Features adjusted:** {stats['entities_modified']}
                - **Line pairs:** {stats['lines_adjusted']}
                - **Tab rectangles:** {stats['polylines_adjusted']}
                - **Relief cuts:** {stats['circles_adjusted']}
                """)

                st.download_button(
                    label="📥 Download Adjusted DXF + Report",
                    data=zip_buffer,
                    file_name=f"{base_name}_adjusted.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

                with st.expander("📋 View Full Report"):
                    st.code(report_text, language=None)

                st.markdown('</div>', unsafe_allow_html=True)

                # Cleanup
                import os
                os.unlink(tmp_path)

            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
                st.info("If this persists, try re-exporting your DXF as R2013 format.")


# ─────────────────────────────────────────────────────────────
# FAQ
# ─────────────────────────────────────────────────────────────

with st.expander("❓ Frequently Asked Questions"):
    st.markdown("""
    **What does this tool do?**
    It finds features in your DXF file (slots, tabs, dados, relief cuts) that were designed 
    for a specific material thickness and adjusts them to match your actual measured material.

    **What if no features are detected?**
    Try adjusting the tolerance slider up slightly. Some files may use 
    non-standard geometry that requires manual adjustment.

    **Is my file safe?**
    Your file is processed in memory and deleted immediately after. We do not store, 
    share, or access your files after processing.

    **What DXF versions are supported?**
    DXF R12 through R2018. If your file fails to load, try re-exporting as DXF R2013.

    **How do I measure my actual material thickness?**
    Use digital calipers. Measure in 3-4 spots and use the average. Material thickness 
    can vary across a single sheet.
    """)


# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="app-footer">
    <p>
        PIF DXF Material Adjuster v1.0<br>
        Parametric Interaction Framework · {datetime.now().year}<br>
        <span style="color:#222;">Built for CNC makers who demand precision.</span>
    </p>
</div>
""", unsafe_allow_html=True)
