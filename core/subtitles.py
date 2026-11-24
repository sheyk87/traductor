"""Subtitle generator supporting SRT and WebVTT formats with clean line breaking."""

import textwrap
from pathlib import Path
from typing import List, Dict, Any
from core.utils import format_srt_time, format_vtt_time


def wrap_subtitle_text(text: str, max_width: int = 42, max_lines: int = 2) -> str:
    """Wraps subtitle lines cleanly so they fit well on screen."""
    lines = textwrap.wrap(text, width=max_width)
    if len(lines) > max_lines:
        # Re-wrap with slightly larger threshold to avoid exceeding 2 lines
        lines = textwrap.wrap(text, width=int(max_width * 1.25))
    return "\n".join(lines[:max_lines])


class SubtitleGenerator:
    """Generates standard .srt and .vtt subtitle files from translated segments."""

    @staticmethod
    def generate_srt(segments: List[Dict[str, Any]], output_file: Path) -> Path:
        """Writes translated segments to a standard SRT file."""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        blocks = []

        for idx, seg in enumerate(segments, start=1):
            start_str = format_srt_time(seg["start"])
            end_str = format_srt_time(seg["end"])
            target_text = seg.get("text_target") or seg.get("text_es") or seg.get("text_en") or ""
            text = wrap_subtitle_text(target_text)
            blocks.append(f"{idx}\n{start_str} --> {end_str}\n{text}\n")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(blocks).strip() + "\n")

        return output_file

    @staticmethod
    def generate_vtt(segments: List[Dict[str, Any]], output_file: Path) -> Path:
        """Writes translated segments to a standard WebVTT file."""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        blocks = ["WEBVTT\n"]

        for idx, seg in enumerate(segments, start=1):
            start_str = format_vtt_time(seg["start"])
            end_str = format_vtt_time(seg["end"])
            target_text = seg.get("text_target") or seg.get("text_es") or seg.get("text_en") or ""
            text = wrap_subtitle_text(target_text)
            blocks.append(f"{idx}\n{start_str} --> {end_str}\n{text}\n")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(blocks).strip() + "\n")

        return output_file
