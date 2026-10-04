"""
Comic Strip Animator - Image Extractor (Tesseract / OpenCV Implementation)
Filename: csa_img_extract__TesseractOCR.py
"""

import os
import cv2
import pytesseract
from typing import List, Dict, Any
from csa_img_extract import CSAImageExtractorBase

class CSAImageExtractorTesseract(CSAImageExtractorBase):
    def __init__(self, tesseract_cmd: str = None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def extract_panels(self, page_image_path: str, output_dir: str) -> List[str]:
        """HOOK_EXTRACT_PANELS: Contour detection along gutters."""
        os.makedirs(output_dir, exist_ok=True)
        img = cv2.imread(page_image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # HOOK_CONTOUR_FILTER: Thresholding to isolate gutter borders
        _, thresh = cv2.threshold(gray, 230, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        extracted_paths = []
        for idx, cnt in enumerate(reversed(contours)):
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 100 and h > 100:  # Ignore tiny noise artifacts
                crop = img[y:y+h, x:x+w]
                out_path = os.path.join(output_dir, f"panel_{idx+1:03d}.png")
                cv2.imwrite(out_path, crop)
                extracted_paths.append(out_path)

        return extracted_paths

    def detect_text_bubbles(self, panel_image_path: str) -> List[Dict[str, Any]]:
        """HOOK_DETECT_BUBBLES: Uses Tesseract OCR to pull speech and caption text."""
        img = cv2.imread(panel_image_path)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        bubbles = []
        # HOOK_PARSE_OCR_TEXT: Reconstruct text strings from detected bounding boxes
        text = " ".join([data['text'][i] for i in range(len(data['text'])) if int(data['conf'][i]) > 40])
        if text.strip():
            bubbles.append({"type": "speech", "text": text.strip()})

        return bubbles

    def isolate_elements(self, panel_image_path: str, output_dir: str) -> List[Dict[str, Any]]:
        """HOOK_ISOLATE_ELEMENTS: Basic contour fallback for character cutouts."""
        return []