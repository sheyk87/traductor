"""End-to-end test script: generates a synthetic English video and tests the entire pipeline."""

import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import edge_tts
import static_ffmpeg

static_ffmpeg.add_paths()
ffmpeg_bin = shutil.which("ffmpeg")

SAMPLE_DIR = Path(__file__).parent / "samples"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

ENGLISH_VIDEO = SAMPLE_DIR / "sample_english.mp4"
ENGLISH_AUDIO = SAMPLE_DIR / "sample_voice.mp3"


async def generate_english_audio():
    text = "Hello and welcome to this tutorial. Today we are learning how to translate videos with artificial intelligence."
    communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
    await communicate.save(str(ENGLISH_AUDIO))


def generate_synthetic_video():
    print("[1/3] Sintetizando audio en inglés para la prueba...")
    asyncio.run(generate_english_audio())

    print("[2/3] Generando video de prueba sintético (6-7 segundos)...")
    # Generate video with test pattern and combine with synthesized audio
    cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=7:size=640x360:rate=25",
        "-i", str(ENGLISH_AUDIO),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        str(ENGLISH_VIDEO),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Video generado en: {ENGLISH_VIDEO}")


def run_pipeline_test():
    print("[3/3] Ejecutando pipeline completo de traducción...")
    from core.config import TranslationConfig
    from core.pipeline import VideoTranslationPipeline

    # Use model='tiny' for ultra-fast unit testing
    config = TranslationConfig(
        voice="es-MX-JorgeNeural",
        whisper_model="tiny",
        keep_background=False,  # Skip demucs for fast synthetic test
        burn_subtitles=True,
    )

    pipeline = VideoTranslationPipeline(config)
    output_video = SAMPLE_DIR / "sample_translated_es.mp4"

    res = pipeline.run(
        video_path=str(ENGLISH_VIDEO),
        output_path=str(output_video),
        progress_callback=lambda stage, pct: print(f"  [{int(pct*100)}%] {stage}"),
    )

    print("\nResultados de la prueba:")
    for k, v in res.items():
        print(f"  {k}: {v}")

    assert output_video.exists(), "El video final no fue creado."
    assert Path(res["subtitles_srt"]).exists(), "El archivo .srt no fue creado."
    assert Path(res["subtitles_vtt"]).exists(), "El archivo .vtt no fue creado."

    print("\n¡Prueba de integración exitosa!")


if __name__ == "__main__":
    generate_synthetic_video()
    run_pipeline_test()
