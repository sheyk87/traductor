"""End-to-end integration test for Spanish -> English video translation."""

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

SPANISH_VIDEO = SAMPLE_DIR / "sample_spanish.mp4"
SPANISH_AUDIO = SAMPLE_DIR / "sample_spanish_voice.mp3"


async def generate_spanish_audio():
    text = "Hola y bienvenidos. Hoy aprenderemos a traducir videos de español a inglés usando inteligencia artificial."
    communicate = edge_tts.Communicate(text, "es-MX-JorgeNeural")
    await communicate.save(str(SPANISH_AUDIO))


def generate_synthetic_spanish_video():
    print("[1/3] Sintetizando audio en español para la prueba...")
    asyncio.run(generate_spanish_audio())

    print("[2/3] Generando video de prueba en español...")
    cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=7:size=640x360:rate=25",
        "-i", str(SPANISH_AUDIO),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        str(SPANISH_VIDEO),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Video generado en: {SPANISH_VIDEO}")


def run_es_to_en_test():
    print("[3/3] Ejecutando traducción Español -> Inglés...")
    from core.config import TranslationConfig
    from core.pipeline import VideoTranslationPipeline

    config = TranslationConfig(
        voice="en-US-GuyNeural",
        whisper_model="tiny",
        keep_background=False,
        burn_subtitles=True,
        source_lang="es",
        target_lang="en",
    )

    pipeline = VideoTranslationPipeline(config)
    output_video = SAMPLE_DIR / "sample_translated_en.mp4"

    res = pipeline.run(
        video_path=str(SPANISH_VIDEO),
        output_path=str(output_video),
        progress_callback=lambda stage, pct: print(f"  [{int(pct*100)}%] {stage}"),
    )

    print("\nResultados de la prueba (ES -> EN):")
    for k, v in res.items():
        print(f"  {k}: {v}")

    assert output_video.exists(), "El video final en inglés no fue creado."
    assert Path(res["subtitles_srt"]).exists(), "El archivo .srt no fue creado."

    print("\n¡Prueba de traducción Español -> Inglés completada con éxito!")


if __name__ == "__main__":
    generate_synthetic_spanish_video()
    run_es_to_en_test()
