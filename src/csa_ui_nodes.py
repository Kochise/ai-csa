# author: d.koch
# coding: utf-8
# naming: pep-0008
# typing: pep-0484
# docstring: pep-0257
# indentation: 4 spaces

""" src/csa_ui_nodes.py
Comic Strip Animator - Node Tree & Render State Operations
"""

# - - - IMPORT - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

#from nicegui import ui

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

from csa_project import save_project, get_node_display_title

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Node & Tree Reordering Logic
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def move_node(node_id: str, direction: int, project_data: dict, project_id: str, refresh_fn):
    """Moves a node up or down in its local children array."""
    root = project_data["nodes"][0]

    def find_and_move(parent):
        children = parent.get("children", [])
        for i, child in enumerate(children):
            if child["id"] == node_id:
                new_idx = i + direction
                if 0 <= new_idx < len(children):
                    children[i], children[new_idx] = children[new_idx], children[i]
                    save_project(project_data, project_id)
                    refresh_fn()
                return True
            if find_and_move(child):
                return True
        return False

    find_and_move(root)

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def toggle_panel_nesting(node_id: str, project_data: dict, project_id: str, refresh_fn):
    """Promotes or nests a panel node relative to parent sequence nodes."""
    root = project_data["nodes"][0]
    children = root.get("children", [])

    # Check root-level children
    for idx, child in enumerate(children):
        if child["id"] == node_id and child.get("type") == "panel_child":
            # Look backwards for a preceding sequence parent to nest into
            for prev_idx in range(idx - 1, -1, -1):
                if children[prev_idx].get("type") == "sequence_parent":
                    target_seq = children[prev_idx]
                    panel = children.pop(idx)
                    target_seq.setdefault("children", []).append(panel)
                    save_project(project_data, project_id)
                    refresh_fn()
                    return

    # Check nested children inside sequence parents
    for seq in children:
        if seq.get("type") == "sequence_parent":
            seq_children = seq.get("children", [])
            for idx, child in enumerate(seq_children):
                if child["id"] == node_id:
                    # Promote to root level immediately after this sequence
                    panel = seq_children.pop(idx)
                    seq_idx = children.index(seq)
                    children.insert(seq_idx + 1, panel)
                    save_project(project_data, project_id)
                    refresh_fn()
                    return

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def remove_sequence(seq_id: str, project_data: dict, project_id: str, refresh_fn):
    """Removes a sequence node and frees its child panels back to root level."""
    root = project_data["nodes"][0]
    children = root.get("children", [])

    for idx, child in enumerate(children):
        if child["id"] == seq_id and child.get("type") == "sequence_parent":
            orphans = child.get("children", [])
            children.pop(idx)
            # Insert orphans back into root children array at the same position
            for o_idx, orphan in enumerate(orphans):
                children.insert(idx + o_idx, orphan)

            save_project(project_data, project_id)
            refresh_fn()
            ui.notify(f"Removed sequence '{get_node_display_title(seq)}'. Freed {len(orphaned_children)} plans.", type="positive")
            return

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def add_new_sequence(project_data: dict, project_id: str, refresh_fn):
    """Appends a new Sequence parent node to the project tree."""
    import time
    timestamp = int(time.time())

    root = project_data["nodes"][0]
    new_seq = {
        "id": f"sequence_{timestamp}",
        "type": "sequence_parent",
        "enabled": True,
        "title": f"Sequence {len(root.get('children', [])) + 1:02d}",
        "director_notes": "",
        "children": []
    }

    root.setdefault("children", []).append(new_seq)
    save_project(project_data, project_id)
    refresh_fn()
    ui.notify("Added new sequence row.", type="positive")

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

def reorder_nodes_by_index(old_index: int, new_index: int, project_data: dict, project_id: str, refresh_fn):
    """Handles Sortable.js drag-and-drop reordering for root children."""
    if not project_data.get("nodes"):
        return

    root = project_data["nodes"][0]
    children = root.get("children", [])

    if 0 <= old_index < len(children) and 0 <= new_index < len(children):
        moved_node = children.pop(old_index)
        children.insert(new_index, moved_node)
        save_project(project_data, project_id)
        refresh_fn()
        ui.notify("Reordered structure.", type="info")


