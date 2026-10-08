# author: d.koch
# coding: utf-8
# naming: pep-0008
# typing: pep-0484
# docstring: pep-0257
# indentation: 4 spaces

""" src/csa_img_extract.py
Comic Strip Animator - Image Extraction Base API Interface
"""

# - - - IMPORT - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

import numpy as np
import pytesseract

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

from abc import ABC, abstractmethod
from PIL import Image
from typing import List, Dict, Any

# - - - CLASS - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class CSAImageExtractor(ABC):
    """Abstract Base Class for comic panel extraction, speech bubble segmentation, and OCR engines."""

    @abstractmethod
    def detect_panel_boxes(
        self,
        img: np.ndarray,
        kernel_size: int = 5,
        min_area_ratio: float = 0.01
    ) -> List[Dict[str, float]]:
        pass

    @abstractmethod
    def extract_bubbles_from_panel(
        self,
        panel_crop: np.ndarray,
        lang: str = "fra"
    ) -> List[Dict[str, Any]]:
        pass

    def extract_text(self, crop: np.ndarray, lang: str = "fra", params: dict = None) -> str:
        """Default concrete implementation for single-region OCR extraction using Tesseract."""
        pil_img = Image.fromarray(crop)
        text = ""
        try:
            text = pytesseract.image_to_string(pil_img, lang=lang, config="--psm 6").strip()
        except Exception:
            pass
        if not text:
            try:
                text = pytesseract.image_to_string(pil_img, lang=lang, config="--psm 11").strip()
            except Exception:
                pass
        return text

# Alias for backward compatibility with concrete extractor imports
CSAExtractorBase = CSAImageExtractor

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

class CSATesseractExtractor(CSAImageExtractor):
    """Tesseract concrete implementation."""

    def detect_panel_boxes(self, img: np.ndarray, kernel_size: int = 5, min_area_ratio: float = 0.01) -> list:
        from csa_extractor import detect_panel_boxes as default_detect
        return default_detect(img, kernel_size=kernel_size, min_area_ratio=min_area_ratio)

    def extract_bubbles_from_panel(self, panel_crop: np.ndarray, lang: str = "fra") -> list:
        return []


# Also alias CSAImageExtractorTesseract to CSATesseractExtractor if csa_main expects that name
CSAImageExtractorTesseract = CSATesseractExtractor

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

class CSAPaddleOCRExtractor(CSAImageExtractor):
    """PaddleOCR concrete implementation."""

    def __init__(self):
        try:
            from paddleocr import PaddleOCR
            # Désactivation complète des sous-modèles UVDoc et de redressement de document de type PaddleX
            self.ocr = PaddleOCR(
                use_angle_cls=False,
                det_model_dir=None,
                rec_model_dir=None,
                cls_model_dir=None,
                show_log=False,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False
            )
            print("[CSA Engine Init] PaddleOCR loaded successfully.")
        except Exception as e:
            self.ocr = None
            print(f"[CSA Engine Warning] PaddleOCR initialization failed: {e}")

    def detect_panel_boxes(self, img: np.ndarray, kernel_size: int = 5, min_area_ratio: float = 0.01) -> list:
        from csa_extractor import detect_panel_boxes as default_detect
        return default_detect(img, kernel_size=kernel_size, min_area_ratio=min_area_ratio)

    def extract_bubbles_from_panel(self, panel_crop: np.ndarray, lang: str = "fra") -> list:
        return []

    def extract_text(self, crop: np.ndarray, lang: str = "fra", params: dict = None) -> str:
        if not self.ocr:
            return "[Error: PaddleOCR not installed or failed to initialize]"
        try:
            result = self.ocr.ocr(crop, cls=False)
            if not result:
                return ""

            texts = []
            if isinstance(result, (list, tuple)):
                for res_item in result:
                    if res_item is None:
                        continue
                    if isinstance(res_item, (list, tuple)):
                        for line in res_item:
                            if isinstance(line, (list, tuple)):
                                for elem in line:
                                    if isinstance(elem, str) and len(elem.strip()) > 0:
                                        texts.append(elem)
                                    elif isinstance(elem, (list, tuple)):
                                        for sub in elem:
                                            if isinstance(sub, str) and len(sub.strip()) > 0:
                                                texts.append(sub)
                            elif isinstance(line, str):
                                texts.append(line)
                    elif isinstance(res_item, str):
                        texts.append(res_item)

            seen = set()
            unique_texts = [t for t in texts if not (t in seen or seen.add(t))]
            return " ".join(unique_texts).strip()
        except Exception as err:
            print(f"[CSA Engine Error] PaddleOCR extract_text failed: {err}")
            return f"[Error: PaddleOCR execution failed - {err}]"

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

class CSAEasyOCRExtractor(CSAImageExtractor):
    """EasyOCR concrete implementation."""

    def __init__(self):
        try:
            import easyocr
            self.reader = easyocr.Reader(['fr', 'en'], gpu=False)
            print("[CSA Engine Init] EasyOCR loaded successfully.")
        except Exception as e:
            self.reader = None
            print(f"[CSA Engine Warning] EasyOCR initialization failed: {e}")

    def detect_panel_boxes(self, img: np.ndarray, kernel_size: int = 5, min_area_ratio: float = 0.01) -> list:
        from csa_extractor import detect_panel_boxes as default_detect
        return default_detect(img, kernel_size=kernel_size, min_area_ratio=min_area_ratio)

    def extract_bubbles_from_panel(self, panel_crop: np.ndarray, lang: str = "fra") -> list:
        return []

    def extract_text(self, crop: np.ndarray, lang: str = "fra", params: dict = None) -> str:
        if not self.reader:
            return "[Error: EasyOCR not installed or failed to initialize]"
        try:
            results = self.reader.readtext(crop)
            texts = [res[1] for res in results if res and len(res) >= 2]
            return " ".join(texts).strip()
        except Exception as err:
            print(f"[CSA Engine Error] EasyOCR extract_text failed: {err}")
            return f"[Error: PaddleOCR execution failed - {err}]"

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def get_extractor_by_name(name: str) -> CSAImageExtractor:
    """Factory function returning the appropriate OCR extractor instance."""
    name_lower = name.lower()
    if "paddle" in name_lower:
        return CSAPaddleOCRExtractor()
    elif "easy" in name_lower:
        return CSAEasyOCRExtractor()
    else:
        return CSATesseractExtractor()
