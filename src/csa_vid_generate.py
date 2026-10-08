# author: d.koch
# coding: utf-8
# naming: pep-0008
# typing: pep-0484
# docstring: pep-0257
# indentation: 4 spaces

""" csa_vid_generate.py
Comic Strip Animator - Video Generation Base Interface
"""

# - - - IMPORT - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

from abc import ABC, abstractmethod
from typing import Dict, Any, List

# - - - CLASS - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class CSAVideoGeneratorBase(ABC):

    @abstractmethod
    def generate_plan_video(self, panel_data: Dict[str, Any], output_path: str) -> str:
        """HOOK_GENERATE_PLAN: Renders an individual panel into a plan video clip."""
        pass

    @abstractmethod
    def stitch_sequence(self, plan_paths: List[str], audio_path: str, output_path: str) -> str:
        """HOOK_STITCH_SEQUENCE: Combines plan videos into a parent sequence."""
        pass
