# author: d.koch
# coding: utf-8
# naming: pep-0008
# typing: pep-0484
# docstring: pep-0257
# indentation: 4 spaces

""" src/csa_img_extract__TesseractOCR.py
Comic Strip Animator - Image Extractor (Tesseract / OpenCV Implementation)
"""

# - - - IMPORT - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import cv2
import numpy as np
import os
import pytesseract
import time
import urllib.request

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

from PIL import Image
from typing import List, Dict, Any

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

from csa_img_extract import CSAImageExtractor

# - - - CLASS - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class CSAImageExtractorTesseract(CSAImageExtractor):
    def __init__(self, tesseract_cmd: str = None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def extract_panels_from_image(
        self,
        image_source: str,
        output_assets_dir: str,
        source_rel_path: str = "",
        lang: str = "fra",
        kernel_size: int = 5,
        min_area_ratio: float = 0.01,
        psm_mode: int = 6
    ) -> list:
        """
        Downloads/loads an image, performs panel contour detection with adjustable sensitivity,
        crops individual panel images, runs OCR with language fallback, and returns structured panel nodes.
        """
        os.makedirs(output_assets_dir, exist_ok=True)
        timestamp = int(time.time())

        # Load image from URL or path
        if image_source.startswith(("http://", "https://")):
            req = urllib.request.urlopen(image_source)
            arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        else:
            img = cv2.imread(image_source)

        if img is None:
            raise ValueError(f"Could not load image source: {image_source}")

        h_img, w_img, _ = img.shape
        img_area = h_img * w_img

        # 1. Edge & Contour Detection for Panel Borders
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)

        # Adaptive thresholding to handle varied gutter lighting
        thresh = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )

        # Morphological operations to close broken panel border lines
        k_val = max(3, kernel_size | 1)  # Ensure odd kernel size
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_val, k_val))
        morphed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        bounding_boxes = []
        min_area = img_area * min_area_ratio

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h

            # Filter out non-panel artifacts or entire page bounding box
            if area > min_area and area < (img_area * 0.98):
                bounding_boxes.append((x, y, w, h))

        # Sort panels top-to-bottom, left-to-right
        bounding_boxes = sorted(bounding_boxes, key=lambda b: (b[1] // 100, b[0]))

        # Fallback: Treat whole page as 1 panel if no contours matched
        if not bounding_boxes:
            bounding_boxes = [(0, 0, w_img, h_img)]

        panel_nodes = []
        custom_config = f"--psm {psm_mode}"

        for idx, (x, y, w, h) in enumerate(bounding_boxes, start=1):
            crop = img[y:y+h, x:x+w]
            crop_filename = f"panel_{timestamp}_{idx:02d}.png"
            crop_rel_path = f"assets/{crop_filename}"
            crop_full_path = os.path.join(output_assets_dir, crop_filename)

            cv2.imwrite(crop_full_path, crop)

            # OCR Execution with Language Fallback
            extracted_text = ""
            try:
                pil_crop = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                extracted_text = pytesseract.image_to_string(pil_crop, lang=lang, config=custom_config).strip()
            except pytesseract.TesseractError as terr:
                print(f"[CSA OCR Warning] Language '{lang}' error: {terr}. Falling back to 'eng'...")
                try:
                    extracted_text = pytesseract.image_to_string(pil_crop, lang="eng", config=custom_config).strip()
                except Exception as ex:
                    print(f"[CSA OCR Error] OCR execution failed: {ex}")

            # Calculate Aspect Ratio
            aspect_ratio = "portrait" if h >= w else "landscape"

            panel_nodes.append({
                "id": f"panel_{timestamp}_{idx:02d}",
                "type": "panel_child",
                "enabled": True,
                "title": f"Panel {idx:02d}",
                "original_image": crop_rel_path,
                "source_file": source_rel_path,
                "extracted_text": extracted_text,
                "ocr_lang": lang,
                "aspect_ratio": aspect_ratio,
                "children": []
            })

        return panel_nodes

    def detect_text_bubbles(self, panel_image_path: str) -> List[Dict[str, Any]]:
        """HOOK_DETECT_BUBBLES: Extracts text and bounding boxes from speech bubbles."""
        if not os.path.exists(panel_image_path):
            return []

        extracted_text = ""
        if pytesseract:
            try:
                img = cv2.imread(panel_image_path)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                raw_text = pytesseract.image_to_string(gray, lang=self.default_lang)
                extracted_text = " ".join(raw_text.split())
            except Exception as e:
                print(f"[CSA OCR Warning] detect_text_bubbles failed: {e}")

        return [{"bbox": [0, 0, 0, 0], "text": extracted_text}]

    def isolate_elements(self, panel_image_path: str, output_dir: str) -> List[Dict[str, Any]]:
        """HOOK_ISOLATE_ELEMENTS: Cuts out foreground characters and props."""
        return []

    def detect_panel_boxes(
        self,
        img: np.ndarray,
        kernel_size: int = 5,
        min_area_ratio: float = 0.01
    ) -> List[Dict[str, float]]:
        """Finds panel bounding boxes normalized from 0.0 to 1.0 (relative to width/height)."""
        h_img, w_img, _ = img.shape
        img_area = h_img * w_img

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)

        thresh = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )

        k_val = max(3, kernel_size | 1)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_val, k_val))
        morphed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        bounding_boxes = []
        min_area = img_area * min_area_ratio

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            if area > min_area and area < (img_area * 0.98):
                bounding_boxes.append((x, y, w, h))

        # Sort top-to-bottom, left-to-right
        bounding_boxes = sorted(bounding_boxes, key=lambda b: (b[1] // 100, b[0]))

        if not bounding_boxes:
            bounding_boxes = [(0, 0, w_img, h_img)]

        # Normalize coordinates
        normalized_boxes = []
        for (x, y, w, h) in bounding_boxes:
            normalized_boxes.append({
                "x": round(x / w_img, 4),
                "y": round(y / h_img, 4),
                "w": round(w / w_img, 4),
                "h": round(h / h_img, 4),
                "pixel_box": (x, y, w, h)
            })

        return normalized_boxes

    def extract_bubbles_from_panel(self, panel_crop: np.ndarray, lang: str = "fra") -> List[Dict[str, Any]]:
        """Isolates speech/thought bubbles and captions, runs pre-OCR thresholding, and classifies text style."""
        h_p, w_p, _ = panel_crop.shape
        hsv = cv2.cvtColor(panel_crop, cv2.COLOR_BGR2HSV)

        # High Value (brightness) and lower Saturation isolates light/white bubble backgrounds
        mask = cv2.inRange(hsv, (0, 0, 180), (180, 60, 255))

        # Close small gaps in bubble outlines
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        text_regions = []

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            panel_area = h_p * w_p

            # Filter out tiny artifacts or panel-sized backgrounds
            if area < (panel_area * 0.015) or area > (panel_area * 0.85):
                continue

            # Classify bubble contour geometry
            perimeter = cv2.arcLength(cnt, True)
            circularity = (4 * np.pi * area) / (perimeter ** 2 + 1e-5)

            # Simple heuristic classification
            if y < (h_p * 0.25) and (w / h) > 2.2:
                text_type = "caption"      # Top rectangle banner
            elif circularity < 0.35:
                text_type = "thought"      # Cloud/scalloped border shape
            else:
                text_type = "speech"       # Regular smooth speech oval

            # Crop region and pre-process for OCR
            crop = panel_crop[y:y+h, x:x+w]
            gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

            # OTSU binarization for clear black text on white
            _, binary = cv2.threshold(gray_crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            padded = cv2.copyMakeBorder(binary, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=[255, 255, 255])

            raw_ocr = ""
            try:
                pil_crop = Image.fromarray(padded)
                raw_ocr = pytesseract.image_to_string(pil_crop, lang=lang, config="--psm 6").strip()
            except Exception:
                pass

            text_regions.append({
                "bbox": [round(x / w_p, 4), round(y / h_p, 4), round(w / w_p, 4), round(h / h_p, 4)],
                "text_type": text_type,
                "raw_ocr": raw_ocr,
                "cleaned_text": raw_ocr
            })

        return text_regions

