"""Full video translation pipeline orchestrator."""

import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Callable, Optional

from core.config import TranslationConfig
from core.utils import validate_video_file, get_media_info
from core.separator import AudioSeparator
from core.transcriber import Transcriber
from core.translator import Translator
from core.subtitles import SubtitleGenerator
from core.tts_engine import TTSEngine
from core.mixer import AudioMixer
from core.video_processor import VideoProcessor


class VideoTranslationPipeline:
    """Orchestrates the entire video translation workflow."""

    def __init__(self, config: Optional[TranslationConfig] = None):
        self.config = config or TranslationConfig()
        self.separator = AudioSeparator()
        self.transcriber = Transcriber(model_size=self.config.whisper_model)
        self.translator = Translator(
            engine=self.config.translation_engine,
            source_lang=self.config.source_lang,
            target_lang=self.config.target_lang,
        )
        self.tts = TTSEngine(
            voice=self.config.voice,
            max_speed_factor=self.config.max_speed_factor,
            target_sample_rate=self.config.target_sample_rate,
        )
        self.mixer = AudioMixer(target_sample_rate=self.config.target_sample_rate)
        self.video_processor = VideoProcessor()

    def run(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """Runs the translation pipeline on the specified input video.

        Args:
            video_path: Path to the input video file.
            output_path: Optional path for the final translated video.
            progress_callback: Optional callback func(stage_name, progress_percentage).
        """
        start_time = time.time()

        def report(stage: str, pct: float):
            if progress_callback:
                progress_callback(stage, pct)

        # 1. Validation & Metadata extraction
        report("Validando archivo de video", 0.05)
        input_video = validate_video_file(video_path)
        media_info = get_media_info(input_video)

        if not media_info["has_audio"]:
            raise ValueError("El video proporcionado no contiene ninguna pista de audio para traducir.")

        total_duration = media_info["duration"]
        if total_duration <= 0:
            raise ValueError("No se pudo determinar la duración del video.")

        source_name = "inglés" if self.config.source_lang == "en" else "español"
        target_name = "español" if self.config.target_lang == "es" else "inglés"

        # Prepare output paths
        if output_path:
            final_video = Path(output_path).resolve()
        else:
            final_video = input_video.parent / f"{input_video.stem}_{self.config.target_lang}{input_video.suffix}"

        srt_file = final_video.with_suffix(".srt")
        vtt_file = final_video.with_suffix(".vtt")

        with tempfile.TemporaryDirectory(prefix="video_trans_") as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            raw_audio = tmp_dir / "original_audio.wav"

            # 2. Extract original audio
            report("Extrayendo audio del video", 0.10)
            self.separator.extract_audio_from_video(input_video, raw_audio)

            # 3. Audio separation (vocals vs background)
            bg_audio: Optional[Path] = None
            voice_for_stt = raw_audio

            if self.config.keep_background:
                report("Separando voz y música de fondo con Demucs IA", 0.20)
                try:
                    sep_result = self.separator.separate(raw_audio, tmp_dir / "separated")
                    voice_for_stt = sep_result["vocals"]
                    bg_audio = sep_result["background"]
                except Exception as e:
                    # In case separation fails or is skipped, proceed with original audio
                    voice_for_stt = raw_audio
                    bg_audio = None

            # 4. Transcription (STT with timestamps)
            report(f"Transcribiendo audio en {source_name} (Whisper IA)", 0.45)
            segments = self.transcriber.transcribe(voice_for_stt, language=self.config.source_lang)

            if not segments:
                raise RuntimeError("No se detectó voz o diálogo en el video.")

            # 5. Translation
            report(f"Traduciendo texto al {target_name}", 0.60)
            translated_segments = self.translator.translate_segments(segments)

            # 6. Subtitles export (.srt and .vtt)
            report(f"Generando subtítulos en {target_name}", 0.70)
            SubtitleGenerator.generate_srt(translated_segments, srt_file)
            SubtitleGenerator.generate_vtt(translated_segments, vtt_file)

            # 7. Text-To-Speech & Timeline Synchronization
            report(f"Sintetizando voz en {target_name} y sincronizando tiempos", 0.80)
            dubbed_vocals_wav = tmp_dir / f"{self.config.target_lang}_vocals.wav"
            self.tts.build_synchronized_track(
                translated_segments,
                total_duration_seconds=total_duration,
                output_wav=dubbed_vocals_wav,
            )

            # 8. Audio Mixing (Vocals + Background)
            report("Mezclando pistas de audio (voz + fondo)", 0.90)
            mixed_audio_wav = tmp_dir / "final_mixed_audio.wav"
            self.mixer.mix(
                vocals_wav=dubbed_vocals_wav,
                background_wav=bg_audio,
                output_wav=mixed_audio_wav,
                bg_ducking_db=self.config.bg_ducking_db,
            )

            # 9. Video Remuxing / Burning
            report("Creando video final traducido", 0.95)
            self.video_processor.process_video(
                original_video=input_video,
                dubbed_audio=mixed_audio_wav,
                subtitles_srt=srt_file,
                output_video=final_video,
                burn_subtitles=self.config.burn_subtitles,
                embed_subtitles=self.config.embed_subtitles,
                target_lang=self.config.target_lang,
            )

        elapsed = time.time() - start_time
        report("Traducción completada con éxito", 1.0)

        return {
            "output_video": str(final_video),
            "subtitles_srt": str(srt_file),
            "subtitles_vtt": str(vtt_file),
            "duration": total_duration,
            "segments_count": len(translated_segments),
            "elapsed_seconds": round(elapsed, 2),
            "voice": self.config.voice,
        }
