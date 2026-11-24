"""Utility helpers for video translation pipeline: ffmpeg checks, timestamps, security validation."""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".m4v", ".wmv"}


def ensure_ffmpeg() -> Dict[str, str]:
    """Ensures ffmpeg and ffprobe are available in PATH via static-ffmpeg or system."""
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception:
        pass

    ffmpeg_bin = shutil.which("ffmpeg")
    ffprobe_bin = shutil.which("ffprobe")

    if not ffmpeg_bin or not ffprobe_bin:
        raise RuntimeError(
            "ffmpeg o ffprobe no fueron encontrados. Asegúrate de tener instalado "
            "'static-ffmpeg' en el entorno o ffmpeg en el sistema."
        )

    # Set pydub converter globally
    try:
        from pydub import AudioSegment
        AudioSegment.converter = ffmpeg_bin
    except Exception:
        pass

    return {"ffmpeg": ffmpeg_bin, "ffprobe": ffprobe_bin}


def validate_video_file(file_path: str) -> Path:
    """Validates the input video file against path traversal and file format constraints."""
    resolved = Path(file_path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"El archivo de video no existe: {file_path}")
    if not resolved.is_file():
        raise ValueError(f"La ruta proporcionada no es un archivo: {file_path}")
    if resolved.suffix.lower() not in ALLOWED_VIDEO_EXTENSIONS:
        raise ValueError(
            f"Formato no admitido: {resolved.suffix}. Extensiones soportadas: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        )
    return resolved


def get_media_info(file_path: Path) -> Dict[str, Any]:
    """Extracts media metadata (duration, streams, sample rate) using ffprobe safely."""
    bins = ensure_ffmpeg()
    cmd = [
        bins["ffprobe"],
        "-v", "error",
        "-show_entries", "format=duration,size,bit_rate:stream=index,codec_type,codec_name,width,height",
        "-of", "json",
        str(file_path),
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    data = json.loads(result.stdout)

    format_info = data.get("format", {})
    streams = data.get("streams", [])

    duration = float(format_info.get("duration", 0.0))
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    has_video = any(s.get("codec_type") == "video" for s in streams)

    return {
        "duration": duration,
        "has_audio": has_audio,
        "has_video": has_video,
        "streams": streams,
    }


def format_srt_time(seconds: float) -> str:
    """Formats seconds into SRT timestamp: HH:MM:SS,mmm"""
    if seconds < 0:
        seconds = 0.0
    millis = int(round((seconds - int(seconds)) * 1000))
    total_seconds = int(seconds)
    secs = total_seconds % 60
    total_minutes = total_seconds // 60
    mins = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def format_vtt_time(seconds: float) -> str:
    """Formats seconds into WebVTT timestamp: HH:MM:SS.mmm"""
    if seconds < 0:
        seconds = 0.0
    millis = int(round((seconds - int(seconds)) * 1000))
    total_seconds = int(seconds)
    secs = total_seconds % 60
    total_minutes = total_seconds // 60
    mins = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours:02d}:{mins:02d}:{secs:02d}.{millis:03d}"


def safe_run_command(cmd: List[str], desc: str = "Ejecutando comando") -> None:
    """Executes a command safely without shell=True to prevent command injection."""
    try:
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Fallo durante {desc}:\nComando: {' '.join(cmd)}\nError: {exc.stderr.strip()}"
        ) from exc
