# Traductor y Doblador Automatizado de Videos (Inglés ⮂ Español)

Sistema local automatizado para traducir videos del **inglés al español** o del **español al inglés**, reemplazando la pista vocal original con voces neuronales de alta fidelidad, sincronizando los tiempos de habla de forma dinámica y generando subtítulos (.srt, .vtt, incrustados o quemados en el video).

---

## 🛠️ Arquitectura y Funcionamiento

El pipeline realiza el procesamiento en 7 fases coordinadas:

1. **Extracción y Validación**: Inspección segura con `ffprobe` y extracción de audio sin pérdida a 44.1 kHz PCM WAV.
2. **Separación de Pistas con IA (Demucs)**: Separa la voz del fondo musical y efectos sonoros (`htdemucs --two-stems=vocals`).
3. **Transcripción con Marcas de Tiempo (faster-whisper)**: Convierte la voz a texto en el idioma de origen con detección de actividad de voz (VAD) para evitar alucinaciones durante silencios.
4. **Traducción Bidireccional (Argos Translate / Google)**: Motor 100% local y offline para pares **EN ➔ ES** y **ES ➔ EN** con puntuación adaptada (`¿?`, `¡!` para español; puntuación estándar para inglés).
5. **Síntesis y Sincronización Temporal (Edge-TTS + atempo)**:
   - Sintetiza cada segmento con voces neuronales masculinas y femeninas acordes al idioma de destino.
   - Aplica estiramiento temporal inteligente (time-stretching con `atempo` en FFmpeg) sin distorsionar el tono para que el habla traducida coincida con la ventana de tiempo del orador original.
   - Ensambla la pista vocal sobre un lienzo temporal de milisegundos exactos para evitar cualquier desfase o acumulación de retardo.
6. **Mezcla y Ducking de Audio**: Aplica atenuación de volumen (ducking de -7 dB) a la música y efectos de fondo durante los diálogos y normaliza los picos a -1.0 dBFS.
7. **Remultiplexado y Subtitulado**:
   - Genera archivos `.srt` y `.vtt` con saltos de línea optimizados para lectura.
   - Incrusta los subtítulos como pista seleccionable en el contenedor `.mp4` (`mov_text`) con metadatos de idioma o los quema permanentemente en la imagen si se solicita con `--burn-subtitles`.

---

## 📦 Informe de Componentes Instalados

El sistema está diseñado de forma **completamente aislada** dentro de la carpeta del proyecto (`.venv/`), **sin modificar librerías del sistema ni requerir permisos de administrador (`sudo`)**:

| Componente | Paquete / Herramienta | Rol en el Sistema | Ubicación |
| :--- | :--- | :--- | :--- |
| **Transcripción (STT)** | `faster-whisper` + `av<14` | Transcripción en CPU con cuantización `int8` y VAD | `.venv/` + caché en `~/.cache/huggingface/hub/` |
| **Separación de Pistas** | `demucs` + `torch` (CPU) | Aislamiento de voz y música instrumental de fondo | `.venv/` + caché en `~/.cache/torch/hub/checkpoints/` |
| **Traducción Neuronal** | `argostranslate` + `deep-translator` | Traducción 100% offline y local (EN ⮂ ES) | `.venv/` + paquetes en `~/.local/share/argos-translate/` |
| **Doblaje (TTS)** | `edge-tts` | Síntesis de voz neural de Microsoft de alta fidelidad | `.venv/` (transmisión en tiempo de ejecución) |
| **Procesamiento de Audio** | `pydub`, `soundfile` | Ajuste de tempos (`atempo`), normalización y ducking | `.venv/` |
| **Motor Multimedia** | `static-ffmpeg` | Binarios autónomos de `ffmpeg` y `ffprobe` (v8.0) | `.venv/lib/python3.12/site-packages/static_ffmpeg/bin/` |
| **Interfaz Gráfica** | `tkinter` + `tk8.6` embebido | Ventana gráfica nativa de escritorio | `.venv/lib/` y `.venv/share/tcltk/` |

---

## 💻 Instructivo de Instalación en Otro Equipo

