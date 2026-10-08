# author: d.koch
# coding: utf-8
# naming: pep-0008
# typing: pep-0484
# docstring: pep-0257
# indentation: 4 spaces

""" src/csa_ui_import__page.py
Full page panel detection view: source fetching and contour parameter controls.
"""

# - - - IMPORT - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import cv2
import os
import shutil
import urllib.request

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

from nicegui import ui

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def render_import_page_view(container, state: dict, extractor_engine, project_dir: str, get_asset_url_fn, render_overlays_fn):
    """Renders the initial comic page panel detection workspace with interactive slider controls."""
    container.clear()

    with container, ui.row().classes("w-full h-full gap-4 items-start"):
        # Image Display Area
        with ui.column().classes("flex-1 h-full gap-2 items-center justify-center"):
            url_input = ui.input(
                label="Comic Page Image URL or Local File Path",
                value="https://www.bedetheque.com/media/Planches/PlancheA_3196.jpg"
            ).classes("w-full").props("dark active")

            canvas_box = ui.element("div").classes("relative border border-slate-700 rounded overflow-hidden bg-black/40 min-h-[350px] w-full flex-1 flex items-center justify-center")

        # Sidebar Controls
        with ui.card().classes("w-80 h-full p-3 bg-slate-800 text-white gap-3 border border-slate-700 overflow-y-auto"):
            lang_select = ui.select(
                label="OCR Default Language",
                options={"fra": "French (fra)", "eng": "English (eng)", "spa": "Spanish (spa)", "deu": "German (deu)"},
                value=state.get("ocr_lang", "fra")
            ).classes("w-full").props("dark active")

            ui.label("Detection Sensitivity").classes("font-bold text-sm text-blue-400 border-b border-slate-700 pb-1")

            # Slider 1: Kernel Size (Border Closing)
            with ui.column().classes("w-full gap-0"):
                with ui.row().classes("w-full justify-between items-center text-xs"):
                    ui.label("Kernel Size (Border Closing)").classes("text-slate-300 font-semibold")
                    kernel_val_lbl = ui.label("5 px").classes("font-mono text-blue-400 font-bold")

                kernel_slider = ui.slider(min=1, max=10, value=2, step=1).props("dark markers snap label-always")
                kernel_slider.on("update:model-value", lambda e: kernel_val_lbl.set_text(f"{int(e.args)} px"))

            # Slider 2: Min Area Ratio (%)
            with ui.column().classes("w-full gap-0 mt-2"):
                with ui.row().classes("w-full justify-between items-center text-xs"):
                    ui.label("Min Area Ratio (%)").classes("text-slate-300 font-semibold")
                    area_val_lbl = ui.label("1.0%").classes("font-mono text-blue-400 font-bold")

                area_slider = ui.slider(min=0.005, max=0.08, value=0.01, step=0.005).props("dark markers snap label-always")
                area_slider.on("update:model-value", lambda e: area_val_lbl.set_text(f"{float(e.args)*100:.1f}%"))

            btn_load = ui.button("Fetch & Analyze Page", color="primary", icon="download").classes("w-full mt-3")

        def refresh_canvas():
            img_web_url = get_asset_url_fn(state["source_rel_path"], project_dir)
            render_overlays_fn(img_web_url, state["boxes"], canvas_box, state["cv_img"], refresh_canvas)

        async def run_edge_analysis():
            target_url = url_input.value.strip()
            if not target_url:
                ui.notify("Please enter a valid URL or path.", type="warning")
                return

            btn_load.props("loading")
            sources_dir = os.path.join(project_dir, "assets", "sources")
            os.makedirs(sources_dir, exist_ok=True)

            filename = os.path.basename(target_url.split("?")[0]) or "imported_source.jpg"
            state["source_local_path"] = os.path.join(sources_dir, filename)
            state["source_rel_path"] = f"assets/sources/{filename}"

            if target_url.startswith(("http://", "https://")):
                req = urllib.request.Request(
                    target_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                with urllib.request.urlopen(req) as resp, open(state["source_local_path"], "wb") as out:
                    shutil.copyfileobj(resp, out)
            elif os.path.exists(target_url):
                shutil.copy(target_url, state["source_local_path"])

            state["cv_img"] = cv2.imread(state["source_local_path"])
            if state["cv_img"] is None:
                ui.notify("Could not decode image.", type="negative")
                btn_load.props(remove="loading")
                return

            state["ocr_lang"] = lang_select.value
            state["boxes"] = extractor_engine.detect_panel_boxes(
                state["cv_img"],
                kernel_size=int(kernel_slider.value),
                min_area_ratio=float(area_slider.value)
            )

            refresh_canvas()
            btn_load.props(remove="loading")
            ui.notify(f"Detected {len(state['boxes'])} panels!", type="positive")

        # Wire Up Click & Live Slider Change Event Triggers
        btn_load.on("click", run_edge_analysis)
        kernel_slider.on("change", lambda: run_edge_analysis())
        area_slider.on("change", lambda: run_edge_analysis())

