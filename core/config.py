"""Configuration settings and constants for the video translation pipeline."""

from dataclasses import dataclass
from typing import Dict

# Curated list of high-quality neural voices from Microsoft Edge TTS in Spanish
SPANISH_VOICES: Dict[str, Dict[str, str]] = {
    "es-MX-JorgeNeural": {
        "name": "Jorge (México)",
        "gender": "Masculino",
        "description": "Español latino neutro, tono claro y profesional",
    },
    "es-MX-DaliaNeural": {
        "name": "Dalia (México)",
        "gender": "Femenino",
        "description": "Español latino neutro, tono cálido y natural",
    },
    "es-ES-AlvaroNeural": {
        "name": "Álvaro (España)",
        "gender": "Masculino",
        "description": "Español castellano, tono firme y profesional",
    },
    "es-ES-ElviraNeural": {
        "name": "Elvira (España)",
        "gender": "Femenino",
        "description": "Español castellano, tono dinámico y expresivo",
    },
    "es-AR-TomasNeural": {
        "name": "Tomás (Argentina)",
        "gender": "Masculino",
        "description": "Acento rioplatense, tono casual y conversacional",
    },
    "es-AR-ElenaNeural": {
        "name": "Elena (Argentina)",
        "gender": "Femenino",
        "description": "Acento rioplatense, tono agradable",
    },
    "es-CO-GonzaloNeural": {
        "name": "Gonzalo (Colombia)",
        "gender": "Masculino",
        "description": "Español colombiano, cadencia neutra y clara",
    },
    "es-CO-SalomeNeural": {
        "name": "Salomé (Colombia)",
        "gender": "Femenino",
        "description": "Español colombiano, tono cálido",
    },
    "es-US-AlonsoNeural": {
        "name": "Alonso (EE.UU. Latino)",
        "gender": "Masculino",
        "description": "Español neutro moderno para tecnología",
    },
    "es-US-PalomaNeural": {
        "name": "Paloma (EE.UU. Latina)",
        "gender": "Femenino",
        "description": "Español neutro moderno, ideal para explicaciones",
    },
}

# Curated list of high-quality neural voices in English
ENGLISH_VOICES: Dict[str, Dict[str, str]] = {
    "en-US-GuyNeural": {
        "name": "Guy (EE.UU.)",
        "gender": "Masculino",
        "description": "American English, natural, conversational and engaging",
    },
    "en-US-JennyNeural": {
        "name": "Jenny (EE.UU.)",
        "gender": "Femenino",
        "description": "American English, clear, professional and friendly",
    },
    "en-US-AriaNeural": {
        "name": "Aria (EE.UU.)",
        "gender": "Femenino",
        "description": "American English, expressive and confident narrator",
    },
    "en-US-ChristopherNeural": {
        "name": "Christopher (EE.UU.)",
        "gender": "Masculino",
        "description": "American English, authoritative, corporate and documentary",
    },
    "en-GB-RyanNeural": {
        "name": "Ryan (Reino Unido)",
        "gender": "Masculino",
        "description": "British English, clear, friendly and modern",
    },
    "en-GB-SoniaNeural": {
        "name": "Sonia (Reino Unido)",
        "gender": "Femenino",
        "description": "British English, warm, articulate and elegant",
    },
    "en-AU-WilliamNeural": {
        "name": "William (Australia)",
        "gender": "Masculino",
        "description": "Australian English, friendly and upbeat",
    },
    "en-CA-LiamNeural": {
        "name": "Liam (Canadá)",
        "gender": "Masculino",
        "description": "Canadian English, clean and balanced",
    },
}

# Backward compatibility alias
DEFAULT_VOICES = SPANISH_VOICES

DEFAULT_VOICE_ES = "es-MX-JorgeNeural"
DEFAULT_VOICE_EN = "en-US-GuyNeural"
DEFAULT_VOICE = DEFAULT_VOICE_ES

DEFAULT_WHISPER_MODEL = "base"
DEFAULT_TRANSLATION_ENGINE = "argos"


def get_voices_for_lang(lang_code: str) -> Dict[str, Dict[str, str]]:
    """Returns curated voices for the target language ('es' or 'en')."""
    return SPANISH_VOICES if lang_code.lower().startswith("es") else ENGLISH_VOICES


def get_default_voice_for_lang(lang_code: str) -> str:
    """Returns the default voice for the target language."""
    return DEFAULT_VOICE_ES if lang_code.lower().startswith("es") else DEFAULT_VOICE_EN


@dataclass
class TranslationConfig:
    voice: str = DEFAULT_VOICE_ES
    whisper_model: str = DEFAULT_WHISPER_MODEL
    translation_engine: str = DEFAULT_TRANSLATION_ENGINE
    keep_background: bool = True
    burn_subtitles: bool = False
    embed_subtitles: bool = True
    export_srt: bool = True
    export_vtt: bool = True
    bg_ducking_db: float = -7.0
    bg_quiet_db: float = -3.0
    max_speed_factor: float = 1.45
    target_sample_rate: int = 44100
    source_lang: str = "en"
    target_lang: str = "es"

    def __post_init__(self):
        # Auto-align voice if it doesn't match the target language
        if self.target_lang == "en" and self.voice.startswith("es-"):
            self.voice = DEFAULT_VOICE_EN
        elif self.target_lang == "es" and self.voice.startswith("en-"):
            self.voice = DEFAULT_VOICE_ES
