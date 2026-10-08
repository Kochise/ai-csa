# author: d.koch
# coding: utf-8
# naming: pep-0008
# typing: pep-0484
# docstring: pep-0257
# indentation: 4 spaces

""" src/csa_project_node.py
Comic Strip Animator - Project Node Tree Management & Schema Integrity
"""

# - - - IMPORT - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import os

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

from csa_project_io import resolve_project_file_path

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def sanitize_node_tree(node: dict, project_dir: str):
    """Recursively validates and upgrades project nodes with missing default schema fields."""

    # Sanitize video plans
    raw_videos = node.get("plan_videos", [])
    if not raw_videos and node.get("plan_video"):
        raw_videos = [node["plan_video"]]

    valid_videos = []
    for rel_path in raw_videos:
        if isinstance(rel_path, str):
            full_path = resolve_project_file_path(rel_path, project_dir)
            if os.path.exists(full_path):
                valid_videos.append(rel_path)

    node["plan_videos"] = valid_videos
    curr_idx = node.get("active_video_index", 0)
    if not valid_videos:
        node["active_video_index"] = 0
        node["plan_video"] = ""
    else:
        new_idx = max(0, min(curr_idx, len(valid_videos) - 1))
        node["active_video_index"] = new_idx
        node["plan_video"] = valid_videos[new_idx]

    # Sanitize image asset references
    for img_key in ("original_image", "background_image", "source_file"):
        img_path = node.get(img_key, "")
        if isinstance(img_path, str) and img_path and not img_path.startswith(("http://", "https://")):
            full_img_path = resolve_project_file_path(img_path, project_dir)
            if not os.path.exists(full_img_path):
                node[img_key] = ""

    # Panel schema defaults
    if node.get("type") == "panel_child":
        node.setdefault("source_file", "")
        node.setdefault("ocr_lang", "fra")
        node.setdefault("aspect_ratio", "portrait")
        node.setdefault("text_regions", [])

    if not isinstance(node.get("extracted_text"), str):
        node["extracted_text"] = ""

    if not isinstance(node.get("director_notes"), str):
        node["director_notes"] = ""

    for child in node.get("children", []):
        sanitize_node_tree(child, project_dir)

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def get_node_display_title(node: dict) -> str:
    """Formats node titles nicely (e.g., panel_001 -> Panel 001)."""
    if node.get("title"):
        return node["title"]
    return node.get("id", "Untitled Row").replace("_", " ").title()
