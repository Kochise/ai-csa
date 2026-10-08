# author: d.koch
# coding: utf-8
# naming: pep-0008
# typing: pep-0484
# docstring: pep-0257
# indentation: 4 spaces

""" src/csa_ui.py
Comic Strip Animator - Main UI Workbench Page & Render Layout
"""

# - - - IMPORT - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import asyncio
import cv2
import json
import numpy as np
import os
import requests
import shutil
import time
import urllib.request
import webbrowser

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

from datetime import datetime
from nicegui import run, ui

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

from csa_project import (
    load_project,
    save_project,
    load_settings,
    save_settings,
    list_available_projects,
    create_new_project_folder,
    get_node_display_title,
    get_asset_url,
    get_video_url,
    resolve_project_file_path
)

from csa_ui_nodes import (
    move_node,
    toggle_panel_nesting,
    remove_sequence,
    add_new_sequence,
    reorder_nodes_by_index
)

from csa_ui_import import open_import_dialog as launch_import_wizard

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Image Lightbox & Preview Helpers
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def open_image_lightbox(img_url: str, title: str = "Image Preview"):
    if not img_url:
        ui.notify("No valid image URL provided for preview.", type="warning")
        return

    with ui.dialog() as dialog, ui.card().classes("w-[90vw] h-[90vh] p-2 bg-slate-900 flex flex-col items-center justify-between text-white"):
        with ui.row().classes("w-full justify-between items-center px-2 py-1 border-b border-slate-700"):
            ui.label(title).classes("font-bold text-base")
            ui.button(icon="close", on_click=dialog.close).props("flat color=white round dense")

        with ui.element("div").classes("w-full h-full overflow-auto flex items-center justify-center p-2 bg-black/60 rounded"):
            ui.image(img_url).classes("max-w-full max-h-full object-contain cursor-zoom-in")

    dialog.open()

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def toggle_row_enabled(node: dict, row_card, project_data: dict, project_id: str):
    node["enabled"] = not node.get("enabled", True)
    if node["enabled"]:
        row_card.classes(remove="opacity-40 bg-gray-200", add="bg-white")
    else:
        row_card.classes(remove="bg-white", add="opacity-40 bg-gray-200")
    save_project(project_data, project_id)

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def open_in_comfyui(node: dict):
    COMFY_URL = "http://localhost:8188"
    try:
        res = requests.get(f"{COMFY_URL}/system_stats", timeout=1.5)
        if res.status_code == 200:
            ui.notify(f"Opening {get_node_display_title(node)} in ComfyUI...", type="positive")
            webbrowser.open_new_tab(COMFY_URL)
        else:
            ui.notify("ComfyUI server returned non-200 status.", type="warning")
    except Exception:
        ui.notify("Could not connect to ComfyUI on http://localhost:8188.", type="warning")

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def cycle_video_version(node: dict, direction: int, media_container, project_data: dict, project_id: str, project_dir: str):
    videos = node.get("plan_videos", [])
    if not videos:
        return

    curr_idx = node.get("active_video_index", 0)
    new_idx = (curr_idx + direction) % len(videos)
    node["active_video_index"] = new_idx
    node["plan_video"] = videos[new_idx]

    save_project(project_data, project_id)
    render_video_preview_container(node, media_container, project_data, project_id, project_dir)

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def render_video_preview_container(node: dict, media_container, project_data: dict, project_id: str, project_dir: str):
    media_container.clear()
    raw_videos = node.get("plan_videos", [])
    if not raw_videos and node.get("plan_video"):
        raw_videos = [node["plan_video"]]

    valid_videos = []
    for rel_path in raw_videos:
        full_path = resolve_project_file_path(rel_path, project_dir)
        if os.path.exists(full_path):
            valid_videos.append(rel_path)

    node["plan_videos"] = valid_videos
    curr_idx = node.get("active_video_index", 0)
    if curr_idx >= len(valid_videos):
        curr_idx = max(0, len(valid_videos) - 1)
        node["active_video_index"] = curr_idx

    active_video = valid_videos[curr_idx] if valid_videos else ""
    video_url = get_video_url(active_video, project_dir)

    with media_container:
        if video_url:
            with ui.row().classes("items-center gap-1"):
                left_btn = ui.button(icon="chevron_left").props("flat round dense size=sm color=grey-7")
                left_btn.on("click", lambda: cycle_video_version(node, -1, media_container, project_data, project_id, project_dir))
                if len(valid_videos) <= 1:
                    left_btn.disable()

                with ui.column().classes("items-center relative"):
                    vid = ui.video(video_url).classes("w-28 h-16 rounded shadow object-cover")
                    vid.tooltip("Plan Preview: Hover/Play to preview rendered video.")
                    ui.badge(f"{curr_idx + 1}/{len(valid_videos)}", color="slate-700").classes("text-3xs absolute -top-2 -right-2 px-1")

                right_btn = ui.button(icon="chevron_right").props("flat round dense size=sm color=grey-7")
                right_btn.on("click", lambda: cycle_video_version(node, 1, media_container, project_data, project_id, project_dir))
                if len(valid_videos) <= 1:
                    right_btn.disable()
        else:
            lbl = ui.label("No Plan Rendered").classes("text-xs text-gray-400 italic")
            lbl.tooltip("Click the red Record button to render video.")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Generation Execution
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _blocking_video_generation(video_engine, node: dict, out_path: str):
    video_engine.generate_plan_video(node, out_path)

