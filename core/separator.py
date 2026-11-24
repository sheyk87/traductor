"""Vocal and background music/effects separation using Demucs."""

import os
import sys
from pathlib import Path
from typing import Dict, Optional
from core.utils import safe_run_command, ensure_ffmpeg


class AudioSeparator:
    """Handles audio separation into vocals and instrumental/background audio."""

    def __init__(self, model_name: str = "htdemucs", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self.ffmpeg_bins = ensure_ffmpeg()

    def extract_audio_from_video(self, video_path: Path, output_wav: Path) -> Path:
        """Extracts audio from video file to 16-bit PCM WAV."""
        cmd = [
            self.ffmpeg_bins["ffmpeg"],
            "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "2",
            str(output_wav),
        ]
        safe_run_command(cmd, "Extracción de audio del video")
        return output_wav

    def separate(self, audio_wav: Path, output_dir: Path) -> Dict[str, Optional[Path]]:
        """Separates audio into vocals and background (no_vocals)."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # We run demucs as a python module
        cmd = [
            sys.executable,
            "-m", "demucs",
            "-n", self.model_name,
            "--two-stems=vocals",
            "-d", self.device,
            "-o", str(output_dir),
            str(audio_wav),
        ]

        safe_run_command(cmd, "Separación de pistas con Demucs (voz vs fondo)")

        # Demucs output structure: <output_dir>/<model_name>/<track_name>/vocals.wav and no_vocals.wav
        track_name = audio_wav.stem
        model_out = output_dir / self.model_name / track_name
        vocals_path = model_out / "vocals.wav"
        background_path = model_out / "no_vocals.wav"

        if not vocals_path.exists() or not background_path.exists():
            raise FileNotFoundError(
                f"No se encontraron las pistas separadas en {model_out}. "
                "Verifica que Demucs haya procesado el archivo correctamente."
            )

        return {
            "vocals": vocals_path,
            "background": background_path,
        }