### En Linux (Ubuntu / Debian / Mint / Fedora)

1. **Copiar o clonar la carpeta del proyecto:**
   ```bash
   cd /ruta/a/traductor
   ```

2. **Crear el entorno virtual e instalar dependencias:**
   ```bash
   # 1. Crear el entorno virtual
   python3 -m venv .venv
   source .venv/bin/activate

   # 2. Actualizar pip e instalar requerimientos
   pip install --upgrade pip
   pip install -r requirements.txt

   # 3. Instalar PyTorch específico para CPU (ahorra gigabytes de CUDA)
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

   # 4. Asegurarse de tener soporte de interfaz gráfica en la distribución:
   sudo apt install -y python3-tk
   ```

3. **Ejecutar:**
   ```bash
   python main.py   # Inicia la interfaz gráfica
   ```

---

### En Windows (10 / 11)

1. **Instalar Python:** Descarga Python 3.10 o superior desde [python.org](https://www.python.org). Asegúrate de marcar las casillas:
   - *"Add python.exe to PATH"*
   - *"tcl/tk and IDLE"*
2. **Abrir PowerShell en la carpeta del proyecto:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
   ```
3. **Ejecutar:**
   ```powershell
   python main.py
   ```

---

## 🗑️ Instructivo de Desinstalación Completa

Dado que no se instalan servicios en el sistema ni dependencias globales, la desinstalación consiste únicamente en borrar la carpeta y las cachés locales de los modelos:

```bash
# 1. Eliminar la carpeta del proyecto y su entorno virtual
rm -rf /ruta/a/traductor

# 2. Eliminar las cachés de modelos de IA descargados
rm -rf ~/.cache/huggingface/hub/models--Systran--faster-whisper*
rm -rf ~/.cache/torch/hub/checkpoints/*demucs*
rm -rf ~/.local/share/argos-translate/
```
*(En Windows, basta con eliminar la carpeta del proyecto y vaciar las carpetas correspondientes en `%USERPROFILE%\.cache`).*

---

## 🚀 Activación Rápida (En este equipo)

Como el entorno virtual ya está completamente configurado en esta máquina:

```bash
cd /home/jovillafane/Descargas/Sistemas/traductor
source .venv/bin/activate
python main.py
```

---

## 🖥️ Interfaz Gráfica (Tkinter)

Para abrir la aplicación gráfica:

```bash
python main.py
# o también:
python gui.py
```

### Funcionalidades de la Interfaz:
- **Selector de Dirección**: Alterna fácilmente entre **🇺🇸 ➔ 🇪🇸 Inglés a Español** y **🇪🇸 ➔ 🇺🇸 Español a Inglés**.
- **Catálogo Dinámico de Voces**: Al cambiar la dirección, la lista de voces se actualiza automáticamente con voces en español o en inglés (EE.UU., Reino Unido, Australia, Canadá), con botón **"🔊 Escuchar Muestra"** para probar la voz antes de procesar el video.
- **Selector de archivos visual**: Selección del video con detección automática de duración y pistas, sugiriendo nombres de salida acordes (`_es.mp4` o `_en.mp4`).
- **Control de Compresión Temporal**: Barra deslizante para ajustar la aceleración máxima permitida para sincronizar pausas.
- **Ajustes de IA**: Selección de modelos Whisper (`tiny`, `base`, `small`, `medium`) y motor de traducción (`argos` offline o `google`).
- **Opciones de Audio & Subtítulos**: Checkboxes para separar música de fondo (Demucs) con control deslizante de atenuación (ducking en dB), incrustar subtítulos en MP4 y quemar subtítulos en video.
- **Progreso en Vivo**: Barra de progreso porcentual, estado de la fase actual y consola de registros en tiempo real.
- **Acciones post-proceso**: Botones para abrir la carpeta de destino, reproducir el video traducido y ver el archivo `.srt` generado.

---

## 📖 Modo de Uso por Consola (CLI)

### 1. Traducción estándar de Inglés a Español
```bash
python main.py video_en.mp4
```

### 2. Traducción de Español a Inglés
```bash
python main.py video_es.mp4 -d es-en
```

### 3. Traducción de Español a Inglés con voz británica y subtítulos quemados
```bash
python main.py charla.mp4 -d es-en --voice en-GB-SoniaNeural --burn-subtitles
```

### 4. Ver catálogo de voces disponibles
```bash
# Todas las voces
python main.py --list-voices

# Solo voces en inglés
python main.py --list-voices --lang en

# Solo voces en español
python main.py --list-voices --lang es
```

---

### 2. Quemar los subtítulos en la pantalla (Hardcoded)
Si deseas que los subtítulos aparezcan visibles permanentemente en el video:
```bash
python main.py /ruta/a/tu_video.mp4 --burn-subtitles
```

---

### 3. Cambiar la voz o el acento
Puedes elegir voces masculinas y femeninas de México (neutro), España, Argentina, Colombia, EE.UU., etc.:
```bash
# Voz femenina de México (cálida y neutra):
python main.py mi_video.mp4 --voice es-MX-DaliaNeural

# Voz de España:
python main.py mi_video.mp4 --voice es-ES-AlvaroNeural

# Voz femenina de España:
python main.py mi_video.mp4 --voice es-ES-ElviraNeural

# Voz de Argentina:
python main.py mi_video.mp4 --voice es-AR-TomasNeural
```

Para ver la lista completa de voces recomendadas:
```bash
python main.py --list-voices
```

---

### 4. Modo rápido sin música de fondo (`--no-background`)
Ideal para tutoriales, screencasts o clases donde solo hay una persona hablando y no hay música de fondo:
```bash
python main.py tutorial.mp4 --no-background -o tutorial_espanol.mp4
```
*(Al saltar la separación de Demucs, el procesamiento es significativamente más rápido).*

---

### 5. Ajustar la precisión del modelo Whisper
Por defecto se utiliza el modelo `base`. Para videos con acentos difíciles o terminología técnica:
```bash
python main.py conferencia.mp4 -m small
```
Modelos disponibles: `tiny`, `base`, `small`, `medium`, `large-v3`.

---

## 📁 Estructura del Código

- [main.py](file:///home/jovillafane/Descargas/Sistemas/traductor/main.py): Punto de entrada principal.
- [cli.py](file:///home/jovillafane/Descargas/Sistemas/traductor/cli.py): Interfaz por consola con barra de progreso y argumentos.
- [core/config.py](file:///home/jovillafane/Descargas/Sistemas/traductor/core/config.py): Configuración, catálogo de voces y parámetros de audio.
- [core/pipeline.py](file:///home/jovillafane/Descargas/Sistemas/traductor/core/pipeline.py): Orquestador del flujo integral.
- [core/separator.py](file:///home/jovillafane/Descargas/Sistemas/traductor/core/separator.py): Separación de voz y fondo instrumental con Demucs.
- [core/transcriber.py](file:///home/jovillafane/Descargas/Sistemas/traductor/core/transcriber.py): Transcripción Speech-to-Text con `faster-whisper` y VAD.
- [core/translator.py](file:///home/jovillafane/Descargas/Sistemas/traductor/core/translator.py): Traducción de segmentos con Argos Translate (offline) o Google.
- [core/tts_engine.py](file:///home/jovillafane/Descargas/Sistemas/traductor/core/tts_engine.py): Síntesis de voz con `edge-tts` y ajuste de tempo (`atempo`).
- [core/subtitles.py](file:///home/jovillafane/Descargas/Sistemas/traductor/core/subtitles.py): Formateador y exportador de subtítulos `.srt` y `.vtt`.
- [core/mixer.py](file:///home/jovillafane/Descargas/Sistemas/traductor/core/mixer.py): Mezcla de audio con ducking y normalización de picos.
- [core/video_processor.py](file:///home/jovillafane/Descargas/Sistemas/traductor/core/video_processor.py): Remultiplexado, subtítulos embebidos y quemados.
- [tests/create_sample_and_test.py](file:///home/jovillafane/Descargas/Sistemas/traductor/tests/create_sample_and_test.py): Prueba automatizada de extremo a extremo con video sintético.
# traductor
# traductor
