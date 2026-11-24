"""Command-line interface (CLI) for the bidirectional video translation system."""

import argparse
import sys
from pathlib import Path
from core.config import (
    TranslationConfig,
    SPANISH_VOICES,
    ENGLISH_VOICES,
    DEFAULT_VOICE_ES,
    DEFAULT_VOICE_EN,
    DEFAULT_WHISPER_MODEL,
    get_voices_for_lang,
)
from core.pipeline import VideoTranslationPipeline


def print_voices(filter_lang: str = "all"):
    """Prints a formatted table of recommended neural voices."""
    if filter_lang in ["all", "es"]:
        print("\n" + "=" * 70)
        print("VOCES NEURONALES EN ESPAÑOL (Edge-TTS)")
        print("=" * 70)
        for voice_id, info in SPANISH_VOICES.items():
            print(f" • ID: {voice_id}")
            print(f"   Nombre: {info['name']} | Género: {info['gender']}")
            print(f"   Detalle: {info['description']}")
            print("-" * 70)

    if filter_lang in ["all", "en"]:
        print("\n" + "=" * 70)
        print("VOCES NEURONALES EN INGLÉS (Edge-TTS)")
        print("=" * 70)
        for voice_id, info in ENGLISH_VOICES.items():
            print(f" • ID: {voice_id}")
            print(f"   Nombre: {info['name']} | Género: {info['gender']}")
            print(f"   Detalle: {info['description']}")
            print("-" * 70)

    print("\nPuedes usar cualquiera de estos IDs con el parámetro --voice <ID>\n")


def main():
    parser = argparse.ArgumentParser(
        description="Traductor bidireccional de videos (Inglés <-> Español) con doblaje y subtítulos sincronizados.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Traducción de inglés a español (predeterminado):
  python main.py video_ingles.mp4

  # Traducción de español a inglés:
  python main.py video_espanol.mp4 -d es-en

  # Traducción de español a inglés con voz femenina británica y subtítulos quemados:
  python main.py charla.mp4 -d es-en --voice en-GB-SoniaNeural --burn-subtitles

  # Ver la lista completa de voces (o filtrar con --lang es / --lang en):
  python main.py --list-voices
        """,
    )

    parser.add_argument(
        "video_path",
        nargs="?",
        help="Ruta al archivo de video que deseas traducir (ej. video.mp4)",
    )
    parser.add_argument(
        "-d", "--direction",
        default="en-es",
        choices=["en-es", "es-en"],
        help="Dirección de la traducción: en-es (Inglés a Español) o es-en (Español a Inglés)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Ruta o nombre para el video traducido final (por defecto: <nombre>_<idioma_destino>.mp4)",
    )
    parser.add_argument(
        "-v", "--voice",
        default=None,
        help="ID de la voz neural (por defecto: es-MX-JorgeNeural para español, en-US-GuyNeural para inglés)",
    )
    parser.add_argument(
        "-m", "--model",
        default=DEFAULT_WHISPER_MODEL,
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help=f"Modelo de Whisper para transcripción (por defecto: {DEFAULT_WHISPER_MODEL})",
    )
    parser.add_argument(
        "--engine",
        default="argos",
        choices=["argos", "google"],
        help="Motor de traducción (argos: 100%% offline y local; google: en línea)",
    )
    parser.add_argument(
        "--no-background",
        action="store_true",
        help="No separar música/efectos de fondo con Demucs (procesamiento más veloz)",
    )
    parser.add_argument(
        "--burn-subtitles",
        action="store_true",
        help="Quemar los subtítulos permanentemente en la imagen del video",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="Muestra el catálogo de voces neuronales disponibles y finaliza",
    )
    parser.add_argument(
        "--lang",
        choices=["es", "en", "all"],
        default="all",
        help="Filtrar catálogo de voces por idioma al usar --list-voices",
    )

    args = parser.parse_args()

    if args.list_voices:
        print_voices(args.lang)
        sys.exit(0)

    if not args.video_path:
        parser.print_help()
        print("\n[!] Error: Debes proporcionar la ruta a un archivo de video.")
        sys.exit(1)

    # Determine languages
    if args.direction == "es-en":
        source_lang = "es"
        target_lang = "en"
        default_voice = DEFAULT_VOICE_EN
    else:
        source_lang = "en"
        target_lang = "es"
        default_voice = DEFAULT_VOICE_ES

    chosen_voice = args.voice or default_voice

    config = TranslationConfig(
        voice=chosen_voice,
        whisper_model=args.model,
        translation_engine=args.engine,
        keep_background=not args.no_background,
        burn_subtitles=args.burn_subtitles,
        source_lang=source_lang,
        target_lang=target_lang,
    )

    dir_str = "Inglés ➔ Español" if args.direction == "en-es" else "Español ➔ Inglés"

    print("\n" + "=" * 60)
    print(" INICIANDO PIPELINE DE TRADUCCIÓN DE VIDEO")
    print("=" * 60)
    print(f" Dirección            : {dir_str}")
    print(f" Video de entrada     : {args.video_path}")
    print(f" Voz seleccionada     : {config.voice}")
    print(f" Modelo Whisper       : {config.whisper_model}")
    print(f" Motor de traducción  : {config.translation_engine}")
    print(f" Preservar fondo IA   : {'Sí (Demucs)' if config.keep_background else 'No (Solo voz)'}")
    print(f" Subtítulos quemados  : {'Sí (Hardcoded)' if config.burn_subtitles else 'No (Soft/Embebidos + .srt)'}")
    print("=" * 60 + "\n")

    def progress_listener(stage: str, pct: float):
        bar_len = 30
        filled = int(bar_len * pct)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\r[{bar}] {int(pct * 100):3d}% | {stage:<55}", end="", flush=True)
        if pct >= 1.0:
            print()

    pipeline = VideoTranslationPipeline(config)

    try:
        results = pipeline.run(
            video_path=args.video_path,
            output_path=args.output,
            progress_callback=progress_listener,
        )

        print("\n" + "=" * 60)
        print(" PROCESO FINALIZADO CON ÉXITO")
        print("=" * 60)
        print(f" Video final traducido : {results['output_video']}")
        print(f" Subtítulos (.srt)     : {results['subtitles_srt']}")
        print(f" Subtítulos (.vtt)     : {results['subtitles_vtt']}")
        print(f" Segmentos traducidos  : {results['segments_count']}")
        print(f" Tiempo de proceso     : {results['elapsed_seconds']} segundos")
        print("=" * 60 + "\n")

    except Exception as exc:
        print(f"\n\n[!] Error durante el procesamiento: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
