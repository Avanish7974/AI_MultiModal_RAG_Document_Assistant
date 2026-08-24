from typing import Any, Dict, List
from urllib.parse import urlparse, parse_qs

import os
import tempfile

from youtube_transcript_api import YouTubeTranscriptApi


# =========================================================
# EXTRACT VIDEO ID
# =========================================================

def extract_video_id(youtube_url: str) -> str:
    """
    Extract YouTube video ID from common URL formats.

    Supported:
        https://www.youtube.com/watch?v=VIDEO_ID
        https://youtu.be/VIDEO_ID
        https://www.youtube.com/shorts/VIDEO_ID
        https://www.youtube.com/embed/VIDEO_ID
        https://www.youtube.com/live/VIDEO_ID
    """

    youtube_url = youtube_url.strip()

    parsed = urlparse(youtube_url)

    hostname = (
        parsed.hostname.lower()
        if parsed.hostname
        else ""
    )

    # -----------------------------------------------------
    # Standard YouTube URL
    # -----------------------------------------------------

    if hostname in {
        "www.youtube.com",
        "youtube.com",
        "m.youtube.com",
    }:

        query_params = parse_qs(
            parsed.query
        )

        if "v" in query_params:
            return query_params["v"][0]

        path_parts = [
            part
            for part in parsed.path.split("/")
            if part
        ]

        if len(path_parts) >= 2:

            if path_parts[0] in {
                "shorts",
                "embed",
                "live",
            }:

                return path_parts[1]

    # -----------------------------------------------------
    # Short URL
    # -----------------------------------------------------

    if hostname == "youtu.be":

        video_id = parsed.path.strip("/")

        if video_id:
            return video_id

    raise ValueError(
        "Invalid YouTube URL. "
        "Please provide a valid YouTube video link."
    )


# =========================================================
# YOUTUBE TRANSCRIPT API
# =========================================================

def _extract_transcript_from_youtube(
    video_id: str,
) -> List[Dict[str, Any]]:
    """
    Try to retrieve an existing YouTube transcript.

    Priority:

        1. English
        2. Hindi
        3. Any available transcript

    Returns timestamped segments.
    """

    api = YouTubeTranscriptApi()

    transcript_list = api.list(
        video_id
    )

    selected_transcript = None

    # -----------------------------------------------------
    # 1. ENGLISH
    # -----------------------------------------------------

    try:

        selected_transcript = (
            transcript_list
            .find_transcript(
                ["en"]
            )
        )

    except Exception:

        selected_transcript = None

    # -----------------------------------------------------
    # 2. HINDI
    # -----------------------------------------------------

    if selected_transcript is None:

        try:

            selected_transcript = (
                transcript_list
                .find_transcript(
                    ["hi"]
                )
            )

        except Exception:

            selected_transcript = None

    # -----------------------------------------------------
    # 3. ANY AVAILABLE LANGUAGE
    # -----------------------------------------------------

    if selected_transcript is None:

        available_transcripts = list(
            transcript_list
        )

        if available_transcripts:

            selected_transcript = (
                available_transcripts[0]
            )

    # -----------------------------------------------------
    # NO TRANSCRIPT
    # -----------------------------------------------------

    if selected_transcript is None:

        raise ValueError(
            "No YouTube transcript is available."
        )

    # -----------------------------------------------------
    # FETCH
    # -----------------------------------------------------

    transcript = selected_transcript.fetch()

    extracted_data = []

    for item in transcript:

        text = str(
            getattr(
                item,
                "text",
                ""
            )
        ).strip()

        if not text:
            continue

        start = float(
            getattr(
                item,
                "start",
                0
            )
        )

        duration = float(
            getattr(
                item,
                "duration",
                0
            )
        )

        extracted_data.append(
            {
                "text": text,
                "start": start,
                "duration": duration,
            }
        )

    if not extracted_data:

        raise ValueError(
            "The YouTube transcript was empty."
        )

    return extracted_data


# =========================================================
# DOWNLOAD YOUTUBE AUDIO
# =========================================================

def _download_youtube_audio(
    youtube_url: str,
    output_directory: str,
) -> str:
    """
    Download the best available audio from YouTube.

    Returns the downloaded audio file path.
    """

    try:

        import yt_dlp

    except ImportError as error:

        raise RuntimeError(
            "yt-dlp is not installed. "
            "Run: python -m pip install -U yt-dlp"
        ) from error

    output_template = os.path.join(
        output_directory,
        "youtube_audio.%(ext)s"
    )

    ydl_options = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    try:

        with yt_dlp.YoutubeDL(
            ydl_options
        ) as ydl:

            ydl.download(
                [youtube_url]
            )

    except Exception as error:

        raise RuntimeError(
            f"Could not download YouTube audio: {error}"
        ) from error

    # -----------------------------------------------------
    # FIND DOWNLOADED AUDIO
    # -----------------------------------------------------

    files = os.listdir(
        output_directory
    )

    audio_files = [
        file_name
        for file_name in files
        if file_name.startswith(
            "youtube_audio."
        )
    ]

    if not audio_files:

        raise RuntimeError(
            "YouTube audio was downloaded, "
            "but the audio file could not be found."
        )

    return os.path.join(
        output_directory,
        audio_files[0]
    )


