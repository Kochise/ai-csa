- Entry Point & Server:

    * `csa_main.py`: Application entry point & NiceGUI server lifecycle

- Workbench UI & Layout:

    * `csa_ui.py`: Main workbench page layout & 12-column grid rendering
    * `csa_ui_nodes.py`: Node tree manipulations (reordering, nesting, promotion)

- Import Wizard Hierarchy:

    * `csa_ui_import.py`: Import wizard dialog frame & step state orchestrator
    * `csa_ui_import__page.py`: Full page view: Panel detection & sensitivity sliders
    * `csa_ui_import__panel.py`: Per-panel view: Crop inspection & text region manager
    * `csa_ui_import__panel_region.py`: Atomic UI leaf: Single speech/SFX region editor card

- Project Data & Disk Operations:

    * `csa_project.py`: Project manager facade (I/O & node operations entry)
    * `csa_project_io.py`: Disk serialization, settings, and web asset pathing
    * `csa_project_node.py`: Tree sanitization, schema migrations & title formatters

- Backend Engines & Base Classes:

    * `csa_img_extract.py`: Abstract base class for image extraction engines
    * `csa_img_extract__TesseractOCR.py`: OpenCV panel detection & Tesseract OCR engine
    * `csa_vid_generate.py`: Abstract base class for video generation engines
    * `csa_vid_generate__FFMpeg.py`: FFmpeg video plan rendering engine
