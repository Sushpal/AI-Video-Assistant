import yt_dlp
from pydub import AudioSegment
import os
import tempfile

try:
    import streamlit as st
except ImportError:
    st = None

DOWNLOAD_DIR = 'downloads'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _get_cookie_file():
    """Write YOUTUBE_COOKIES secret to a temp file if available. Returns path or None."""
    if st is None:
        return None
    try:
        cookies = st.secrets.get("YOUTUBE_COOKIES", None)
    except Exception:
        cookies = None

    if not cookies:
        return None

    # FIX: Streamlit Secrets TOML triple-quote adds leading whitespace
    # to each line — strip it so Netscape cookie format stays valid
    cleaned_lines = [line.lstrip() for line in cookies.splitlines()]
    cleaned_cookies = "\n".join(cleaned_lines)

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    tmp.write(cleaned_cookies)
    tmp.flush()
    tmp.close()
    return tmp.name


def download_youtube_audio(url: str) -> str:
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    cookie_file = _get_cookie_file()

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["ios", "web"],
            }
        },
        "restrictfilenames": True,
    }

    if cookie_file:
        ydl_opts["cookiefile"] = cookie_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base = os.path.splitext(filename)[0]
            return base + ".wav"
    finally:
        # Cleanup temp cookie file
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)


def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to WAV format using pydub."""
    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)  # 16khz
    audio.export(output_path, format="wav")
    return output_path


def chunk_audio(wav_path: str, chunk_minutes: int = 10) -> list:
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000

    chunks = []
    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start: start + chunk_ms]
        chunk_path = f"{wav_path}_chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)

    return chunks


def cleanup_file(path: str):
    """Safely delete a file — no crash if already gone."""
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"🗑️ Deleted: {path}")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")


def process_input(source: str) -> list:
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected YouTube URL. Downloading audio...")
        wav_path = download_youtube_audio(source)
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source)

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready — {len(chunks)} chunk(s) created.")

    # Cleanup original WAV immediately after chunking
    cleanup_file(wav_path)

    return chunks