async def trigger_node_generation(node: dict, progress_bar, media_container, video_engine, project_data: dict, project_id: str, project_dir: str):
    node_title = get_node_display_title(node)
    ui.notify(f"Generating video plan: {node_title}", type="info")

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    rel_path = f"renders/plans/{node['id']}_{timestamp}.mp4"
    out_path = resolve_project_file_path(rel_path, project_dir)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    progress_bar.set_visibility(True)
    try:
        await run.cpu_bound(_blocking_video_generation, video_engine, node, out_path)
        if "plan_videos" not in node or not isinstance(node["plan_videos"], list):
            node["plan_videos"] = []

        node["plan_videos"].append(rel_path)
        node["active_video_index"] = len(node["plan_videos"]) - 1
        node["plan_video"] = rel_path

        save_project(project_data, project_id)
        ui.notify(f"Render complete for {node_title}!", type="positive")
        render_video_preview_container(node, media_container, project_data, project_id, project_dir)
    except Exception as e:
        ui.notify(f"Generation error: {str(e)}", type="negative")
    finally:
        progress_bar.set_visibility(False)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Import Wizard & Canvas Overlays (Exact Pre-Refactor Match)
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def render_import_dialog(project_data: dict, project_id: str, project_dir: str, extractor_engine, refresh_fn):
    launch_import_wizard(
        project_data=project_data,
        project_id=project_id,
        project_dir=project_dir,
        extractor_engine=extractor_engine,
        save_project_fn=save_project,
        refresh_fn=refresh_fn,
        get_asset_url_fn=get_asset_url,
        open_lightbox_fn=open_image_lightbox,
        render_overlays_fn=render_canvas_overlays
    )

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def find_gutter_edges_outward(cv_img, split_pos: int, axis: str = "x", search_radius: int = 25):
    """Scans outward from split_pos to find white gutter borders."""
    if cv_img is None:
        return split_pos, split_pos

    h, w = cv_img.shape[:2]
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY) if len(cv_img.shape) == 3 else cv_img

    if axis == "x":
        split_pos = max(search_radius, min(w - search_radius - 1, split_pos))
        profile = [np.mean(gray[:, pos]) for pos in range(split_pos - search_radius, split_pos + search_radius + 1)]
        peak_idx = int(np.argmax(profile))
        gutter_center = (split_pos - search_radius) + peak_idx
        return max(0, gutter_center - 2), min(w, gutter_center + 2)
    else:
        split_pos = max(search_radius, min(h - search_radius - 1, split_pos))
        profile = [np.mean(gray[pos, :]) for pos in range(split_pos - search_radius, split_pos + search_radius + 1)]
        peak_idx = int(np.argmax(profile))
        gutter_center = (split_pos - search_radius) + peak_idx
        return max(0, gutter_center - 2), min(h, gutter_center + 2)

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def split_panel(index: int, axis: str, boxes: list, cv_img, callback):
    """Splits target panel box and snaps boundaries to white gutter space."""
    if index < 0 or index >= len(boxes):
        return

    target = boxes.pop(index)
    h_img, w_img = cv_img.shape[:2] if cv_img is not None else (1000, 1000)

    if axis == "vertical":
        half_w = target["w"] / 2
        mid_x_px = int((target["x"] + half_w) * w_img)
        left_px, right_px = find_gutter_edges_outward(cv_img, mid_x_px, axis="x")

        left_pct = round(left_px / w_img, 4)
        right_pct = round(right_px / w_img, 4)

        box1 = {"x": target["x"], "y": target["y"], "w": round(left_pct - target["x"], 4), "h": target["h"]}
        box2 = {"x": right_pct, "y": target["y"], "w": round((target["x"] + target["w"]) - right_pct, 4), "h": target["h"]}
    else:
        half_h = target["h"] / 2
        mid_y_px = int((target["y"] + half_h) * h_img)
        top_px, bottom_px = find_gutter_edges_outward(cv_img, mid_y_px, axis="y")

        top_pct = round(top_px / h_img, 4)
        bottom_pct = round(bottom_px / h_img, 4)

        box1 = {"x": target["x"], "y": target["y"], "w": target["w"], "h": round(top_pct - target["y"], 4)}
        box2 = {"x": target["x"], "y": bottom_pct, "w": target["w"], "h": round((target["x"] + target["h"]) - bottom_pct, 4)}

    boxes.insert(index, box1)
    boxes.insert(index + 1, box2)
    if callback:
        callback()

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def render_canvas_overlays(img_url: str, boxes: list, canvas_container, cv_img, on_boxes_updated_fn=None):
    """Renders SVG panel overlays and split buttons mapped 1:1 to the image canvas."""
    canvas_container.clear()

    with canvas_container:
        # Wrapper strictly bounded to image aspect ratio using fit-content
        with ui.element("div").classes("relative w-fit h-fit max-h-[60vh] mx-auto overflow-hidden rounded shadow-sm flex items-center justify-center"):
            # Native image tag inside NiceGUI html element ensures 1:1 overlay mapping without Quasar flex overrides
            ui.html(f'<img src="{img_url}" class="max-h-[60vh] max-w-full object-contain block pointer-events-none" />')

            # Layer 1: SVG Panel Boundaries & Text with Black Stroke Outline
            svg_lines = [
                '<svg class="absolute inset-0 w-full h-full pointer-events-none">',
                '<style>',
                '  .panel-num-text {',
                '    font-weight: 900;',
                '    fill: #facc15;',  # Bright Yellow Fill
                '    stroke: #000000;',
                '    stroke-width: 3.5px;',
                '    stroke-linejoin: round;',
                '    paint-order: stroke fill;',
                '    user-select: none;',
                '  }',
                '</style>'
            ]

            for idx, b in enumerate(boxes):
                x_pct, y_pct = b["x"] * 100, b["y"] * 100
                w_pct, h_pct = b["w"] * 100, b["h"] * 100

                cx_pct = x_pct + (w_pct / 2)
                cy_pct = y_pct + (h_pct / 2)
                font_size = max(22, int(h_pct * 3.0))

                # Dashed boundary box
                svg_lines.append(
                    f'<rect x="{x_pct}%" y="{y_pct}%" width="{w_pct}%" height="{h_pct}%" '
                    f'fill="rgba(59, 130, 246, 0.18)" stroke="#3b82f6" stroke-width="2.5" '
                    f'stroke-dasharray="8,5" />'
                )

                # Centered panel number with black stroke border
                svg_lines.append(
                    f'<text x="{cx_pct}%" y="{cy_pct}%" class="panel-num-text" '
                    f'font-size="{font_size}px" text-anchor="middle" '
                    f'dominant-baseline="central">{idx+1}</text>'
                )

            svg_lines.append('</svg>')
            ui.html("".join(svg_lines)).classes("absolute inset-0 pointer-events-none")

            # Layer 2: Bumped Inward Split Controls
            for idx, b in enumerate(boxes):
                x_pct, y_pct = b["x"] * 100, b["y"] * 100
                w_pct, h_pct = b["w"] * 100, b["h"] * 100

                # Right Side Split Icon -> Horizontal Cut
                r_x = x_pct + (w_pct * 0.90)
                r_y = y_pct + (h_pct * 0.50)
                h_btn = ui.button(
                    icon="content_cut",
                    on_click=lambda _, i=idx: split_panel(i, axis="horizontal", boxes=boxes, cv_img=cv_img, callback=on_boxes_updated_fn)
                ).props("round dense size=xs color=purple-4 elevation-6").classes(
                    "absolute z-20 transform -translate-x-1/2 -translate-y-1/2 shadow-2xl border-2 border-black"
                )
                h_btn.style(f"left: {r_x}%; top: {r_y}%;")
                h_btn.tooltip("Split Horizontally (Create Row Below)")

                # Bottom Side Split Icon -> Vertical Cut
                b_x = x_pct + (w_pct * 0.50)
                b_y = y_pct + (h_pct * 0.90)
                v_btn = ui.button(
                    icon="content_cut",
                    on_click=lambda _, i=idx: split_panel(i, axis="vertical", boxes=boxes, cv_img=cv_img, callback=on_boxes_updated_fn)
                ).props("round dense size=xs color=blue-4 elevation-6").classes(
                    "absolute z-20 transform -translate-x-1/2 -translate-y-1/2 rotate-90 shadow-2xl border-2 border-black"
                )
                v_btn.style(f"left: {b_x}%; top: {b_y}%;")
                v_btn.tooltip("Split Vertically (Create Column Beside)")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Workbench Tree Layout Rendering
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def render_node_row(node: dict, is_child: bool, project_data: dict, project_id: str, project_dir: str, video_engine, extractor_engine, refresh_fn):
    indent_class = "ml-8 border-l-4 border-blue-400 pl-3" if is_child else "border-b-2 border-slate-300"
    bg_class = "bg-white" if node.get("enabled", True) else "opacity-40 bg-gray-200"

    with ui.card().classes(f"w-full mb-2 p-2 transition-all relative overflow-hidden sortable-item {indent_class} {bg_class}") as row_card:
        progress_bar = ui.linear_progress(value=None, show_value=False).classes("w-full absolute top-0 left-0 h-1")
        progress_bar.set_visibility(False)

        with ui.grid(columns=12).classes("w-full items-center gap-2"):
            # Col 1-3: Controls & Drag Handle
            with ui.column().classes("col-span-3 justify-center gap-0"):
                with ui.row().classes("items-center gap-1"):
                    if node.get("type") != "root_lore":
                        ui.icon("drag_indicator").classes("drag-handle cursor-grab text-slate-400 hover:text-slate-700")

                    eye_btn = ui.button(icon="visibility", color="blue-7").props("flat round dense")
                    eye_btn.on("click", lambda: toggle_row_enabled(node, row_card, project_data, project_id))

                    record_btn = ui.button(icon="fiber_manual_record", color="red-6").props("flat round dense")

                    if node.get("type") == "panel_child":
                        comfy_btn = ui.button(icon="palette", color="purple-7").props("flat round dense")
                        comfy_btn.on("click", lambda: open_in_comfyui(node))
                        nest_btn = ui.button(icon="unfold_less" if is_child else "unfold_more").props("flat round dense color=deep-orange-7")
                        nest_btn.on("click", lambda: toggle_panel_nesting(node["id"], project_data, project_id, refresh_fn))

                    elif node.get("type") == "sequence_parent":
                        del_seq_btn = ui.button(icon="delete", color="red-7").props("flat round dense")
                        del_seq_btn.on("click", lambda: remove_sequence(node["id"], project_data, project_id, refresh_fn))

                ui.label(get_node_display_title(node)).classes("font-bold text-sm truncate pl-1")

            # Col 4-8: Captions & Guidance
            with ui.column().classes("col-span-5 justify-center"):
                if node.get("type") == "root_lore":
                    ui.input(
                        label="Global Lore Description",
                        value=node.get("world_description") or node.get("description", "")
                    ).classes("w-full").on("change", lambda e: node.update({"world_description": e.args}) or save_project(project_data, project_id))

                elif node.get("type") == "sequence_parent":
                    ui.input(
                        label="Director Guidance & Ambient SFX",
                        value=node.get("director_notes", "")
                    ).classes("w-full").on("change", lambda e: node.update({"director_notes": e.args}) or save_project(project_data, project_id))

                elif node.get("type") == "panel_child":
                    ui.input(
                        label="Extracted Dialogue / Captions",
                        value=node.get("extracted_text", "")
                    ).classes("w-full").on("change", lambda e: node.update({"extracted_text": e.args}) or save_project(project_data, project_id))

            # Col 9-10: Image Preview
            with ui.column().classes("col-span-2 items-center justify-center"):
                if node.get("type") == "panel_child":
                    img_url = get_asset_url(node.get("original_image", ""), project_dir)
                    if img_url:
                        frame_class = "w-14 h-20" if node.get("aspect_ratio") == "portrait" else "w-20 h-14"
                        ui.image(img_url).classes(f"{frame_class} rounded object-cover border shadow-sm cursor-pointer").on(
                            "click", lambda: open_image_lightbox(img_url, get_node_display_title(node))
                        )
                    else:
                        with ui.card().classes("w-16 h-16 bg-slate-100 flex items-center justify-center border-dashed border-2 border-slate-300"):
                            ui.label("No Image").classes("text-3xs text-slate-400 italic")
                else:
                    ui.label("-").classes("text-slate-300")

            # Col 11-12: Media Render Preview
            media_container = ui.column().classes("col-span-2 items-center justify-center")
            render_video_preview_container(node, media_container, project_data, project_id, project_dir)
            record_btn.on("click", lambda: trigger_node_generation(node, progress_bar, media_container, video_engine, project_data, project_id, project_dir))

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

