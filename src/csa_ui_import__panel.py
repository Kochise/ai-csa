# author: d.koch
# coding: utf-8
# naming: pep-0008
# typing: pep-0484
# docstring: pep-0257
# indentation: 4 spaces

""" src/csa_ui_import__panel.py
Per-panel inspection view with region overlays and OCR re-execution.
"""

# - - - IMPORT - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import base64
import cv2
import numpy as np
import os
import pytesseract

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

from PIL import Image
from nicegui import ui

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

from csa_ui_import__panel_region import render_panel_region_card
from csa_img_extract import get_extractor_by_name

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def clean_and_denoise_for_ocr(crop_bgr: np.ndarray, params: dict) -> np.ndarray:
    """
    Parametric Clean Pipeline for Hand-Lettered Comics:
    Uses custom scale, bilateral filtering, adaptive thresholding, and min-area speckle filtering.
    """
    scale = float(params.get("scale", 2.0))
    sigma = int(params.get("sigma", 5))
    block_size = int(params.get("block_size", 19))
    c_val = int(params.get("c_val", 9))
    min_area = int(params.get("min_area", 12))

    # 1. Upscale
    scaled = cv2.resize(crop_bgr, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # 2. Grayscale
    gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)

    # 3. Bilateral Filter Smoothing
    denoised = cv2.bilateralFilter(gray, d=5, sigmaColor=sigma * 10, sigmaSpace=sigma * 10) if sigma > 0 else gray

    # 4. Adaptive Thresholding (block_size must be odd and >= 3)
    b_size = max(3, block_size if block_size % 2 == 1 else block_size + 1)
    binary = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, b_size, c_val
    )

    # 5. Connected Component Area Filtering
    if min_area > 0:
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(cv2.bitwise_not(binary))
        filtered = np.full_like(binary, 255)

        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] >= min_area:
                filtered[labels == i] = 0
        binary = filtered

    # 6. 32px White Border Margin
    padded = cv2.copyMakeBorder(binary, 32, 32, 32, 32, cv2.BORDER_CONSTANT, value=[255, 255, 255])
    return padded

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def reprocess_region_ocr(panel_crop_path: str, region: dict, project_dir: str, r_idx: int, params: dict, lang: str = "fra", engine_name: str = "Tesseract"):
    """Crops region, applies parametric cleaning, generates Base64 debug data URL, and re-runs OCR via CSAExtractorBase subclasses."""
    print(f"\n[CSA Debug OCR Log] --- Starting OCR Reprocess for Region #{r_idx} using {engine_name} ---")
    if not os.path.exists(panel_crop_path):
        print(f"[CSA Debug OCR Error] Panel file missing: {panel_crop_path}")
        return

    img = cv2.imread(panel_crop_path)
    if img is None:
        print(f"[CSA Debug OCR Error] cv2.imread failed for: {panel_crop_path}")
        return

    h_img, w_img = img.shape[:2]
    bbox = region.get("bbox", [0.1, 0.1, 0.3, 0.2])

    x = int(bbox[0] * w_img)
    y = int(bbox[1] * h_img)
    w = int(bbox[2] * w_img)
    h = int(bbox[3] * h_img)

    x, y = max(0, x), max(0, y)
    w, h = max(10, min(w_img - x, w)), max(10, min(h_img - y, h))

    crop = img[y:y+h, x:x+w]
    if crop.size == 0:
        print("[CSA Debug OCR Error] Crop array is empty!")
        return

    cleaned_crop = clean_and_denoise_for_ocr(crop, params)

    # Save debug image
    shm_dir = "/dev/shm/csa_ocr_debug" if os.path.exists("/dev/shm") else os.path.join(project_dir, "assets")
    os.makedirs(shm_dir, exist_ok=True)

    debug_filename = f"ocr_debug_r{r_idx}_{int(os.path.getmtime(panel_crop_path))}.png"
    debug_full_path = os.path.join(shm_dir, debug_filename)
    cv2.imwrite(debug_full_path, cleaned_crop)

    _, buffer = cv2.imencode('.png', cleaned_crop)
    base64_str = base64.b64encode(buffer).decode('utf-8')
    region["debug_img_url"] = f"data:image/png;base64,{base64_str}"
    region["debug_img_abs"] = debug_full_path

    target_lang = region.get("detected_lang", lang)
    text = ""

    # Use CSAExtractorBase factory/subclass implementation
    text = ""
    try:
        extractor = get_extractor_by_name(engine_name)
        # Fallback handling for engines returning full panel lists vs single region text
        if hasattr(extractor, "extract_text"):
            text = extractor.extract_text(cleaned_crop, lang=target_lang, params=params).strip()
        else:
            extracted_list = extractor.extract_bubbles_from_panel(cleaned_crop, lang=target_lang)
            text = " ".join([b.get("cleaned_text", "") for b in extracted_list]).strip()
    except Exception as err:
        print(f"[CSA Debug OCR Error] {engine_name} extractor failed: {err}")

    # Fallback to Tesseract via pytesseract if empty
    if not text:
        try:
            pil_img = Image.fromarray(cleaned_crop)
            text = pytesseract.image_to_string(pil_img, lang=target_lang, config="--psm 6").strip()
        except Exception as t_err:
            print(f"[CSA Debug OCR Error] Tesseract fallback failed: {t_err}")

    region["cleaned_text"] = text
    region["raw_ocr"] = text
    print(f"[CSA Debug OCR Log] Final OCR Result for Region #{r_idx}: '{text}'")

    if not region.get("user_modified_type", False):
        if y < (h_img * 0.25) and (w / max(1, h)) > 2.2:
            region["text_type"] = "caption"
        else:
            region["text_type"] = "speech"

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def render_import_panel_view(container, state: dict, project_dir: str, get_asset_url_fn, open_lightbox_fn, on_refresh_cb):
    """Renders per-panel view with organized two-line OCR controls and zoom/pan modal lightbox."""
    container.clear()

    p_idx = state["current_panel_idx"]
    if p_idx < 0 or p_idx >= len(state["panel_nodes"]):
        return

    panel = state["panel_nodes"][p_idx]
    crop_rel_path = panel["original_image"]
    crop_full_path = os.path.join(project_dir, crop_rel_path)
    crop_url = get_asset_url_fn(crop_rel_path, project_dir)

    # Ensure pre-processing parameters persist per-panel in state
    ocr_params = state.setdefault("ocr_params", {
        "scale": 2.0,
        "sigma": 5,
        "block_size": 19,
        "c_val": 9,
        "min_area": 12,
        "engine": "Tesseract"
    })

    # Persistent Zoom/Pan Lightbox Modal Dialog
    if "lightbox_dialog" not in state:
        # Adjusted card size to fill modal space nicely
        with ui.dialog() as dlg, ui.card().classes("bg-slate-900 border border-slate-700 p-4 gap-3 items-center w-[96vw] h-[94vh] max-w-none max-h-none flex flex-col"):
            dlg.props("persistent")
            with ui.row().classes("w-full justify-between items-center flex-shrink-0 z-10"):
                title_lbl = ui.label("").classes("text-white font-bold text-sm")
                ui.button(icon="close", on_click=dlg.close).props("flat dense round color=white")
            # Enforce absolute full-area sizing on the image column container
            img_col = ui.column().classes("flex-1 w-full h-full min-h-0 items-center justify-center overflow-hidden bg-black rounded relative cursor-grab active:cursor-grabbing p-0")
        state["lightbox_dialog"] = dlg
        state["lightbox_title_lbl"] = title_lbl
        state["lightbox_img_col"] = img_col

    def show_lightbox(img_src: str, title_str: str):
        state["lightbox_title_lbl"].text = title_str
        state["lightbox_img_col"].clear()
        with state["lightbox_img_col"]:
            # Forcing absolute sizing directly in the wrapper HTML element
            ui.html(f'''
                <div id="zoom-container" style="position: absolute; inset: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; overflow: hidden; background: #000;">
                    <img id="zoom-image" src="{img_src}" style="max-width: 100%; max-height: 100%; object-fit: contain; transform: scale(1) translate(0px, 0px); transition: transform 0.05s ease-out; cursor: grab;" />
                </div>
            ''').classes("absolute inset-0 w-full h-full")
        state["lightbox_dialog"].open()
        
        # Attach zoom & pan logic via run_javascript
        ui.timer(0.05, lambda: ui.run_javascript('''
            const container = document.getElementById("zoom-container");
            const img = document.getElementById("zoom-image");
            if (container && img && !container._zoomInitialized) {
                container._zoomInitialized = true;
                let scale = 1, panning = false, pointX = 0, pointY = 0, startX = 0, startY = 0;

                container.onwheel = function(e) {
                    e.preventDefault();
                    if (e.deltaY < 0) { scale *= 1.15; } else { scale /= 1.15; }
                    scale = Math.max(0.5, Math.min(scale, 15));
                    img.style.transform = `scale(${scale}) translate(${pointX}px, ${pointY}px)`;
                };

                img.onmousedown = function(e) {
                    e.preventDefault();
                    startX = e.clientX - pointX * scale; 
                    startY = e.clientY - pointY * scale;
                    panning = true;
                    img.style.cursor = "grabbing";
                };

                window.onmouseup = function() {
                    panning = false;
                    if (img) img.style.cursor = "grab";
                };

                window.onmousemove = function(e) {
                    if (!panning) return;
                    pointX = (e.clientX - startX) / scale;
                    pointY = (e.clientY - startY) / scale;
                    img.style.transform = `scale(${scale}) translate(${pointX}px, ${pointY}px)`;
                };
            }
        '''), once=True)

    with container, ui.column().classes("w-full h-full max-h-[85vh] overflow-hidden gap-2"):
        
        def trigger_reprocess():
            engine_choice = ocr_params.get("engine", "Tesseract")
            for r_i, r_item in enumerate(panel.get("text_regions", []), start=1):
                reprocess_region_ocr(crop_full_path, r_item, project_dir, r_i, ocr_params, lang=r_item.get("detected_lang", panel.get("ocr_lang", "fra")), engine_name=engine_choice)

            updates = [{
                "idx": r_i,
                "text": r_item.get("cleaned_text", ""),
                "img_url": r_item.get("debug_img_url", "")
            } for r_i, r_item in enumerate(panel.get("text_regions", []), start=1)]

            ui.run_javascript(f'''
                const scroller = document.getElementById("region-sidebar-scroller");
                const savedScroll = scroller ? scroller.scrollTop : 0;

                const updates = {updates};
                updates.forEach(u => {{
                    const ta = document.getElementById("textarea-region-" + u.idx);
                    if (ta && ta.value !== u.text) {{
                        ta.value = u.text;
                        ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                    const imgEl = document.getElementById("debug-img-" + u.idx);
                    if (imgEl && u.img_url) {{
                        imgEl.src = u.img_url;
                    }}
                }});

                if (scroller) {{
                    scroller.scrollTop = savedScroll;
                }}
            ''')
            render_panel_image_and_svg()

        # Cleaned Single Control Pane (Line 1: Header, Centered Engine, Scale, Reset)
        with ui.row().classes("w-full items-center justify-between border-b border-slate-800 pb-2"):
            ui.label("⚙️ OCR Pre-Processing Controls").classes("font-bold text-slate-200")

            with ui.row().classes("items-center gap-1 justify-center flex-1"):
                ui.label("Engine:").classes("text-xs text-slate-400")
                engine_select = ui.select(
                    options=["Tesseract", "Paddle", "Easy"],
                    value=ocr_params.get("engine", "Tesseract")
                ).props("dense dark size=xs").classes("w-32")
                engine_select.on_value_change(lambda e: (ocr_params.update({"engine": e.value}), trigger_reprocess()))

            with ui.row().classes("items-center gap-3"):
                with ui.row().classes("items-center gap-1"):
                    ui.label("Scale:")
                    s_select = ui.select(options={1.5: "1.5x", 2.0: "2.0x", 2.5: "2.5x", 3.0: "3.0x"}, value=ocr_params["scale"]).props("dense dark size=xs")
                    s_select.on_value_change(lambda e: (ocr_params.update({"scale": float(e.value)}), trigger_reprocess()))

                ui.button("Reset Settings", icon="refresh", on_click=lambda: (
                    ocr_params.update({"scale": 2.0, "sigma": 5, "block_size": 19, "c_val": 9, "min_area": 12, "engine": "Tesseract"}),
                    trigger_reprocess()
                )).props("dense flat size=xs color=grey-4")

        # Line 2: Sliders with direct data binding
        with ui.row().classes("w-full items-center justify-between gap-4 pt-1"):
            with ui.row().classes("items-center gap-1 flex-1"):
                ui.label("Denoise:").classes("w-14")
                ui.slider(min=0, max=10).bind_value(ocr_params, "sigma").on("change", lambda: trigger_reprocess()).props("dense dark label").classes("flex-1")

            with ui.row().classes("items-center gap-1 flex-1"):
                ui.label("Block Size:").classes("w-16")
                ui.slider(min=5, max=35, step=2).bind_value(ocr_params, "block_size").on("change", lambda: trigger_reprocess()).props("dense dark label").classes("flex-1")

            with ui.row().classes("items-center gap-1 flex-1"):
                ui.label("C:").classes("w-8")
                ui.slider(min=1, max=20).bind_value(ocr_params, "c_val").on("change", lambda: trigger_reprocess()).props("dense dark label").classes("flex-1")

            with ui.row().classes("items-center gap-1 flex-1"):
                ui.label("Min Area:").classes("w-16")
                ui.slider(min=0, max=50).bind_value(ocr_params, "min_area").on("change", lambda: trigger_reprocess()).props("dense dark label").classes("flex-1")

        # Main View Area
        with ui.row().classes("w-full flex-1 gap-4 items-start overflow-hidden"):
            # Left Panel Viewport Container (stores container reference for in-place SVG box updates)
            left_viewport_col = ui.column().classes("flex-1 h-full items-center justify-center bg-black/40 rounded border border-slate-700 p-2 relative overflow-hidden")
            
            def render_panel_image_and_svg():
                left_viewport_col.clear()
                with left_viewport_col:
                    if crop_url:
                        with ui.element("div").classes("relative w-fit h-fit max-h-[60vh] mx-auto overflow-hidden rounded shadow-sm flex items-center justify-center cursor-pointer").on(
                            "click", lambda e, url=crop_url: show_lightbox(url, f"Panel {p_idx + 1}")
                        ):
                            ui.html(f'<img src="{crop_url}" class="max-h-[60vh] max-w-full object-contain block pointer-events-none" />')

                            svg_lines = [
                                '<svg class="absolute inset-0 w-full h-full pointer-events-none">',
                                '<style>',
                                '  .region-num-text {',
                                '    font-weight: 900;',
                                '    fill: #facc15;',
                                '    stroke: #000000;',
                                '    stroke-width: 3px;',
                                '    stroke-linejoin: round;',
                                '    paint-order: stroke fill;',
                                '    user-select: none;',
                                '  }',
                                '</style>'
                            ]

                            for r_idx, reg in enumerate(panel.get("text_regions", []), start=1):
                                bbox = reg.get("bbox", [0, 0, 0, 0])
                                x_pct, y_pct, w_pct, h_pct = bbox[0] * 100, bbox[1] * 100, bbox[2] * 100, bbox[3] * 100
                                cx_pct = x_pct + (w_pct / 2)
                                cy_pct = y_pct + (h_pct / 2)
                                font_size = max(18, int(h_pct * 2.5))
                                stroke_color = "#34d399" if reg.get("text_type") == "speech" else "#f43f5e"

                                svg_lines.append(
                                    f'<rect x="{x_pct}%" y="{y_pct}%" width="{w_pct}%" height="{h_pct}%" '
                                    f'fill="rgba(52, 211, 153, 0.18)" stroke="{stroke_color}" stroke-width="2.5" '
                                    f'stroke-dasharray="6,4" />'
                                )
                                svg_lines.append(
                                    f'<text x="{cx_pct}%" y="{cy_pct}%" class="region-num-text" '
                                    f'font-size="{font_size}px" text-anchor="middle" '
                                    f'dominant-baseline="central">{r_idx}</text>'
                                )

                            svg_lines.append('</svg>')
                            ui.html("".join(svg_lines)).classes("absolute inset-0 pointer-events-none")

            render_panel_image_and_svg()

            # Right Region Sidebar
            with ui.column().classes("w-[440px] h-full flex flex-col bg-slate-800 p-3 rounded border border-slate-700 gap-3"):
                with ui.row().classes("w-full justify-between items-center border-b border-slate-700 pb-2 flex-shrink-0"):
                    ui.label("Detected Text & SFX").classes("font-bold text-sm")

                    def add_manual_region():
                        new_reg = {
                            "text_type": "speech",
                            "cleaned_text": "",
                            "bbox": [0.1, 0.1, 0.4, 0.2],
                            "user_modified_type": False,
                            "detected_lang": panel.get("ocr_lang", "fra")
                        }
                        r_count = len(panel["text_regions"]) + 1
                        reprocess_region_ocr(crop_full_path, new_reg, project_dir, r_count, ocr_params, lang=panel.get("ocr_lang", "fra"), engine_name=ocr_params.get("engine", "Tesseract"))
                        panel["text_regions"].append(new_reg)
                        render_import_panel_view(container, state, project_dir, get_asset_url_fn, open_lightbox_fn, on_refresh_cb)

                    ui.button("ADD REGION", icon="add", color="positive", on_click=add_manual_region).props("dense flat").classes("font-bold text-sm")

                # Scrollable cards container with permanent scrollbar and pr-3 right margin
                with ui.column().classes("w-full flex-1 min-h-0 overflow-y-scroll gap-3 pr-3") as scroller_el:
                    scroller_el.props('id="region-sidebar-scroller"')
                    if not panel["text_regions"]:
                        ui.label("No text bubbles detected.").classes("text-xs text-slate-400 italic py-4")

                    def delete_region(idx: int):
                        panel["text_regions"].pop(idx)
                        render_import_panel_view(container, state, project_dir, get_asset_url_fn, open_lightbox_fn, on_refresh_cb)

                    def on_region_changed(reg_idx, reg):
                        reprocess_region_ocr(crop_full_path, reg, project_dir, reg_idx + 1, ocr_params, lang=reg.get("detected_lang", panel.get("ocr_lang", "fra")), engine_name=ocr_params.get("engine", "Tesseract"))
                        render_import_panel_view(container, state, project_dir, get_asset_url_fn, open_lightbox_fn, on_refresh_cb)

                    def on_spinner_changed(reg_idx, reg):
                        reprocess_region_ocr(crop_full_path, reg, project_dir, reg_idx + 1, ocr_params, lang=reg.get("detected_lang", panel.get("ocr_lang", "fra")), engine_name=ocr_params.get("engine", "Tesseract"))
                        render_panel_image_and_svg()

                    for r_idx, reg in enumerate(panel["text_regions"]):
                        if not reg.get("debug_img_url"):
                            reprocess_region_ocr(crop_full_path, reg, project_dir, r_idx + 1, ocr_params, lang=reg.get("detected_lang", panel.get("ocr_lang", "fra")), engine_name=ocr_params.get("engine", "Tesseract"))

                        render_panel_region_card(
                            reg, r_idx, default_lang=panel.get("ocr_lang", "fra"),
                            project_dir=project_dir, get_asset_url_fn=get_asset_url_fn, open_lightbox_fn=show_lightbox,
                            on_delete_cb=delete_region, on_change_cb=lambda idx=r_idx, r=reg: on_region_changed(idx, r),
                            on_spinner_cb=lambda idx=r_idx, r=reg: on_spinner_changed(idx, r)
                        )

