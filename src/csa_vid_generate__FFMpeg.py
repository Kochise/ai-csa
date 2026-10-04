"""
Comic Strip Animator - Video Generator (FFmpeg / Fallback Implementation)
Filename: csa_vid_generate__FFMpeg.py
"""

import subprocess
import os
from typing import Dict, Any, List
from csa_vid_generate import CSAVideoGeneratorBase

class CSAVideoGeneratorFFMpeg(CSAVideoGeneratorBase):

    def generate_plan_video(self, panel_data: Dict[str, Any], output_path: str) -> str:
        """HOOK_GENERATE_PLAN: Creates a 3-second animated zoom/pan preview from a panel image."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img_path = panel_data.get("background_image") or panel_data.get("original_image")

        # HOOK_FFMPEG_PAN_ZOOM: Smooth zoom pan over the panel image
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", img_path,
            "-vf", "zoompan=z='min(zoom+0.0015,1.15)':d=75:s=1280x720",
            "-t", "3", "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path

    def stitch_sequence(self, plan_paths: List[str], audio_path: str, output_path: str) -> str:
        """HOOK_STITCH_SEQUENCE: Concatenates plan videos into a single MP4 sequence."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        list_file = output_path + ".txt"

        # HOOK_WRITE_CONCAT_FILE: Prepares file list for FFmpeg concat filter
        with open(list_file, "w") as f:
            for path in plan_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
            "-c", "copy", output_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(list_file):
            os.remove(list_file)
        return output_path