# =========================================================
# WHISPER TRANSCRIPTION
# =========================================================

def _transcribe_with_whisper(
    audio_path: str,
) -> List[Dict[str, Any]]:
    """
    Transcribe YouTube audio using faster-whisper.

    Uses CPU + INT8 for maximum compatibility
    with the existing Windows/Python environment.

    Whisper automatically detects the spoken language.
    """

    try:

        from faster_whisper import WhisperModel

    except ImportError as error:

        raise RuntimeError(
            "faster-whisper is not installed. "
            "Run: python -m pip install -U faster-whisper"
        ) from error

    # -----------------------------------------------------
    # LOAD MODEL
    # -----------------------------------------------------

    model = WhisperModel(
        "base",
        device="cpu",
        compute_type="int8",
    )

    # -----------------------------------------------------
    # TRANSCRIBE
    # -----------------------------------------------------

    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        vad_filter=True,
    )

    extracted_data = []

    # IMPORTANT:
    # faster-whisper returns a generator.
    # Iterating over it performs the actual transcription.

    for segment in segments:

        text = str(
            segment.text
        ).strip()

        if not text:
            continue

        start = float(
            segment.start
        )

        end = float(
            segment.end
        )

        duration = max(
            0.0,
            end - start
        )

        extracted_data.append(
            {
                "text": text,
                "start": start,
                "duration": duration,
            }
        )

    if not extracted_data:

        raise ValueError(
            "Whisper could not detect any speech "
            "in the downloaded YouTube audio."
        )

    return extracted_data


# =========================================================
# WHISPER FALLBACK
# =========================================================

def _extract_transcript_with_whisper(
    youtube_url: str,
) -> List[Dict[str, Any]]:
    """
    Fallback transcription pipeline:

        YouTube URL
            ↓
        Download audio
            ↓
        faster-whisper
            ↓
        Timestamped transcript
    """

    temporary_directory = tempfile.mkdtemp(
        prefix="youtube_rag_"
    )

    try:

        print(
            "=== YOUTUBE WHISPER FALLBACK ==="
        )

        # -------------------------------------------------
        # DOWNLOAD AUDIO
        # -------------------------------------------------

        print(
            "Downloading YouTube audio..."
        )

        audio_path = _download_youtube_audio(
            youtube_url,
            temporary_directory,
        )

        print(
            f"Audio downloaded: {audio_path}"
        )

        # -------------------------------------------------
        # TRANSCRIBE
        # -------------------------------------------------

        print(
            "Transcribing with faster-whisper..."
        )

        transcript = _transcribe_with_whisper(
            audio_path
        )

        print(
            f"Whisper segments: {len(transcript)}"
        )

        return transcript

    finally:

        # -------------------------------------------------
        # CLEAN TEMPORARY FILES
        # -------------------------------------------------

        try:

            for file_name in os.listdir(
                temporary_directory
            ):

                file_path = os.path.join(
                    temporary_directory,
                    file_name,
                )

                if os.path.isfile(
                    file_path
                ):

                    os.remove(
                        file_path
                    )

            os.rmdir(
                temporary_directory
            )

        except Exception:

            pass


# =========================================================
# MAIN TRANSCRIPT FUNCTION
# =========================================================

def extract_youtube_transcript(
    youtube_url: str,
) -> List[Dict[str, Any]]:
    """
    Extract a transcript from a YouTube video.

    PRIMARY METHOD:
        YouTube Transcript API

    FALLBACK METHOD:
        Download YouTube audio with yt-dlp
        and transcribe it using faster-whisper.

    This means videos with:
        - English subtitles
        - Hindi subtitles
        - Auto-generated subtitles
        - No subtitles

    can all be processed when the audio itself
    is accessible.

    Returns:

        [
            {
                "text": "...",
                "start": 12.5,
                "duration": 4.2
            }
        ]
    """

    video_id = extract_video_id(
        youtube_url
    )

    # =====================================================
    # METHOD 1 — YOUTUBE TRANSCRIPT
    # =====================================================

    try:

        print(
            "=== TRYING YOUTUBE TRANSCRIPT ==="
        )

        transcript = (
            _extract_transcript_from_youtube(
                video_id
            )
        )

        print(
            f"YouTube transcript segments: "
            f"{len(transcript)}"
        )

        return transcript

    except Exception as transcript_error:

        print(
            "YouTube transcript unavailable."
        )

        print(
            f"Reason: {transcript_error}"
        )

    # =====================================================
    # METHOD 2 — WHISPER FALLBACK
    # =====================================================

    try:

        print(
            "=== FALLING BACK TO WHISPER ==="
        )

        transcript = (
            _extract_transcript_with_whisper(
                youtube_url
            )
        )

        print(
            f"Whisper transcript segments: "
            f"{len(transcript)}"
        )

        return transcript

    except Exception as whisper_error:

        raise RuntimeError(
            "Could not extract a transcript from "
            "this YouTube video.\n\n"
            "YouTube subtitles were unavailable and "
            "the Whisper fallback also failed.\n\n"
            f"Whisper error: {whisper_error}"
        ) from whisper_error