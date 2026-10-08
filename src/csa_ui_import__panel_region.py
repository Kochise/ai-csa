# author: d.koch
# coding: utf-8
# naming: pep-0008
# typing: pep-0484
# docstring: pep-0257
# indentation: 4 spaces

""" src/csa_ui_import__panel_region.py
Atomic UI component for editing an individual text/SFX region inside a panel.
"""

# - - - IMPORT - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import os

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

from nicegui import ui

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def make_repeating_button(icon_name: str, on_step_fn):
    """Point 2 Fix: Helper creating a button with hold-to-repeat action."""
    btn = ui.button(icon=icon_name).props("flat dense round size=xs color=white")

    # Wire both click and mousedown events for immediate step + fast holding
    btn.on("click", on_step_fn)
    btn.on("mousedown", lambda: ui.run_javascript(f'''
        if (window._spinner_timer) clearInterval(window._spinner_timer);
        window._spinner_timer = setInterval(() => {{
            emitEvent("spinner_repeat");
        }}, 90);
    '''))

    return btn

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def render_panel_region_card(region: dict, r_idx: int, default_lang: str, project_dir: str, get_asset_url_fn, open_lightbox_fn, on_delete_cb, on_change_cb, on_spinner_cb):
    """Renders region card with position spinners, readable debug thumbnail, and text area."""
    bbox = region.setdefault("bbox", [0.1, 0.1, 0.3, 0.2])
    region.setdefault("detected_lang", default_lang)

    def adjust_bbox(index: int, delta: float):
        bbox[index] = max(0.0, min(1.0, round(bbox[index] + delta, 3)))
        # Trigger light OCR reprocess and SVG overlay update without resetting the form UI tree
        on_spinner_cb()
        if "_debug_img" in region and region.get("debug_img_url"):
            region["_debug_img"].content = f'<img src="{region["debug_img_url"]}" class="h-28 w-auto max-w-full object-contain rounded border border-slate-600 cursor-pointer bg-black/80 hover:opacity-90 block mx-auto" />'

    with ui.card().classes("w-full p-2 bg-slate-900 border border-slate-700 gap-2 relative"):
        # Header Row
        with ui.row().classes("w-full justify-between items-center gap-1"):
            ui.badge(f"#{r_idx + 1}", color="emerald-7").classes("text-xs font-mono")

            def on_type_changed(e):
                region["text_type"] = e.value
                region["user_modified_type"] = True
                on_change_cb()

            ui.select(
                options={
                    "speech": "🗣️ Speech",
                    "caption": "📜 Caption",
                    "thought": "💭 Thought",
                    "onomatopoeia": "⚡ Sound/SFX",
                },
                value=region.get("text_type", "speech"),
                on_change=on_type_changed,
            ).props("dense dark size=xs").classes("w-32")

            def on_lang_changed(e):
                region["detected_lang"] = e.value
                on_change_cb()

            ui.select(
                options={"fra": "fra", "eng": "eng", "spa": "spa", "deu": "deu"},
                value=region.get("detected_lang", default_lang),
                on_change=on_lang_changed,
            ).props("dense dark size=xs").classes("w-20")

            ui.button(
                icon="delete",
                color="red-5",
                on_click=lambda: on_delete_cb(r_idx),
            ).props("flat dense round size=sm").classes("p-1 hover:bg-red-900/50")

        # Top Bar Controls: X Spinner & W Spinner
        with ui.row().classes("w-full justify-between items-center px-4 text-2xs text-slate-400 font-mono"):
            # X Spinner
            with ui.row().classes("items-center gap-1 bg-slate-800 px-2 py-0.5 rounded border border-slate-700"):
                ui.label("X:").classes("text-blue-400 font-bold")
                ui.button(icon="chevron_left", on_click=lambda: adjust_bbox(0, -0.01)).props("flat dense round size=xs color=white no-parent-event")
                ui.label(f"{int(bbox[0]*100)}%").classes("w-6 text-center text-white")
                ui.button(icon="chevron_right", on_click=lambda: adjust_bbox(0, 0.01)).props("flat dense round size=xs color=white no-parent-event")

            # W Spinner
            with ui.row().classes("items-center gap-1 bg-slate-800 px-2 py-0.5 rounded border border-slate-700"):
                ui.label("W:").classes("text-blue-400 font-bold")
                ui.button(icon="chevron_left", on_click=lambda: adjust_bbox(2, -0.01)).props("flat dense round size=xs color=white no-parent-event")
                ui.label(f"{int(bbox[2]*100)}%").classes("w-6 text-center text-white")
                ui.button(icon="chevron_right", on_click=lambda: adjust_bbox(2, 0.01)).props("flat dense round size=xs color=white no-parent-event")

        # Middle Row: Vertical Controls (Y & H Spinners) + Text Input Area
        with ui.row().classes("w-full items-stretch gap-2 min-h-[110px]"):
            # Left Vertical Spinners
            with ui.column().classes("gap-1 items-center bg-slate-800 p-1 rounded border border-slate-700 justify-center"):
                # Y Spinner
                with ui.column().classes("items-center gap-0"):
                    ui.label("Y").classes("text-3xs text-blue-400 font-bold")
                    ui.button(icon="expand_less", on_click=lambda: adjust_bbox(1, -0.01)).props("flat dense round size=xs color=white no-parent-event")
                    ui.label(f"{int(bbox[1]*100)}%").classes("text-3xs text-white font-mono")
                    ui.button(icon="expand_more", on_click=lambda: adjust_bbox(1, 0.01)).props("flat dense round size=xs color=white no-parent-event")

                ui.element("div").classes("w-full h-px bg-slate-700")

                # H Spinner
                with ui.column().classes("items-center gap-0"):
                    ui.label("H").classes("text-3xs text-blue-400 font-bold")
                    ui.button(icon="expand_less", on_click=lambda: adjust_bbox(3, -0.01)).props("flat dense round size=xs color=white no-parent-event")
                    ui.label(f"{int(bbox[3]*100)}%").classes("text-3xs text-white font-mono")
                    ui.button(icon="expand_more", on_click=lambda: adjust_bbox(3, 0.01)).props("flat dense round size=xs color=white no-parent-event")

            # Extracted Text Input Field
            textarea_element = ui.textarea(
                value=region.get("cleaned_text", ""),
                on_change=lambda e: (region.update({"cleaned_text": e.value}), on_change_cb()),
            ).props(f'dense dark font-mono text-xs input-style="height: 100%;" id="textarea-region-{r_idx + 1}"').classes("flex-1 h-full min-h-[110px] w-full")
            region["_textarea"] = textarea_element

        # Debug Preview Thumbnail stored in region dict
        debug_url = region.get("debug_img_url")
        debug_img_element = ui.html()
        region["_debug_img"] = debug_img_element

        if debug_url:
            with ui.row().classes("w-full items-center justify-center bg-slate-800 p-1.5 rounded border border-slate-700 mt-1"):
                debug_img_element = ui.html(
                    f'<img id="debug-img-{r_idx + 1}" src="{debug_url}" class="h-28 w-auto max-w-full object-contain rounded border border-slate-600 cursor-pointer bg-black/80 hover:opacity-90 block mx-auto" />'
                ).on("click", lambda e, url=debug_url: open_lightbox_fn(url, f"OCR Pre-Processed Crop — Region #{r_idx + 1}"))
                region["_debug_img"] = debug_img_element

