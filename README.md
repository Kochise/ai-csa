# Comic Strip Animator (CSA)

**Comic Strip Animator (CSA)** is an open-source interactive workbench designed to convert comic strip pages into animated video episodes. It combines automatic gutter detection, speech bubble inpainting, character extraction, text-to-speech, and image-to-video generation into a hierarchical spreadsheet workflow.

---

## Architecture Overview

CSA operates on a three-tier model hierarchy:

1. **Root Lore Row**: Global style prompts, world rules, and character reference descriptions.
2. **Parent Sequence Rows**: Directional controls, camera motion prompts, and continuous ambient sound effects spanning multiple scenes.
3. **Child Panel Rows**: Individual panels containing clean inpainted backgrounds, character cutouts, extracted dialogue, and rendered **Plans** (individual panel video clips).

---

## Quick Start & Installation

### 1. Run Setup Script

```bash
./setup.sh
```

The setup script will:

- Detect if executed from a **Git** clone and prompt for automatic `git pull` updates.
- Install required system libraries (`ffmpeg`, `tesseract-ocr`, `poppler-utils`).
- Create a local **Python** virtual environment (`venv`).
- Install **PyTorch** (with **CUDA** support) and required **Python** dependencies.

### 2. Launch the Application

```bash
./start.sh
```

Open your browser at: http://localhost:8080

---

## Step-by-Step User Guide: Generating an Episode

### Step 1: Create or Open a Project

Click **New Project** in the top menu bar to create a project directory structure under `projects/<project_name>/`.

### Step 2: Import Comic Pages

Click **Import Comic** to upload your source material (PDF, EPUB, or PNG/JPG page files). Files are saved to `assets/raw/`.

### Step 3: Extract Panels & Speech Bubbles

Click **Extract Panels**. The backend pipeline will automatically:

1. Detect panel borders via gutter contouring.
2. Extract speech/thought bubbles using OCR (**Tesseract** / **PaddleOCR**).
3. Inpaint original speech bubbles to produce clean background images.
4. Populate the interactive spreadsheet grid with a child row for each panel.

### Step 4: Define World Lore & Group Sequences

1. **Fill Root Lore**: Define visual art style (e.g., "1950s sci-fi aesthetic, film grain, vibrant colors") and character prompt descriptions.
2. **Group Panels**: Select related panel rows and group them under a Parent Sequence Row.
3. **Add Director's Guidance**: Set camera movement (e.g., "Slow zoom in") and ambient SFX (e.g., "Rain and distant thunder") in the parent sequence row.

### Step 5: Preview & Generate Individual Plans

- Click the red **Record** button on any panel child row to generate its Plan (a 3–5 second animated video clip).
- Adjust dialogue text or descriptions and regenerate until satisfied.
- Use the **Eye** icon toggle to include or exclude specific panels from the final video without deleting them.

### Step 6: Render Full Episode

Click **Generate Full Episode** in the top menu bar. The engine will:

1. Filter all rows where the **Eye** visibility button is toggled ON.
2. Generate any missing individual panel **Plans**.
3. Concatenate panel clips under parent Sequences and overlay dialogue TTS + ambient audio.
4. Stitch all sequences into `projects/<project_name>/renders/full_episode.mp4`.

---

## UI Control Reference

| Control Element		| Location			| Function			|
| :---					| :---				| :---				|
| **Eye** Icon Toggle	| Left of each row	| **Visibility Toggle**<br> Excludes row from full episode renders when off (grayed out). Row remains editable and can still be previewed.	|
| Red **Record** Button	| Left of each row	| **Generate Plan / Sequence**<br> Renders a video clip for the specific row.	|
| Lore Row / Root		| Top of table		| **Global Context**<br> Holds world descriptions and character visual bibles applied across all AI generations.	|
| Sequence Row / Parent	| Table hierarchy	| **Scene Director**<br> Controls background music, continuous sound effects, and camera movement over grouped panels.	|
| Panel Row / Child		| Table hierarchy	| **Panel Detail**<br> Displays original panel, inpainted background, extracted character cutouts, and editable dialogue text.	|
| Generate Full Episode	| Top Menu Bar		| **Master Render**<br> Assembles all visible plans and sequences into the final video file (`full_episode.mp4`).	|