@ui.refreshable
def render_workbench_content(project_data: dict, project_id: str, project_dir: str, video_engine, extractor_engine):
    with ui.column().classes("w-full p-4 max-w-7xl mx-auto"):
        with ui.grid(columns=12).classes("w-full px-2 mb-1 text-xs font-bold text-slate-500 uppercase tracking-wider"):
            ui.label("Controls & Row Title").classes("col-span-3")
            ui.label("Prompt / Guidance / Captions").classes("col-span-5")
            ui.label("Source Image").classes("col-span-2 text-center")
            ui.label("Video Plan Render").classes("col-span-2 text-center")

        root_node = project_data["nodes"][0] if project_data["nodes"] else None
        if root_node:
            render_node_row(root_node, False, project_data, project_id, project_dir, video_engine, extractor_engine, render_workbench_content.refresh)

            with ui.column().classes("w-full sortable-container gap-0"):
                for child in root_node.get("children", []):
                    render_node_row(child, False, project_data, project_id, project_dir, video_engine, extractor_engine, render_workbench_content.refresh)

                    if "children" in child:
                        for grand_child in child["children"]:
                            render_node_row(grand_child, True, project_data, project_id, project_dir, video_engine, extractor_engine, render_workbench_content.refresh)

    ui.run_javascript(f'''
        const el = document.querySelector('.sortable-container');
        if (el && !el._sortable) {{
            el._sortable = new Sortable(el, {{
                animation: 150,
                handle: '.drag-handle',
                ghostClass: 'bg-blue-100',
                onEnd: function (evt) {{
                    if (evt.oldIndex !== undefined && evt.newIndex !== undefined && evt.oldIndex !== evt.newIndex) {{
                        emitEvent('reorder_nodes', {{ oldIndex: evt.oldIndex, newIndex: evt.newIndex }});
                    }}
                }}
            }});
        }}
    ''')

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def build_workbench_ui(project_data: dict, project_id: str, project_dir: str, video_engine, extractor_engine):
    proj_name = project_data.get("project_name", project_id)
    ui.page_title(f"{proj_name} - CSA Workbench")

    ui.add_head_html('<script src="https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.0/Sortable.min.js"></script>')

    ui.on('reorder_nodes', lambda e: reorder_nodes_by_index(
        e.args['oldIndex'], e.args['newIndex'], project_data, project_id, render_workbench_content.refresh
    ))

    def switch_active_project(target_id: str):
        if target_id == project_id:
            return
        settings = load_settings()
        settings["active_project_id"] = target_id
        save_settings(settings)
        ui.navigate.to("/")

    # Left Drawer
    with ui.left_drawer(value=True).classes("bg-slate-900 text-white p-3 border-r border-slate-800") as drawer:
        with ui.row().classes("w-full justify-between items-center mb-4 pb-2 border-b border-slate-700"):
            ui.label("Projects").classes("text-lg font-bold tracking-wide")

        all_projects = list_available_projects()
        with ui.column().classes("w-full gap-2 overflow-y-auto"):
            for proj in all_projects:
                p_id = proj["id"]
                is_active = (p_id == project_id)
                card_bg = "bg-slate-800 border-2 border-blue-500" if is_active else "bg-slate-800/60 hover:bg-slate-800"

                with ui.card().classes(f"w-full p-2 cursor-pointer transition-all {card_bg}").on("click", lambda _, target=p_id: switch_active_project(target)):
                    with ui.row().classes("w-full items-center gap-2 no-wrap"):
                        thumb_url = get_asset_url(proj["thumbnail"], proj["folder"])
                        if thumb_url:
                            ui.image(thumb_url).classes("w-12 h-10 rounded object-cover border border-slate-600 flex-shrink-0")
                        else:
                            with ui.column().classes("w-12 h-10 bg-slate-700 rounded items-center justify-center border border-slate-600 flex-shrink-0"):
                                ui.icon("movie", size="xs").classes("text-slate-400")

                        with ui.column().classes("gap-0 overflow-hidden"):
                            ui.label(proj["name"]).classes("font-bold text-xs truncate w-full text-slate-100")
                            ui.label(f"{proj['panels_count']} Panels • {proj['renders_count']} Renders").classes("text-3xs text-slate-400")

    # Header Bar
    with ui.header().classes("bg-slate-800 text-white flex justify-between items-center px-4 py-2"):
        with ui.row().classes("items-center gap-2"):
            ui.button(icon="menu", on_click=drawer.toggle).props("flat color=white round dense")

            btn_import = ui.button("Import Comic", icon="file_upload", color="primary").props("flat color=white")
            btn_import.on("click", lambda: render_import_dialog(project_data, project_id, project_dir, extractor_engine, render_workbench_content.refresh))

            btn_add_seq = ui.button("Add Sequence", icon="post_add", color="primary").props("flat color=white")
            btn_add_seq.on("click", lambda: add_new_sequence(project_data, project_id, render_workbench_content.refresh))

        ui.label(proj_name).classes("text-lg font-bold tracking-wide text-center")

    render_workbench_content(project_data, project_id, project_dir, video_engine, extractor_engine)

