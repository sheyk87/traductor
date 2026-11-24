"""Video processing module: multiplexing audio, embedding soft subtitles, and burning hardcoded subtitles."""

import shutil
from pathlib import Path
from core.utils import ensure_ffmpeg, safe_run_command


class VideoProcessor:
    """Handles final video muxing and subtitle integration."""

    def __init__(self):
        self.ffmpeg_bins = ensure_ffmpeg()

    def process_video(
        self,
        original_video: Path,
        dubbed_audio: Path,
        subtitles_srt: Path,
        output_video: Path,
        burn_subtitles: bool = False,
        embed_subtitles: bool = True,
        target_lang: str = "es",
    ) -> Path:
        """Merges new dubbed audio and subtitles into the target video."""
        output_video.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_bin = self.ffmpeg_bins["ffmpeg"]

        sub_lang = "spa" if target_lang.lower().startswith("es") else "eng"
        sub_title = "Español" if target_lang.lower().startswith("es") else "English"

        if burn_subtitles:
            # Escape path for ffmpeg subtitles filter (replace \ and escape :)
            srt_str = str(subtitles_srt.resolve()).replace("\\", "/").replace(":", "\\:")
            cmd = [
                ffmpeg_bin,
                "-y",
                "-i", str(original_video),
                "-i", str(dubbed_audio),
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-vf", f"subtitles='{srt_str}'",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                str(output_video),
            ]
            desc = "Renderizado de video con subtítulos quemados (hardcoded)"
        else:
            # Stream-copy video for ultra fast remuxing and zero loss
            cmd = [
                ffmpeg_bin,
                "-y",
                "-i", str(original_video),
                "-i", str(dubbed_audio),
            ]

            if embed_subtitles and subtitles_srt.exists():
                cmd.extend(["-i", str(subtitles_srt)])
                cmd.extend(["-map", "0:v:0", "-map", "1:a:0", "-map", "2:s:0"])
                
                # Use mov_text for MP4 containers, srt for MKV
                is_mp4 = output_video.suffix.lower() in [".mp4", ".m4v", ".mov"]
                sub_codec = "mov_text" if is_mp4 else "srt"

                cmd.extend([
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-c:s", sub_codec,
                    "-metadata:s:s:0", f"language={sub_lang}",
                    "-metadata:s:s:0", f"title={sub_title}",
                    "-shortest",
                ])
            else:
                cmd.extend([
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest",
                ])

            cmd.append(str(output_video))
            desc = "Remultiplexado de video con audio doblado y subtítulos embebidos"

        safe_run_command(cmd, desc)
        return output_video
