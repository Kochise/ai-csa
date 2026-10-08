# author: d.koch
# coding: utf-8
# naming: pep-0008
# typing: pep-0484
# docstring: pep-0257
# indentation: 4 spaces

""" src/csa_project_io.py
Comic Strip Animator - Project Storage & Disk I/O Management
"""

# - - - IMPORT - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import json
import os
import re

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

from datetime import datetime

# - - - GLOBAL - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

PROJECTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "projects"))
SETTINGS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "settings.json"))

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Application Settings Persistence
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[CSA Settings] Error reading settings.json: {e}")
    return {"active_project_id": "project_001"}

def save_settings(settings: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Legacy Migrations & Folder Initialization
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def migrate_legacy_project():
    """Migrates legacy single project.json to project_001 and initializes folder structures."""
    legacy_json = os.path.join(PROJECTS_DIR, "project.json")
    target_dir = os.path.join(PROJECTS_DIR, "project_001")
    target_json = os.path.join(target_dir, "project.json")

    if os.path.exists(legacy_json) and not os.path.exists(target_json):
        print(f"[CSA Setup] Migrating {legacy_json} to {target_json}...")
        os.makedirs(target_dir, exist_ok=True)
        os.rename(legacy_json, target_json)

    if os.path.exists(PROJECTS_DIR):
        for entry in os.listdir(PROJECTS_DIR):
            proj_dir = os.path.join(PROJECTS_DIR, entry)
            if os.path.isdir(proj_dir):
                os.makedirs(os.path.join(proj_dir, "assets", "sources"), exist_ok=True)
                os.makedirs(os.path.join(proj_dir, "renders", "plans"), exist_ok=True)

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def get_project_path(project_id: str) -> str:
    return os.path.join(PROJECTS_DIR, project_id, "project.json")

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def create_new_project_folder(project_name: str) -> str:
    """Creates a new project directory with subfolders and initial JSON schema."""
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    existing = [d for d in os.listdir(PROJECTS_DIR) if os.path.isdir(os.path.join(PROJECTS_DIR, d))]

    clean_slug = re.sub(r'[^a-zA-Z0-9_]', '_', project_name.lower().strip())
    new_id = f"project_{clean_slug}" if clean_slug else f"project_{len(existing) + 1:03d}"

    counter = 1
    base_id = new_id
    while new_id in existing:
        new_id = f"{base_id}_{counter}"
        counter += 1

    project_dir = os.path.join(PROJECTS_DIR, new_id)
    os.makedirs(os.path.join(project_dir, "assets", "sources"), exist_ok=True)
    os.makedirs(os.path.join(project_dir, "renders", "plans"), exist_ok=True)

    initial_data = {
        "project_name": project_name,
        "nodes": [
            {
                "id": "root_lore",
                "type": "root_lore",
                "enabled": True,
                "title": "Root Lore & Character Bible",
                "world_description": "",
                "children": []
            }
        ]
    }

    with open(os.path.join(project_dir, "project.json"), "w", encoding="utf-8") as f:
        json.dump(initial_data, f, indent=2)

    return new_id

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Path Resolvers & Web URL Formatting
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def resolve_project_file_path(path: str, project_dir: str) -> str:
    """Resolves relative project paths to full local filesystem paths."""
    if not path:
        return ""
    if os.path.isabs(path) or path.startswith("http://") or path.startswith("https://"):
        return path
    if path.startswith(project_dir):
        return path
    return os.path.join(project_dir, path)

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def get_asset_url(image_path: str, project_dir: str) -> str:
    if not image_path:
        return ""
    if image_path.startswith("http://") or image_path.startswith("https://"):
        return image_path

    resolved_path = resolve_project_file_path(image_path, project_dir)
    if not os.path.exists(resolved_path):
        return ""

    normalized_path = resolved_path.replace("\\", "/")
    if "assets/" in normalized_path:
        relative_asset = normalized_path.split("assets/")[-1]
        return f"/assets/{relative_asset}"

    return image_path

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def get_video_url(video_path: str, project_dir: str) -> str:
    if not video_path:
        return ""

    resolved_path = resolve_project_file_path(video_path, project_dir)
    if not os.path.exists(resolved_path):
        return ""

    normalized_path = resolved_path.replace("\\", "/")
    if "renders/" in normalized_path:
        relative_render = normalized_path.split("renders/")[-1]
        iso_query = datetime.now().isoformat()
        return f"/renders/{relative_render}?t={iso_query}"

    return video_path
