"""
Comic Strip Animator - Main Web Workbench Interface (NiceGUI)
Filename: src/csa_main.py
"""

import webbrowser
import json
import requests
from nicegui import ui

# Import modular backend implementations
from csa_img_extract__TesseractOCR import CSAImageExtractorTesseract
from csa_vid_generate__FFMpeg import CSAVideoGeneratorFFMpeg

# Global UI state and tree data
PROJECT_DATA = {
    "project_name": "Demo Episode",
    "nodes": [
        {
            "id": "root_lore",
            "type": "root_lore",
            "enabled": True,
            "title": "Root Lore & Character Bible",
            "description": "Sci-Fi dystopian world, muted retro palette, high cinematic contrast."
        },
        {
            "id": "seq_01",
            "type": "sequence_parent",
            "enabled": True,
            "title": "Sequence 1: Landing at Sector 7",
            "director_notes": "Slow camera pan right. Low ship engine rumbling SFX.",
            "plan_video": "",
            "children": [
                {
                    "id": "panel_001",
                    "type": "panel_child",
                    "enabled": True,
                    "title": "Panel 1 - Approaching Anomaly",
                    "extracted_text": "We are approaching the primary anomaly!",
                    "original_image": "https://picsum.photos/id/10/300/200",
                    "plan_video": ""
                },
                {
                    "id": "panel_002",
                    "type": "panel_child",
                    "enabled": True,
                    "title": "Panel 2 - Cockpit View",
                    "extracted_text": "Prepare energy shields.",
                    "original_image": "https://picsum.photos/id/11/300/200",
                    "plan_video": ""
                }
            ]
        }
    ]
}

extractor_engine = CSAImageExtractorTesseract()
video_engine = CSAVideoGeneratorFFMpeg()

def toggle_row_enabled(node: dict, row_container):
    """HOOK_TOGGLE_VISIBILITY: Toggles eye visibility without disabling editing."""
    node["enabled"] = not node.get("enabled", True)
    if node["enabled"]:
        row_container.classes(remove="opacity-40 bg-gray-200", add="bg-white")
    else:
        row_container.classes(remove="bg-white", add="opacity-40 bg-gray-200")

def render_node_row(node: dict, is_child: bool = False):
    """HOOK_RENDER_ROW: Renders hierarchical spreadsheet rows with explanatory tooltips."""
    indent_class = "ml-8 border-l-4 border-blue-400 pl-4" if is_child else "border-b-2 border-gray-300"
    bg_class = "bg-white" if node.get("enabled", True) else "opacity-40 bg-gray-200"

    with ui.card().classes(f"w-full mb-2 p-2 transition-all {indent_class} {bg_class}") as row_card:
        with ui.row().classes("w-full items-center justify-between gap-2"):
            
            # Left Action Buttons: Eye Toggle & Record Button
            with ui.row().classes("items-center gap-1"):
                # HOOK_TOOLTIP_EYE: Visibility toggle balloon
                eye_btn = ui.button(icon="visibility", color="blue-7").props("flat round dense")
                eye_btn.tooltip("Toggle visibility: When off (grayed out), this item is skipped during full episode generation, but can still be edited and previewed individually.")
                eye_btn.on("click", lambda: toggle_row_enabled(node, row_card))

                # HOOK_TOOLTIP_RECORD: Record button balloon
                record_btn = ui.button(icon="fiber_manual_record", color="red-6").props("flat round dense")
                if node["type"] == "sequence_parent":
                    record_btn.tooltip("Record/Generate Sequence: Stitches all visible child plans into a parent sequence video with background SFX.")
                else:
                    record_btn.tooltip("Record/Generate Plan: Generates an animated video clip for this panel.")

                ui.label(node.get("title", "Untitled")).classes("font-bold text-md")

            # Input fields with explanatory tooltips
            if node["type"] == "root_lore":
                lore_input = ui.input(label="Global Lore & Character Descriptions").bind_value(node, "description").classes("w-1/2")
                lore_input.tooltip("Root Lore: Global world rules, art style cues, and character visual prompts applied across all scenes for consistency.")
                
            elif node["type"] == "sequence_parent":
                dir_input = ui.input(label="Director's Guidance & Ambient SFX").bind_value(node, "director_notes").classes("w-1/3")
                dir_input.tooltip("Director Notes: Instructions for camera movement, ambient background noises, and music spanning this group of panels.")
                
            elif node["type"] == "panel_child":
                ui.image(node["original_image"]).classes("w-20 h-14 rounded object-cover")
                txt_input = ui.input(label="Extracted Dialogue / Captions").bind_value(node, "extracted_text").classes("w-1/3")
                txt_input.tooltip("Dialogue & Bubbles: OCR extracted text used for character voice narration and speech bubble inpainting.")

            # Right Video Preview / Thumbnail
            with ui.row().classes("items-center gap-2"):
                if node.get("plan_video") and os.path.exists(node["plan_video"]):
                    preview_vid = ui.video(node["plan_video"]).classes("w-28 h-16 rounded shadow")
                    preview_vid.tooltip("Plan/Sequence Preview: Hover/Play to preview rendered video output.")
                else:
                    lbl = ui.label("No Plan Rendered").classes("text-xs text-gray-400 italic")
                    lbl.tooltip("Status: Click the red Record button on the left to render a video plan for this row.")

                record_btn.on("click", lambda: trigger_node_generation(node))

