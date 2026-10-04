"""
Comic Strip Animator - Video Generation Base Interface
Filename: csa_vid_generate.py
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List

class CSAVideoGeneratorBase(ABC):

    @abstractmethod
    def generate_plan_video(self, panel_data: Dict[str, Any], output_path: str) -> str:
        """HOOK_GENERATE_PLAN: Renders an individual panel into a plan video clip."""
        pass

    @abstractmethod
    def stitch_sequence(self, plan_paths: List[str], audio_path: str, output_path: str) -> str:
        """HOOK_STITCH_SEQUENCE: Combines plan videos into a parent sequence."""
        pass