#!/usr/bin/env python

# author: d.koch
# coding: utf-8
# naming: pep-0008
# typing: pep-0484
# docstring: pep-0257
# indentation: 4 spaces

""" src/csa_main.py
Comic Strip Animator - Main Server Entry Point
"""

# - - - IMPORT - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import argparse
import asyncio
import os
import sys

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

from nicegui import app, ui
import nicegui.run as run

# Set process pool start method before app startup
run.process_pool_start_method = "spawn"

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

# Import modular project facade & workbench page
from csa_project import (
    load_settings,
    save_settings,
    migrate_legacy_project,
    load_project,
    PROJECTS_DIR
)

from csa_ui import build_workbench_ui

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

# Import modular backend implementations
from csa_img_extract__TesseractOCR import CSAImageExtractorTesseract
from csa_vid_generate__FFMpeg import CSAVideoGeneratorFFMpeg

# - - - GLOBAL - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# Backend Engines
extractor_engine = CSAImageExtractorTesseract()
video_engine = CSAVideoGeneratorFFMpeg()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Project Persistence Setup
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# Setup Environment & Active Project
migrate_legacy_project()
APP_SETTINGS = load_settings()
CURRENT_PROJECT_ID = APP_SETTINGS.get("active_project_id", "project_001")
CURRENT_PROJECT_DIR = os.path.join(PROJECTS_DIR, CURRENT_PROJECT_ID)

# Ensure project static directories exist
os.makedirs(f"{CURRENT_PROJECT_DIR}/renders/plans", exist_ok=True)
os.makedirs(f"{CURRENT_PROJECT_DIR}/assets", exist_ok=True)

app.add_static_files('/renders', f'{CURRENT_PROJECT_DIR}/renders')
app.add_static_files('/assets', f'{CURRENT_PROJECT_DIR}/assets')

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Server Lifecycle & UI Workbench Page
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# HOOK_TAB_AUTO_SHUTDOWN: Shutdown server when no browser tabs remain connected

# Auto Shutdown Tracker
CONNECTED_CLIENTS = 0

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

@app.on_connect
def handle_connect():
    global CONNECTED_CLIENTS
    CONNECTED_CLIENTS += 1

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

@app.on_disconnect
def handle_disconnect():
    global CONNECTED_CLIENTS
    CONNECTED_CLIENTS -= 1
    asyncio.create_task(check_shutdown_after_delay(delay=4))

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

async def check_shutdown_after_delay(delay: int = 4):
    await asyncio.sleep(delay)
    if CONNECTED_CLIENTS <= 0:
        print("\n[CSA] No active browser windows detected. Shutting down server...")
        # Signal app shutdown gracefully through asyncio rather than os._exit
        app.shutdown()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# Main Page Entry Route
@ui.page("/")
def main_workbench_page():
    # Reload settings and active project on every page load
    app_settings = load_settings()
    active_project_id = app_settings.get("active_project_id", "project_001")
    active_project_dir = os.path.join(PROJECTS_DIR, active_project_id)
    project_data = load_project(active_project_id)

    # Ensure project folders exist
    os.makedirs(f"{active_project_dir}/renders/plans", exist_ok=True)
    os.makedirs(f"{active_project_dir}/assets", exist_ok=True)

    build_workbench_ui(
        project_data=project_data,
        project_id=active_project_id,
        project_dir=active_project_dir,
        video_engine=video_engine,
        extractor_engine=extractor_engine
    )

#  - - - MAIN - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def parse_args():
    parser = argparse.ArgumentParser(description="Comic Scene Animator")
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=8080,
        help="NiceGUI server port (default: 8080)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host address to bind (default: 0.0.0.0)"
    )
    return parser.parse_args()

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

if __name__ in {"__main__", "__mp_main__"}:
    args = parse_args()

    # Persist default settings on initial setup
    save_settings(APP_SETTINGS)

    ui.run(
        title="CSA Workbench",
        host=args.host,
        port=args.port,
        reload=False,
        binding_refresh_interval=0.1,
        reconnect_timeout=30.0
    )

