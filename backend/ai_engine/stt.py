"""
Speech-to-text module using Groq Whisper.
Migrated from week2_multimodal/stt.py — removed hardcoded ffmpeg paths.
"""
import os
import shutil
from pydub import AudioSegment
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


def _find_ffmpeg() -> str:
    """
    Find ffmpeg binary. Checks PATH first, then common locations.
    Returns the path to ffmpeg or raises an error.
    """
    # Check if ffmpeg is in PATH
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path

    # Check common Windows locations
    common_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        os.path.expanduser(r"~\Desktop\ffmpeg\bin\ffmpeg.exe"),
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path

    raise FileNotFoundError(
        "ffmpeg not found. Install ffmpeg and add it to PATH, "
        "or set the FFMPEG_PATH environment variable."
    )


_pydub_configured = False


def _configure_pydub():
    """
    Point pydub at the right ffmpeg binary.

    Called lazily, on the first transcription rather than at import time: a
    missing ffmpeg used to raise while this module was being imported, and
    since `ai_engine.ingest` imports it at the top, that took PDF and image
    ingestion down with it instead of failing only the audio path.
    """
    global _pydub_configured
    if _pydub_configured:
        return

    ffmpeg_path = os.environ.get("FFMPEG_PATH") or _find_ffmpeg()
    ffmpeg_dir = os.path.dirname(ffmpeg_path)

    AudioSegment.converter = ffmpeg_path
    ffprobe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    ffprobe_path = os.path.join(ffmpeg_dir, ffprobe_name)
    if os.path.exists(ffprobe_path):
        AudioSegment.ffprobe = ffprobe_path

    # Ensure ffmpeg dir is in PATH
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] += os.pathsep + ffmpeg_dir

    _pydub_configured = True

# Groq's default client timeout is 10 minutes, which outlives the frontend's
# own timeout — a stalled request left the browser waiting on a call the
# server was still holding open. Capped below the client budget so a hang
# surfaces as an error the user can see.
TRANSCRIBE_TIMEOUT = float(os.getenv("GROQ_TRANSCRIBE_TIMEOUT", "600"))

# Groq rejects transcription uploads above 25MB. At the 32kbps mono we encode,
# that is roughly 1.8 hours of audio.
MAX_UPLOAD_MB = 24.0

# Initialize Groq client
_client = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=TRANSCRIBE_TIMEOUT)


def transcribe_audio(
    file_path: str,
    model: str = "whisper-large-v3-turbo",
    language: str = "tr",
) -> dict:
    """
    Transcribe an audio file to text using Groq Whisper.

    Args:
        file_path: Path to the audio file (mp3, mp4, wav, m4a)
        model: Whisper model name
        language: Language code for transcription

    Returns:
        dict with 'full_text' key containing the transcription
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    _configure_pydub()

    # Compress audio: mono, low bitrate for faster upload
    print(f"Preparing audio: {os.path.basename(file_path)}")
    try:
        audio = AudioSegment.from_file(file_path)
    except Exception as e:
        raise RuntimeError(
            f"Ses dosyası okunamadı ({os.path.basename(file_path)}). "
            f"ffmpeg kurulu ve biçim destekli olmalı. Ayrıntı: {e}"
        ) from e
    audio = audio.set_frame_rate(16000).set_channels(1)

    # Save as temporary mp3
    temp_path = file_path.rsplit(".", 1)[0] + "_temp.mp3"
    audio.export(temp_path, format="mp3", bitrate="32k")

    size_mb = os.path.getsize(temp_path) / (1024 * 1024)
    print(f"Compressed size: {size_mb:.1f}MB")

    if size_mb > MAX_UPLOAD_MB:
        os.remove(temp_path)
        raise ValueError(
            f"Ses kaydı çok uzun ({len(audio) / 60000:.0f} dakika, "
            f"sıkıştırılmış {size_mb:.0f}MB). Transkripsiyon servisi en fazla "
            f"{MAX_UPLOAD_MB:.0f}MB kabul ediyor; kaydı bölerek yükleyin."
        )

    try:
        with open(temp_path, "rb") as f:
            result = _client.audio.transcriptions.create(
                file=(os.path.basename(temp_path), f),
                model=model,
                language=language,
            )
        return {"full_text": result.text}
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
