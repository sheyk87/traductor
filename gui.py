"""Tkinter Graphical User Interface for bidirectional video translation (EN <-> ES)."""

import os
import sys
import queue
import threading
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

# Bootstrap Tkinter runtime libraries
from core.gui_setup import ensure_tkinter
ensure_tkinter()

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from core.config import (
    TranslationConfig,
    SPANISH_VOICES,
    ENGLISH_VOICES,
    DEFAULT_VOICE_ES,
    DEFAULT_VOICE_EN,
    DEFAULT_WHISPER_MODEL,
    get_voices_for_lang,
    get_default_voice_for_lang,
)
from core.pipeline import VideoTranslationPipeline
from core.utils import get_media_info


class VideoTranslatorApp(tk.Tk):
    """Main Tkinter window for bidirectional video translation."""

    def __init__(self):
        super().__init__()

        self.title("Traductor de Video IA — Doblaje & Subtítulos (Inglés ⮂ Español)")
        self.geometry("960x880")
        self.minsize(880, 720)

        # Communication queue between worker thread and UI
        self.msg_queue: queue.Queue = queue.Queue()
        self.is_processing = False
        self.last_result: Optional[Dict[str, Any]] = None

        self._configure_styles()
        self._create_widgets()
        self._check_queue_loop()

    def _configure_styles(self):
        """Sets up modern ttk styling."""
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Color palette
        self.bg_main = "#f4f6f9"
        self.card_bg = "#ffffff"
        self.primary_color = "#1a73e8"
        self.success_color = "#1e8e3e"
        self.text_dark = "#202124"

        self.configure(bg=self.bg_main)

        self.style.configure(".", background=self.bg_main, foreground=self.text_dark, font=("Segoe UI", 10))
        self.style.configure("TLabelframe", background=self.card_bg, foreground=self.primary_color, relief="groove")
        self.style.configure("TLabelframe.Label", background=self.card_bg, foreground="#1967d2", font=("Segoe UI", 10, "bold"))
        self.style.configure("Card.TFrame", background=self.card_bg)

        self.style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), background=self.primary_color, foreground="#ffffff")
        self.style.map("Primary.TButton", background=[("active", "#1557b0"), ("disabled", "#dadce0")])

        self.style.configure("Secondary.TButton", font=("Segoe UI", 10))
        self.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), foreground=self.primary_color)

    def _create_widgets(self):
        """Constructs all GUI panels."""
        canvas_frame = tk.Frame(self, bg=self.bg_main)
        canvas_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(canvas_frame, bg=self.bg_main, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        self.scrollable_content = tk.Frame(canvas, bg=self.bg_main)

        self.scrollable_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw", width=930)
        canvas.configure(xscrollcommand=None, yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=(15, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

        # 1. Header
        header_frame = tk.Frame(self.scrollable_content, bg=self.bg_main)
        header_frame.pack(fill="x", pady=(0, 10))

        title_lbl = tk.Label(
            header_frame,
            text="🎬 Traductor & Doblador de Video (Inglés ⮂ Español)",
            font=("Segoe UI", 15, "bold"),
            bg=self.bg_main,
            fg="#1a237e",
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(
            header_frame,
            text="Traducción bidireccional con sincronización temporal por IA, preservación de música de fondo y subtítulos",
            font=("Segoe UI", 9),
            bg=self.bg_main,
            fg="#5f6368",
        )
        subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # 2. Files and Direction Card
        self._create_files_card(self.scrollable_content)

        # 3. Voice Settings Card
        self._create_voice_card(self.scrollable_content)

        # 4. Processing & Subtitles Options Card
        self._create_options_card(self.scrollable_content)

        # 5. Execution & Progress Card
        self._create_progress_card(self.scrollable_content)

        # 6. Live Log Area Card
        self._create_log_card(self.scrollable_content)

    def _create_files_card(self, parent):
        card = ttk.LabelFrame(parent, text=" 📁 Dirección y Archivos de Video ", padding=12)
        card.pack(fill="x", pady=6)

        # Direction Selector Row
        r_dir = tk.Frame(card, bg=self.card_bg)
        r_dir.pack(fill="x", pady=(0, 8))
        tk.Label(r_dir, text="Dirección de traducción:", width=22, anchor="w", bg=self.card_bg, font=("Segoe UI", 9, "bold")).pack(side="left")

        self.direction_combo = ttk.Combobox(
            r_dir,
            values=[
                "🇺🇸 ➔ 🇪🇸  Inglés a Español",
                "🇪🇸 ➔ 🇺🇸  Español a Inglés",
            ],
            state="readonly",
            width=32,
            font=("Segoe UI", 9, "bold"),
        )
        self.direction_combo.set("🇺🇸 ➔ 🇪🇸  Inglés a Español")
        self.direction_combo.bind("<<ComboboxSelected>>", self._on_direction_changed)
        self.direction_combo.pack(side="left", padx=6)

        sep = ttk.Separator(card, orient="horizontal")
        sep.pack(fill="x", pady=(4, 8))

        # Input Video Row
        r1 = tk.Frame(card, bg=self.card_bg)
        r1.pack(fill="x", pady=3)
        self.input_lbl = tk.Label(r1, text="Video de entrada (Inglés):", width=22, anchor="w", bg=self.card_bg, font=("Segoe UI", 9, "bold"))
        self.input_lbl.pack(side="left")
        self.input_entry = ttk.Entry(r1)
        self.input_entry.pack(side="left", fill="x", expand=True, padx=6)
        btn_browse_in = ttk.Button(r1, text="Examinar...", command=self._browse_input_video, style="Secondary.TButton")
        btn_browse_in.pack(side="right")

        # Video metadata label
        self.meta_lbl = tk.Label(card, text="Selecciona un video para inspeccionar su duración y formato.", bg=self.card_bg, fg="#70757a", font=("Segoe UI", 8))
        self.meta_lbl.pack(anchor="w", padx=(155, 0), pady=(0, 4))

        # Output Video Row
        r2 = tk.Frame(card, bg=self.card_bg)
        r2.pack(fill="x", pady=3)
        self.output_lbl = tk.Label(r2, text="Video final (Español):", width=22, anchor="w", bg=self.card_bg, font=("Segoe UI", 9, "bold"))
        self.output_lbl.pack(side="left")
        self.output_entry = ttk.Entry(r2)
        self.output_entry.pack(side="left", fill="x", expand=True, padx=6)
        btn_browse_out = ttk.Button(r2, text="Guardar como...", command=self._browse_output_video, style="Secondary.TButton")
        btn_browse_out.pack(side="right")

    def _create_voice_card(self, parent):
        card = ttk.LabelFrame(parent, text=" 🎙️ Doblaje y Síntesis de Voz (Edge-TTS) ", padding=12)
        card.pack(fill="x", pady=6)

        # Voice Selector
        r1 = tk.Frame(card, bg=self.card_bg)
        r1.pack(fill="x", pady=4)
        self.voice_label = tk.Label(r1, text="Voz en español:", width=22, anchor="w", bg=self.card_bg, font=("Segoe UI", 9, "bold"))
        self.voice_label.pack(side="left")

        self.voice_map = {}
        self.voice_combo = ttk.Combobox(r1, state="readonly", width=55)
        self._populate_voices("es")
        self.voice_combo.pack(side="left", fill="x", expand=True, padx=6)

        btn_sample = ttk.Button(r1, text="🔊 Escuchar Muestra", command=self._play_voice_sample, style="Secondary.TButton")
        btn_sample.pack(side="right")

        # Max Speed Stretch Factor
        r2 = tk.Frame(card, bg=self.card_bg)
        r2.pack(fill="x", pady=4)
        tk.Label(r2, text="Compresión de tiempo:", width=22, anchor="w", bg=self.card_bg).pack(side="left")

        self.speed_factor_var = tk.DoubleVar(value=1.45)
        speed_scale = ttk.Scale(
            r2,
            from_=1.10,
            to=1.70,
            variable=self.speed_factor_var,
            orient="horizontal",
            command=self._update_speed_lbl,
        )
        speed_scale.pack(side="left", fill="x", expand=True, padx=6)

        self.speed_val_lbl = tk.Label(r2, text="1.45x (Aceleración máx. para calzar pausas)", width=32, anchor="w", bg=self.card_bg, font=("Segoe UI", 8))
        self.speed_val_lbl.pack(side="right")

    def _populate_voices(self, target_lang: str):
        """Populates the voice combobox with voices for the given target language."""
        voices_dict = get_voices_for_lang(target_lang)
        self.voice_map = {}
        display_list = []
        for vid, vinfo in voices_dict.items():
            disp = f"{vinfo['name']} [{vinfo['gender']}] — {vinfo['description']}"
            self.voice_map[disp] = vid
            display_list.append(disp)

        self.voice_combo["values"] = display_list
        default_voice = get_default_voice_for_lang(target_lang)
        for disp, vid in self.voice_map.items():
            if vid == default_voice:
                self.voice_combo.set(disp)
                break

    def _on_direction_changed(self, event=None):
        """Handles switching between EN->ES and ES->EN."""
        is_es_to_en = "Español a Inglés" in self.direction_combo.get()
        target_lang = "en" if is_es_to_en else "es"
        source_name = "Español" if is_es_to_en else "Inglés"
        target_name = "Inglés" if is_es_to_en else "Español"

        self.input_lbl.config(text=f"Video de entrada ({source_name}):")
        self.output_lbl.config(text=f"Video final ({target_name}):")
        self.voice_label.config(text=f"Voz en {target_name.lower()}:")

        self._populate_voices(target_lang)

        # Update output path if an input video is currently selected
        in_path = self.input_entry.get().strip()
        if in_path:
            p = Path(in_path)
            stem = p.stem
            for sfx in ["_es", "_en"]:
                if stem.endswith(sfx):
                    stem = stem[:-len(sfx)]
            new_out = p.parent / f"{stem}_{target_lang}{p.suffix}"
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, str(new_out))

    def _update_speed_lbl(self, val):
        self.speed_val_lbl.config(text=f"{float(val):.2f}x (Aceleración máx. para calzar pausas)")

    def _create_options_card(self, parent):
        card = ttk.LabelFrame(parent, text=" ⚙️ Opciones de Inteligencia Artificial & Subtítulos ", padding=12)
        card.pack(fill="x", pady=6)

        # AI Models Row
        r1 = tk.Frame(card, bg=self.card_bg)
        r1.pack(fill="x", pady=3)

        tk.Label(r1, text="Modelo Whisper:", width=18, anchor="w", bg=self.card_bg).pack(side="left")
        self.whisper_combo = ttk.Combobox(
            r1,
            values=["base (Recomendado - Óptimo en CPU)", "tiny (Ultra rápido)", "small (Mayor precisión)", "medium (Alta fidelidad)"],
            state="readonly",
            width=32,
        )
        self.whisper_combo.set("base (Recomendado - Óptimo en CPU)")
        self.whisper_combo.pack(side="left", padx=4)

        tk.Label(r1, text="Traducción:", width=12, anchor="e", bg=self.card_bg).pack(side="left", padx=(10, 4))
        self.engine_combo = ttk.Combobox(
            r1,
            values=["argos (100% Offline / Local)", "google (En línea)"],
            state="readonly",
            width=28,
        )
        self.engine_combo.set("argos (100% Offline / Local)")
        self.engine_combo.pack(side="left", padx=4)

        # Checkboxes for audio and subtitles
        sep_line = ttk.Separator(card, orient="horizontal")
        sep_line.pack(fill="x", pady=8)

        r2 = tk.Frame(card, bg=self.card_bg)
        r2.pack(fill="x", pady=2)

        self.keep_bg_var = tk.BooleanVar(value=True)
        chk_bg = ttk.Checkbutton(
            r2,
            text="Preservar música y efectos de fondo (Separar voz con Demucs IA)",
            variable=self.keep_bg_var,
        )
        chk_bg.pack(side="left")

        # Ducking level
        self.ducking_var = tk.DoubleVar(value=-7.0)
        r_duck = tk.Frame(card, bg=self.card_bg)
        r_duck.pack(fill="x", pady=2)
        tk.Label(r_duck, text="  ↳ Atenuación de fondo durante voz:", bg=self.card_bg, font=("Segoe UI", 8)).pack(side="left", padx=(15, 4))
        duck_scale = ttk.Scale(r_duck, from_=-15.0, to=-2.0, variable=self.ducking_var, orient="horizontal", command=self._update_duck_lbl)
        duck_scale.pack(side="left", fill="x", expand=True, padx=6)
        self.duck_lbl = tk.Label(r_duck, text="-7.0 dB", width=8, bg=self.card_bg, font=("Segoe UI", 8))
        self.duck_lbl.pack(side="left")

        # Subtitles configuration
        r3 = tk.Frame(card, bg=self.card_bg)
        r3.pack(fill="x", pady=(6, 2))

        self.embed_subs_var = tk.BooleanVar(value=True)
        chk_embed = ttk.Checkbutton(
            r3,
            text="Incrustar subtítulos en MP4 (Soft-subs seleccionables)",
            variable=self.embed_subs_var,
        )
        chk_embed.pack(side="left", padx=(0, 20))

        self.burn_subs_var = tk.BooleanVar(value=False)
        chk_burn = ttk.Checkbutton(
            r3,
            text="Quemar subtítulos en el video (Hardcoded permanente)",
            variable=self.burn_subs_var,
        )
        chk_burn.pack(side="left")

    def _update_duck_lbl(self, val):
        self.duck_lbl.config(text=f"{float(val):.1f} dB")

    def _create_progress_card(self, parent):
        card = ttk.LabelFrame(parent, text=" 📊 Progreso y Ejecución ", padding=12)
        card.pack(fill="x", pady=6)

        status_row = tk.Frame(card, bg=self.card_bg)
        status_row.pack(fill="x", pady=2)

        self.status_lbl = tk.Label(status_row, text="Listo para iniciar.", font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg="#202124")
        self.status_lbl.pack(side="left")

        self.pct_lbl = tk.Label(status_row, text="0%", font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg=self.primary_color)
        self.pct_lbl.pack(side="right")

        self.progressbar = ttk.Progressbar(card, mode="determinate", maximum=100)
        self.progressbar.pack(fill="x", pady=(4, 10))

        btn_row = tk.Frame(card, bg=self.card_bg)
        btn_row.pack(fill="x")

        self.btn_start = tk.Button(
            btn_row,
            text="▶  INICIAR TRADUCCIÓN",
            command=self._start_translation,
            bg=self.primary_color,
            fg="#ffffff",
            activebackground="#1557b0",
            activeforeground="#ffffff",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            padx=18,
            pady=8,
            cursor="hand2",
        )
        self.btn_start.pack(side="left", padx=(0, 10))

        self.btn_open_folder = ttk.Button(btn_row, text="📁 Abrir Carpeta", command=self._open_output_folder, state="disabled")
        self.btn_open_folder.pack(side="left", padx=4)

        self.btn_play_video = ttk.Button(btn_row, text="🎬 Reproducir Video", command=self._play_output_video, state="disabled")
        self.btn_play_video.pack(side="left", padx=4)

        self.btn_view_srt = ttk.Button(btn_row, text="📄 Ver Subtítulos", command=self._open_subtitles_file, state="disabled")
        self.btn_view_srt.pack(side="left", padx=4)

    def _create_log_card(self, parent):
        card = ttk.LabelFrame(parent, text=" 📜 Registro en Vivo (Consola) ", padding=10)
        card.pack(fill="both", expand=True, pady=6)

        self.log_text = scrolledtext.ScrolledText(
            card,
            height=8,
            bg="#1e1e2e",
            fg="#cdd6f4",
            insertbackground="#ffffff",
            font=("Consolas", 9),
            relief="flat",
        )
        self.log_text.pack(fill="both", expand=True)

    def log(self, message: str):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def _browse_input_video(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar video para traducir",
            filetypes=[
                ("Videos soportados", "*.mp4 *.mkv *.avi *.mov *.webm *.flv *.m4v"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not file_path:
            return

        self.input_entry.delete(0, tk.END)
        self.input_entry.insert(0, file_path)

        p = Path(file_path)
        try:
            info = get_media_info(p)
            dur_mins = int(info["duration"] // 60)
            dur_secs = int(info["duration"] % 60)
            self.meta_lbl.config(
                text=f"✔ Duración: {dur_mins}m {dur_secs}s | Audio: {'Detectado' if info['has_audio'] else 'No detectado'}",
                fg="#137333",
            )
        except Exception:
            self.meta_lbl.config(text="✔ Archivo seleccionado correctamente.", fg="#137333")

        is_es_to_en = "Español a Inglés" in self.direction_combo.get()
        target_lang = "en" if is_es_to_en else "es"
        out_path = p.parent / f"{p.stem}_{target_lang}{p.suffix}"
        self.output_entry.delete(0, tk.END)
        self.output_entry.insert(0, str(out_path))

    def _browse_output_video(self):
        file_path = filedialog.asksaveasfilename(
            title="Guardar video traducido como",
            defaultextension=".mp4",
            filetypes=[("Video MP4", "*.mp4"), ("Video MKV", "*.mkv"), ("Todos los archivos", "*.*")],
        )
        if file_path:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, file_path)

    def _play_voice_sample(self):
        selected_disp = self.voice_combo.get()
        is_es_to_en = "Español a Inglés" in self.direction_combo.get()
        default_voice = DEFAULT_VOICE_EN if is_es_to_en else DEFAULT_VOICE_ES
        voice_id = self.voice_map.get(selected_disp, default_voice)

        sample_text = (
            "Hello, this is a demonstration of my voice for dubbing your video."
            if is_es_to_en
            else "Hola, esta es una demostración de mi voz para el doblaje de tus videos."
        )

        def worker():
            self.log(f"Generando muestra de voz para: {voice_id}...")
            import edge_tts
            import asyncio
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_mp3 = f.name

            try:
                asyncio.run(edge_tts.Communicate(sample_text, voice_id).save(tmp_mp3))
                if shutil.which("pw-play"):
                    subprocess.run(["pw-play", tmp_mp3], check=True)
                elif shutil.which("aplay"):
                    tmp_wav = tmp_mp3.replace(".mp3", ".wav")
                    subprocess.run(["ffmpeg", "-y", "-i", tmp_mp3, tmp_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(["aplay", "-q", tmp_wav], check=True)
                    if os.path.exists(tmp_wav):
                        os.unlink(tmp_wav)
                else:
                    self.log("[!] No se encontró un reproductor de audio de sistema (pw-play/aplay).")
            except Exception as e:
                self.log(f"[!] Error al reproducir muestra: {e}")
            finally:
                if os.path.exists(tmp_mp3):
                    os.unlink(tmp_mp3)

        threading.Thread(target=worker, daemon=True).start()

    def _start_translation(self):
        in_video = self.input_entry.get().strip()
        out_video = self.output_entry.get().strip()

        if not in_video or not Path(in_video).exists():
            messagebox.showerror("Error", "Por favor selecciona un archivo de video de entrada válido.")
            return

        if not out_video:
            messagebox.showerror("Error", "Por favor especifica la ruta de salida para el video traducido.")
            return

        is_es_to_en = "Español a Inglés" in self.direction_combo.get()
        source_lang = "es" if is_es_to_en else "en"
        target_lang = "en" if is_es_to_en else "es"
        default_voice = DEFAULT_VOICE_EN if is_es_to_en else DEFAULT_VOICE_ES

        selected_voice_disp = self.voice_combo.get()
        voice_id = self.voice_map.get(selected_voice_disp, default_voice)

        whisper_raw = self.whisper_combo.get().split()[0]
        engine_raw = self.engine_combo.get().split()[0]

        config = TranslationConfig(
            voice=voice_id,
            whisper_model=whisper_raw,
            translation_engine=engine_raw,
            keep_background=self.keep_bg_var.get(),
            burn_subtitles=self.burn_subs_var.get(),
            embed_subtitles=self.embed_subs_var.get(),
            bg_ducking_db=self.ducking_var.get(),
            max_speed_factor=self.speed_factor_var.get(),
            source_lang=source_lang,
            target_lang=target_lang,
        )

        self.is_processing = True
        self.btn_start.config(state="disabled", bg="#dadce0")
        self.btn_open_folder.config(state="disabled")
        self.btn_play_video.config(state="disabled")
        self.btn_view_srt.config(state="disabled")
        self.progressbar["value"] = 0
        self.pct_lbl.config(text="0%")

        dir_label = "Español ➔ Inglés" if is_es_to_en else "Inglés ➔ Español"

        self.log("\n" + "=" * 50)
        self.log(f"Iniciando proceso de traducción ({dir_label})...")
        self.log(f" • Video entrada: {Path(in_video).name}")
        self.log(f" • Voz de doblaje: {voice_id}")
        self.log(f" • Modelo Whisper: {whisper_raw}")
        self.log(f" • Preservar música: {config.keep_background}")
        self.log(f" • Quemar subtítulos: {config.burn_subtitles}")
        self.log("=" * 50)

        def worker():
            def progress_callback(stage_name: str, pct: float):
                self.msg_queue.put(("progress", stage_name, pct))

            try:
                pipeline = VideoTranslationPipeline(config)
                results = pipeline.run(
                    video_path=in_video,
                    output_path=out_video,
                    progress_callback=progress_callback,
                )
                self.msg_queue.put(("success", results))
            except Exception as exc:
                self.msg_queue.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _check_queue_loop(self):
        try:
            while not self.msg_queue.empty():
                msg_type, *args = self.msg_queue.get_nowait()

                if msg_type == "progress":
                    stage, pct = args
                    pct_int = int(pct * 100)
                    self.progressbar["value"] = pct_int
                    self.pct_lbl.config(text=f"{pct_int}%")
                    self.status_lbl.config(text=stage)
                    self.log(f"[{pct_int:2d}%] {stage}")

                elif msg_type == "success":
                    results = args[0]
                    self.last_result = results
                    self.is_processing = False
                    self.progressbar["value"] = 100
                    self.pct_lbl.config(text="100%")
                    self.status_lbl.config(text="✔ ¡Traducción finalizada con éxito!")
                    self.btn_start.config(state="normal", bg=self.primary_color)

                    self.btn_open_folder.config(state="normal")
                    self.btn_play_video.config(state="normal")
                    self.btn_view_srt.config(state="normal")

                    self.log("\n✔ PROCESO COMPLETADO EXITOSAMENTE")
                    self.log(f"Video final: {results['output_video']}")
                    self.log(f"Subtítulos: {results['subtitles_srt']}")
                    self.log(f"Segmentos traducidos: {results['segments_count']}")
                    self.log(f"Tiempo total: {results['elapsed_seconds']} s\n")

                    messagebox.showinfo(
                        "Traducción Completa",
                        f"El video se tradujo correctamente en {results['elapsed_seconds']} segundos.\n\n"
                        f"Archivo guardado en:\n{results['output_video']}",
                    )

                elif msg_type == "error":
                    err_msg = args[0]
                    self.is_processing = False
                    self.status_lbl.config(text="❌ Error durante el proceso.")
                    self.btn_start.config(state="normal", bg=self.primary_color)
                    self.log(f"\n[ERROR]: {err_msg}\n")
                    messagebox.showerror("Error en la Traducción", f"Ocurrió un error:\n\n{err_msg}")

        except Exception as e:
            print(f"Queue error: {e}")

        self.after(100, self._check_queue_loop)

    def _open_output_folder(self):
        if self.last_result and "output_video" in self.last_result:
            folder = Path(self.last_result["output_video"]).parent
            subprocess.Popen(["xdg-open", str(folder)])

    def _play_output_video(self):
        if self.last_result and "output_video" in self.last_result:
            video = self.last_result["output_video"]
            subprocess.Popen(["xdg-open", video])

    def _open_subtitles_file(self):
        if self.last_result and "subtitles_srt" in self.last_result:
            srt = self.last_result["subtitles_srt"]
            subprocess.Popen(["xdg-open", srt])


def launch_gui():
    app = VideoTranslatorApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