def trigger_node_generation(node: dict):
    """HOOK_TRIGGER_GEN: Generates video plans or sequences based on row type."""
    ui.notify(f"Processing sequence plan for: {node.get('title')}", type="info")
    out_path = f"projects/project_001/renders/plans/{node['id']}.mp4"
    
    # Render plan video clip using backend video engine
    video_engine.generate_plan_video(node, out_path)
    node["plan_video"] = out_path
    ui.notify(f"Plan generated for {node.get('title')}!", type="positive")
    ui.update()

def open_in_comfyui(project_id: str, sequence_id: str, panel_id: str, prompt_text: str, bg_image_path: str):
    COMFY_URL = "http://localhost:8188"
    
    # Step 1: Verify ComfyUI is online
    try:
        response = requests.get(f"{COMFY_URL}/system_stats", timeout=2)
        if response.status_code != 200:
            ui.notify("ComfyUI server is not responding at port 8188", type="negative")
            return
    except Exception:
        ui.notify("Could not connect to ComfyUI on http://localhost:8188. Is it running?", type="warning")
        return

    # Step 2: Prepare workflow JSON with pre-filled panel parameters
    # (Update LoadImage node path, Positive CLIP Text Encode, Seed, etc.)
    # ... asset copying and JSON node parameter injection ...
    
    ui.notify(f"Staged Panel {panel_id} assets into ComfyUI!", type="positive")
    
    # Step 3: Launch new browser tab targeting ComfyUI workbench
    webbrowser.open_new_tab(COMFY_URL)

# UI Column Rendering inside the Panel Row Table
def render_panel_row_actions(row_data):
    with ui.row().classes('items-center gap-2'):
        # Existing Plan Generation Button
        ui.button(icon='videocam', color='red', on_click=lambda: generate_plan(row_data))
        
        # NEW: External ComfyUI Fine-Tuning Button
        ui.button(
            'Refine in ComfyUI', 
            icon='open_in_new', 
            color='purple-7', 
            on_click=lambda: open_in_comfyui(
                project_id=row_data['project_id'],
                sequence_id=row_data['sequence_id'],
                panel_id=row_data['panel_id'],
                prompt_text=row_data['prompt'],
                bg_image_path=row_data['bg_path']
            )
        ).tooltip('Open pre-filled node graph in a new browser tab (Port 8188)')

@ui.page("/")
def build_workbench_ui():
    """HOOK_BUILD_MAIN_UI: Main top menu bar with tooltips and spreadsheet layout."""
    
    # Top Menu Bar with Tooltips
    with ui.header().classes("bg-slate-800 text-white flex justify-between items-center p-2"):
        ui.label("Comic Strip Animator (CSA) Workbench").classes("text-lg font-bold")
        
        with ui.row().classes("gap-2"):
            btn_new = ui.button("New Project", icon="add").props("flat color=white")
            btn_new.tooltip("Create a new project folder with dedicated asset directories and configuration file.")

            btn_import = ui.button("Import Comic", icon="file_upload").props("flat color=white")
            btn_import.tooltip("Import comic pages from PDF, EPUB, or raw image files.")

            btn_extract = ui.button("Extract Panels", icon="grid_view", color="secondary")
            btn_extract.tooltip("Automatically split comic pages into panel rows using gutter detection and run OCR on speech bubbles.")

            btn_gen = ui.button("Generate Full Episode", icon="movie", color="positive")
            btn_gen.tooltip("Generate episode with all selected plans/sequences: Compiles all visible rows (Eye open) into a final stitched episode.")

    # Main Spreadsheet Layout
    with ui.column().classes("w-full p-4 max-w-7xl mx-auto"):
        for node in PROJECT_DATA["nodes"]:
            render_node_row(node, is_child=False)
            
            # Render children under sequence parent
            if "children" in node:
                for child in node["children"]:
                    render_node_row(child, is_child=True)

if __name__ in {"__main__", "__mp_main__"}:
    os.makedirs("projects/project_001/renders/plans", exist_ok=True)
    ui.run(title="CSA Workbench", port=8080, reload=False)