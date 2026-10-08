# author: d.koch
# coding: utf-8
# naming: pep-0008
# typing: pep-0484
# docstring: pep-0257
# indentation: 4 spaces

""" src/csa_project.py
Comic Strip Animator - Project Management Facade
"""

# - - - IMPORT - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import json
import os

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

from csa_project_io import (
    PROJECTS_DIR,
    SETTINGS_FILE,
    load_settings,
    save_settings,
    migrate_legacy_project,
    get_project_path,
    create_new_project_folder,
    resolve_project_file_path,
    get_asset_url,
    get_video_url
)

from csa_project_node import (
    sanitize_node_tree,
    get_node_display_title
)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Project Lifecycle Methods
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def load_project(project_id: str) -> dict:
    """Loads and sanitizes project JSON data from disk."""
    file_path = get_project_path(project_id)
    project_dir = os.path.dirname(file_path)

    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

                nodes = data.get("nodes", [])
                if len(nodes) > 1 or (nodes and nodes[0].get("type") != "root_lore"):
                    root = None
                    other_nodes = []
                    for n in nodes:
                        if n.get("type") == "root_lore":
                            root = n
                        else:
                            other_nodes.append(n)

                    if not root:
                        root = {
                            "id": "root_lore",
                            "type": "root_lore",
                            "enabled": True,
                            "title": "Root Lore & Character Bible",
                            "world_description": "",
                            "children": []
                        }

                    root.setdefault("children", []).extend(other_nodes)
                    data["nodes"] = [root]

                if data.get("nodes"):
                    sanitize_node_tree(data["nodes"][0], project_dir)

                return data
        except Exception as e:
            print(f"[CSA Project] Error loading {file_path}: {e}")

    default_project = {
        "project_name": "Demo Episode",
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
    sanitize_node_tree(default_project["nodes"][0], project_dir)
    return default_project

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def save_project(project_data: dict, project_id: str):
    """Saves project data back to its JSON file on disk."""
    file_path = get_project_path(project_id)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(project_data, f, indent=2)

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def list_available_projects(projects_dir: str = PROJECTS_DIR) -> list:
    """Scans the projects directory and gathers panel statistics and cover thumbnails."""
    projects_list = []
    if not os.path.exists(projects_dir):
        return projects_list

    for entry in os.listdir(projects_dir):
        proj_folder = os.path.join(projects_dir, entry)
        proj_json = os.path.join(proj_folder, "project.json")

        if os.path.isdir(proj_folder) and os.path.exists(proj_json):
            try:
                with open(proj_json, "r", encoding="utf-8") as f:
                    data = json.load(f)

                nodes = data.get("nodes", [])
                panels_count = 0
                first_thumbnail = ""

                def count_panels(n_list):
                    nonlocal panels_count, first_thumbnail
                    for n in n_list:
                        if n.get("type") == "panel_child":
                            panels_count += 1
                            if not first_thumbnail and n.get("original_image"):
                                first_thumbnail = n["original_image"]
                        if "children" in n:
                            count_panels(n["children"])

                count_panels(nodes)

                renders_dir = os.path.join(proj_folder, "renders", "plans")
                renders_count = len(os.listdir(renders_dir)) if os.path.exists(renders_dir) else 0

                projects_list.append({
                    "id": entry,
                    "name": data.get("project_name", entry),
                    "panels_count": panels_count,
                    "renders_count": renders_count,
                    "thumbnail": first_thumbnail,
                    "folder": proj_folder
                })
            except Exception as e:
                print(f"[CSA Proj Scanner] Error parsing {entry}: {e}")

    return projects_list
