"""
Comic Strip Animator - Image Extraction Base API Interface
Filename: csa_img_extract.py
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any

class CSAImageExtractorBase(ABC):
    """
    Generic Abstract Base Class for extracting panels, text, and elements.
    """

    @abstractmethod
    def extract_panels(self, page_image_path: str, output_dir: str) -> List[str]:
        """HOOK_EXTRACT_PANELS: Detects comic panels using gutter lines."""
        pass

    @abstractmethod
    def detect_text_bubbles(self, panel_image_path: str) -> List[Dict[str, Any]]:
        """HOOK_DETECT_BUBBLES: Extracts text and bounding boxes from speech bubbles."""
        pass

    @abstractmethod
    def isolate_elements(self, panel_image_path: str, output_dir: str) -> List[Dict[str, Any]]:
        """HOOK_ISOLATE_ELEMENTS: Cuts out foreground characters and props."""
        pass