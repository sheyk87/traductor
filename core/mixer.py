"""Audio mixer for combining Spanish vocals with background music and effects."""

from pathlib import Path
from typing import Optional, List, Dict, Any
from pydub import AudioSegment
from core.utils import ensure_ffmpeg


class AudioMixer:
    """Mixes Spanish vocal audio with background instrumental audio using level normalization."""

    def __init__(self, target_sample_rate: int = 44100):
        self.target_sample_rate = target_sample_rate
        ffmpeg_bins = ensure_ffmpeg()
        AudioSegment.converter = ffmpeg_bins["ffmpeg"]

    def mix(
        self,
        vocals_wav: Path,
        background_wav: Optional[Path],
        output_wav: Path,
        bg_ducking_db: float = -7.0,
    ) -> Path:
        """Combines vocal track with optional background track."""
        output_wav.parent.mkdir(parents=True, exist_ok=True)

        vocals = AudioSegment.from_file(vocals_wav)
        vocals = vocals.set_frame_rate(self.target_sample_rate).set_channels(2)

        if background_wav is not None and background_wav.exists():
            bg = AudioSegment.from_file(background_wav)
            bg = bg.set_frame_rate(self.target_sample_rate).set_channels(2)

            # Match lengths (in case background is slightly shorter or longer)
            if len(bg) < len(vocals):
                silence = AudioSegment.silent(
                    duration=len(vocals) - len(bg),
                    frame_rate=self.target_sample_rate,
                ).set_channels(2)
                bg = bg + silence
            elif len(bg) > len(vocals):
                bg = bg[: len(vocals)]

            # Lower background audio so translated speech is clear and dominant
            bg = bg + bg_ducking_db

            # Overlay vocals on top of ducked background
            mixed = bg.overlay(vocals)
        else:
            mixed = vocals

        # Peak normalization to -1.0 dBFS to prevent clipping
        if mixed.max_dBFS > -1.0:
            gain = -1.0 - mixed.max_dBFS
            mixed = mixed.apply_gain(gain)

        mixed.export(output_wav, format="wav")
        return output_wav
