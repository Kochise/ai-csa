# author: d.koch
# coding: utf-8
# naming: pep-0008
# typing: pep-0484
# docstring: pep-0257
# indentation: 4 spaces

""" src/csa_img_extract__EasyOCR.py
EasyOCR concrete implementation of CSAExtractorBase using PyTorch deep-learning recognition heads.
"""

import numpy as np
from csa_img_extract import CSAExtractorBase

try:
    import easyocr
except ImportError:
    easyocr = None

class CSAEasyOCRExtractor(CSAExtractorBase):
    """EasyOCR backend optimized for deep learning text detection across diverse cartoon fonts."""

    def __init__(self, lang_list: list = ["fr", "en"]):
        if easyocr is None:
            raise ImportError("EasyOCR is not installed. Run 'pip install easyocr'.")
        self.reader = easyocr.Reader(lang_list)

    def detect_panel_boxes(self, cv_img: np.ndarray, kernel_size: int = 5, min_area_ratio: float = 0.01) -> list:
        from csa_extractor import detect_panel_boxes as default_detect
        return default_detect(cv_img, kernel_size=kernel_size, min_area_ratio=min_area_ratio)

    def extract_bubbles_from_panel(self, panel_crop: np.ndarray, lang: str = "fra") -> list:
        h_img, w_img = panel_crop.shape[:2]
        # EasyOCR returns list of ([x,y coordinates], text, confidence)
        results = self.reader.readtext(panel_crop)
        regions = []

        for bbox_pts, text, conf in results:
            xs = [pt[0] for pt in bbox_pts]
            ys = [pt[1] for pt in bbox_pts]
            min_x, max_x = max(0.0, min(xs)), min(w_img, max(xs))
            min_y, max_y = max(0.0, min(ys)), min(h_img, max(ys))

            x_pct = round(min_x / w_img, 4)
            y_pct = round(min_y / h_img, 4)
            w_pct = round((max_x - min_x) / w_img, 4)
            h_pct = round((max_y - min_y) / h_img, 4)

            if w_pct > 0.02 and h_pct > 0.02:
                regions.append({
                    "text_type": "speech",
                    "cleaned_text": text.strip(),
                    "raw_ocr": text.strip(),
                    "bbox": [x_pct, y_pct, w_pct, h_pct],
                    "detected_lang": lang,
                    "user_modified_type": False
                })

        return regions