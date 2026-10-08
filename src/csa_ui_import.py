# author: d.koch
# coding: utf-8
# naming: pep-0008
# typing: pep-0484
# docstring: pep-0257
# indentation: 4 spaces

""" src/csa_ui_import.py
Main import wizard dialog container and view flow controller.
"""

# - - - IMPORT - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import cv2
import os
import time

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

from nicegui import ui

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

from csa_ui_import__page import render_import_page_view
from csa_ui_import__panel import render_import_panel_view

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def open_import_dialog(project_data: dict, project_id: str, project_dir: str, extractor_engine, save_project_fn, refresh_fn, get_asset_url_fn, open_lightbox_fn, render_overlays_fn):
    """Creates and opens the comic page import modal dialog."""
    wizard_dialog = ui.dialog()
    wizard_dialog.props("persistent")  # Enforce persistence so backdrop clicks do not close the wizard

    state = {
        "view_mode": "page",
        "current_panel_idx": 0,
        "source_local_path": "",
        "source_rel_path": "",
        "cv_img": None,
        "boxes": [],
        "panel_nodes": [],
        "ocr_lang": "fra"
    }

    with wizard_dialog, ui.card().classes("w-[1000px] max-w-[95vw] h-[85vh] p-5 bg-slate-900 text-white flex flex-col justify-between gap-3"):
        # Header Status
        with ui.row().classes("w-full justify-between items-center border-b border-slate-700 pb-2"):
            header_title = ui.label("Comic Page Import Wizard — Page Panel Detection").classes("text-xl font-bold")
            step_badge = ui.badge("Page View", color="blue-7").classes("text-sm font-mono")

        # View Workspace
        view_container = ui.column().classes("w-full flex-1 overflow-hidden relative justify-center items-center")

        def update_header():
            if state["view_mode"] == "page":
                header_title.text = "Comic Page Import Wizard — Page Panel Detection"
                step_badge.text = "Page View"
            else:
                p_idx = state["current_panel_idx"]
                header_title.text = f"Import Wizard — Panel {p_idx + 1} of {len(state['panel_nodes'])}: Text & Sound Review"
                step_badge.text = f"Panel {p_idx + 1}/{len(state['panel_nodes'])}"

        # Initial Render
        render_import_page_view(view_container, state, extractor_engine, project_dir, get_asset_url_fn, render_overlays_fn)

        # Footer Actions
        with ui.row().classes("w-full justify-between items-center pt-2 border-t border-slate-700"):
            ui.button("Cancel", on_click=wizard_dialog.close).props("flat color=white")

            with ui.row().classes("gap-2 items-center"):
                btn_back = ui.button("◄ Back", color="grey-7").classes("hidden")
                btn_next = ui.button("Next ➔", color="primary")

        async def proceed_next():
            if state["view_mode"] == "page":
                if not state["boxes"]:
                    ui.notify("Please detect panels before proceeding.", type="warning")
                    return

                btn_next.props("loading")
                assets_dir = os.path.join(project_dir, "assets")
                timestamp = int(time.time())
                state["panel_nodes"] = []
                h_img, w_img, _ = state["cv_img"].shape

                for idx, b in enumerate(state["boxes"], start=1):
                    x, y, w, h = int(b["x"] * w_img), int(b["y"] * h_img), int(b["w"] * w_img), int(b["h"] * h_img)
                    crop = state["cv_img"][y:y + h, x:x + w]

                    crop_filename = f"panel_{timestamp}_{idx:02d}.png"
                    crop_rel_path = f"assets/{crop_filename}"
                    cv2.imwrite(os.path.join(assets_dir, crop_filename), crop)

                    regions = extractor_engine.extract_bubbles_from_panel(crop, lang=state.get("ocr_lang", "fra"))
                    aspect_ratio = "portrait" if h >= w else "landscape"

                    state["panel_nodes"].append({
                        "id": f"panel_{timestamp}_{idx:02d}",
                        "type": "panel_child",
                        "enabled": True,
                        "title": f"Panel {idx:02d}",
                        "original_image": crop_rel_path,
                        "source_file": state["source_rel_path"],
                        "extracted_text": "",
                        "text_regions": regions,
                        "ocr_lang": state.get("ocr_lang", "fra"),
                        "aspect_ratio": aspect_ratio,
                        "children": []
                    })

                btn_next.props(remove="loading")
                state["view_mode"] = "panel"
                state["current_panel_idx"] = 0
                btn_back.classes(remove="hidden")
                update_header()
                render_import_panel_view(view_container, state, project_dir, get_asset_url_fn, open_lightbox_fn, update_header)

            elif state["view_mode"] == "panel":
                if state["current_panel_idx"] < len(state["panel_nodes"]) - 1:
                    state["current_panel_idx"] += 1
                    update_header()
                    render_import_panel_view(view_container, state, project_dir, get_asset_url_fn, open_lightbox_fn, update_header)
                else:
                    root_node = project_data["nodes"][0]
                    for p in state["panel_nodes"]:
                        p["extracted_text"] = " ".join([r["cleaned_text"] for r in p["text_regions"] if r.get("cleaned_text")])
                    root_node.setdefault("children", []).extend(state["panel_nodes"])
                    save_project_fn(project_data, project_id)
                    wizard_dialog.close()
                    refresh_fn()
                    ui.notify(f"Successfully imported {len(state['panel_nodes'])} panels!", type="positive")

        def proceed_back():
            if state["view_mode"] == "panel":
                if state["current_panel_idx"] > 0:
                    state["current_panel_idx"] -= 1
                    update_header()
                    render_import_panel_view(view_container, state, project_dir, get_asset_url_fn, open_lightbox_fn, update_header)
                else:
                    state["view_mode"] = "page"
                    btn_back.classes(add="hidden")
                    update_header()
                    render_import_page_view(view_container, state, extractor_engine, project_dir, get_asset_url_fn, render_overlays_fn)

        btn_next.on("click", proceed_next)
        btn_back.on("click", proceed_back)

    wizard_dialog.open()
