"""Text-to-Speech synthesis using Edge-TTS with intelligent pitch-preserving time synchronization."""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

import edge_tts
from pydub import AudioSegment

from core.utils import ensure_ffmpeg, safe_run_command
from core.config import DEFAULT_VOICE


class TTSEngine:
    """Synthesizes Spanish audio segments and synchronizes them to the original video timeline."""

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        max_speed_factor: float = 1.45,
        target_sample_rate: int = 44100,
    ):
        self.voice = voice
        self.max_speed_factor = max_speed_factor
        self.target_sample_rate = target_sample_rate
        self.ffmpeg_bins = ensure_ffmpeg()
        AudioSegment.converter = self.ffmpeg_bins["ffmpeg"]

    def _adjust_audio_speed(self, input_wav: Path, output_wav: Path, speed_factor: float) -> Path:
        """Changes audio tempo/speed without altering pitch using ffmpeg atempo filter."""
        # atempo filter supports values from 0.5 to 2.0
        clamped_factor = max(0.5, min(2.0, speed_factor))
        cmd = [
            self.ffmpeg_bins["ffmpeg"],
            "-y",
            "-i", str(input_wav),
            "-filter:a", f"atempo={clamped_factor:.4f}",
            "-ar", str(self.target_sample_rate),
            "-ac", "2",
            str(output_wav),
        ]
        safe_run_command(cmd, f"Ajuste de velocidad de audio (factor {speed_factor:.2f})")
        return output_wav

    async def _synthesize_single_segment(
        self,
        text: str,
        output_file: Path,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Synthesizes a single segment to an audio file using edge-tts with concurrency limits."""
        async with semaphore:
            for attempt in range(3):
                try:
                    communicate = edge_tts.Communicate(text, self.voice)
                    await communicate.save(str(output_file))
                    return
                except Exception as e:
                    if attempt == 2:
                        raise e
                    await asyncio.sleep(1.0 + attempt)

    async def synthesize_all_segments(
        self,
        segments: List[Dict[str, Any]],
        temp_dir: Path,
        max_concurrency: int = 4,
    ) -> List[Path]:
        """Synthesizes all text segments in parallel with rate control."""
        semaphore = asyncio.Semaphore(max_concurrency)
        tasks = []
        raw_audio_paths = []

        for idx, seg in enumerate(segments):
            out_path = temp_dir / f"raw_seg_{idx:04d}.mp3"
            raw_audio_paths.append(out_path)
            text_to_speak = seg.get("text_target") or seg.get("text_es") or seg.get("text_en") or ""
            tasks.append(
                self._synthesize_single_segment(text_to_speak, out_path, semaphore)
            )

        await asyncio.gather(*tasks)
        return raw_audio_paths

    def build_synchronized_track(
        self,
        segments: List[Dict[str, Any]],
        total_duration_seconds: float,
        output_wav: Path,
    ) -> Path:
        """Assembles a frame-accurate, drift-free vocal track aligned to the timeline."""
        output_wav.parent.mkdir(parents=True, exist_ok=True)
        total_ms = int(total_duration_seconds * 1000)

        # Initialize silent stereo timeline
        timeline = AudioSegment.silent(duration=total_ms, frame_rate=self.target_sample_rate)
        timeline = timeline.set_channels(2)

        with tempfile.TemporaryDirectory(prefix="tts_sync_") as tmp:
            tmp_path = Path(tmp)

            # Step 1: Synthesize all raw segments via async edge-tts
            raw_paths = asyncio.run(self.synthesize_all_segments(segments, tmp_path))

            # Step 2: Time-stretch and place each segment onto the timeline
            for idx, (seg, raw_path) in enumerate(zip(segments, raw_paths)):
                if not raw_path.exists() or raw_path.stat().st_size == 0:
                    continue

                start_sec = seg["start"]
                end_sec = seg["end"]
                start_ms = int(start_sec * 1000)
                target_duration_sec = max(0.5, end_sec - start_sec)

                # Determine the max available window before the next segment starts
                if idx + 1 < len(segments):
                    next_start_sec = segments[idx + 1]["start"]
                    # Leave 60ms breathing room before next speech segment
                    available_sec = max(target_duration_sec, next_start_sec - start_sec - 0.06)
                else:
                    available_sec = max(target_duration_sec, total_duration_seconds - start_sec)

                # Load generated audio segment
                audio_seg = AudioSegment.from_file(raw_path)
                gen_duration_sec = len(audio_seg) / 1000.0

                # Check if generated audio exceeds available window
                if gen_duration_sec > available_sec:
                    speed_factor = gen_duration_sec / available_sec
                    # Clamp speed factor to avoid unnatural pitch or cartoonish sound
                    speed_factor = min(speed_factor, self.max_speed_factor)

                    if speed_factor > 1.04:
                        wav_input = tmp_path / f"input_{idx:04d}.wav"
                        wav_output = tmp_path / f"sped_{idx:04d}.wav"
                        audio_seg.export(wav_input, format="wav")
                        self._adjust_audio_speed(wav_input, wav_output, speed_factor)
                        audio_seg = AudioSegment.from_file(wav_output)

                # Ensure uniform audio parameters
                audio_seg = audio_seg.set_frame_rate(self.target_sample_rate).set_channels(2)

                # Overlay segment at the exact start timestamp
                if start_ms < total_ms:
                    timeline = timeline.overlay(audio_seg, position=start_ms)

        # Export full vocal track
        timeline.export(output_wav, format="wav")
        return output_wav
