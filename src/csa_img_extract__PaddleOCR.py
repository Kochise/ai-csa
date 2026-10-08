# author: d.koch
# coding: utf-8
# naming: pep-0008
# typing: pep-0484
# docstring: pep-0257
# indentation: 4 spaces

""" src/csa_img_extract__PaddleOCR.py
PaddleOCR concrete implementation of CSAExtractorBase for superior multi-language and stylized text recognition.
"""

import numpy as np
from csa_img_extract import CSAExtractorBase

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

class CSAPaddleOCRExtractor(CSAExtractorBase):
    """PaddleOCR backend supporting robust recognition on low-quality or stylized hand-lettered comic fonts."""

    def __init__(self, lang: str = "fr"):
        if PaddleOCR is None:
            raise ImportError("PaddleOCR is not installed. Run 'pip install paddleocr paddlepaddle'.")
        # Initialize PaddleOCR with language support
        self.ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)

    def detect_panel_boxes(self, cv_img: np.ndarray, kernel_size: int = 5, min_area_ratio: float = 0.01) -> list:
        # Delegates to standard contour detection or uses paddle layout analysis
        from csa_extractor import detect_panel_boxes as default_detect
        return default_detect(cv_img, kernel_size=kernel_size, min_area_ratio=min_area_ratio)

    def extract_bubbles_from_panel(self, panel_crop: np.ndarray, lang: str = "fra") -> list:
        h_img, w_img = panel_crop.shape[:2]
        result = self.ocr.ocr(panel_crop, cls=True)
        regions = []

        if not result or not result[0]:
            return regions

        for line in result[0]:
            box_coords, (text, confidence) = line
            # box_coords is 4 points [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            xs = [pt[0] for pt in box_coords]
            ys = [pt[1] for pt in box_coords]
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