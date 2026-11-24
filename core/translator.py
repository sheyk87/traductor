"""Translation engine supporting Argos Translate (100% offline) and Google Translator for EN<->ES."""

import time
from typing import List, Dict, Any


class Translator:
    """Translates text segments between English and Spanish."""

    def __init__(self, engine: str = "argos", source_lang: str = "en", target_lang: str = "es"):
        self.engine = engine.lower()
        self.source_lang = source_lang.lower()
        self.target_lang = target_lang.lower()
        self._argos_model = None

    def _init_argos(self):
        if self._argos_model is not None:
            return

        import argostranslate.package
        import argostranslate.translate

        # Check if source->target is installed
        installed_langs = argostranslate.translate.get_installed_languages()
        source_found = next((l for l in installed_langs if l.code == self.source_lang), None)
        target_found = next((l for l in installed_langs if l.code == self.target_lang), None)

        translation = None
        if source_found and target_found:
            translation = source_found.get_translation(target_found)

        if translation is None:
            # Install package from index
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()
            pkg = next(
                (p for p in available_packages if p.from_code == self.source_lang and p.to_code == self.target_lang),
                None,
            )
            if pkg is None:
                raise RuntimeError(
                    f"No se encontró el paquete de traducción Argos de {self.source_lang} a {self.target_lang}."
                )
            argostranslate.package.install_from_path(pkg.download())

            # Re-fetch languages
            installed_langs = argostranslate.translate.get_installed_languages()
            source_found = next((l for l in installed_langs if l.code == self.source_lang), None)
            target_found = next((l for l in installed_langs if l.code == self.target_lang), None)
            translation = source_found.get_translation(target_found)

        self._argos_model = translation

    def translate_text(self, text: str) -> str:
        """Translates a single string."""
        clean_text = text.strip()
        if not clean_text:
            return ""

        if self.engine == "argos":
            self._init_argos()
            return self._argos_model.translate(clean_text)

        elif self.engine == "google":
            from deep_translator import GoogleTranslator
            for attempt in range(3):
                try:
                    return GoogleTranslator(source=self.source_lang, target=self.target_lang).translate(clean_text)
                except Exception:
                    time.sleep(1.0 + attempt)
            # Fallback to argos if google fails
            self._init_argos()
            return self._argos_model.translate(clean_text)

        else:
            raise ValueError(f"Motor de traducción no soportado: {self.engine}")

    def translate_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Translates a list of transcription segments and preserves timestamp structure."""
        translated_segments = []

        for seg in segments:
            original = seg.get("text", "").strip()
            translated = self.translate_text(original).strip()

            if self.target_lang == "es":
                # Spanish punctuation formatting
                if original.endswith("?") and not translated.startswith("¿"):
                    translated = "¿" + translated
                if original.endswith("!") and not translated.startswith("¡"):
                    translated = "¡" + translated
                text_en = original
                text_es = translated
            else:
                # English punctuation formatting: remove inverted marks if any
                translated = translated.lstrip("¿¡").strip()
                text_en = translated
                text_es = original

            translated_segments.append({
                "id": seg["id"],
                "start": seg["start"],
                "end": seg["end"],
                "text_source": original,
                "text_target": translated,
                "text_en": text_en,
                "text_es": text_es,
            })

        return translated_segments
