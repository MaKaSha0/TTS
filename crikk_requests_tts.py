#!/usr/bin/env python3
"""Generate a Burmese MP3 using requests and Crikk's public guest TTS form.

Install:
    python -m pip install requests

List free voices shown on the Burmese page:
    python crikk_requests_tts.py --list-voices

Generate with a selected voice:
    python crikk_requests_tts.py "မင်္ဂလာပါ။" -o nilar.mp3 --voice Nilar
    python crikk_requests_tts.py "မင်္ဂလာပါ။" -o thiha.mp3 --voice Thiha
    python crikk_requests_tts.py "မင်္ဂလာပါ။" -o ava.mp3 --voice "Ava Multilingual"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

PAGE_URL = "https://crikk.com/text-to-speech/burmese"
GUEST_TTS_URL = "https://crikk.com/api/tts/guest"
# The guest page UI shows 2,500; the direct guest endpoint accepted 5,000 once.
MAX_CHARS = 5000

# Voice options listed by Crikk's public Burmese TTS page and marked isFree=1
# in that page's current voice data (checked 2026-10-06).
VOICE_IDS = {
    "Nilar": "my-MM-NilarNeural",
    "Thiha": "my-MM-ThihaNeural",
    "Florian Multilingual": "de-DE-FlorianMultilingualNeural",
    "Seraphina Multilingual": "de-DE-SeraphinaMultilingualNeural",
    "Ava Multilingual": "en-US-AvaMultilingualNeural",
    "Andrew Multilingual": "en-US-AndrewMultilingualNeural",
    "Emma Multilingual": "en-US-EmmaMultilingualNeural",
    "Brian Multilingual": "en-US-BrianMultilingualNeural",
    "Remy Multilingual": "fr-FR-RemyMultilingualNeural",
    "Vivienne Multilingual": "fr-FR-VivienneMultilingualNeural",
    "Giuseppe Multilingual": "it-IT-GiuseppeMultilingualNeural",
    "Hyunsu Multilingual": "ko-KR-HyunsuMultilingualNeural",
    "Thalita Multilingual": "pt-BR-ThalitaMultilingualNeural",
}


def generate(text: str, voice_name: str, output: Path, timeout: int = 120) -> Path:
    text = text.strip()
    if not text:
        raise ValueError("Text must not be empty")
    if len(text) > MAX_CHARS:
        raise ValueError(f"Text is {len(text)} characters; this script is capped at {MAX_CHARS} characters")
    if voice_name not in VOICE_IDS:
        raise ValueError(f"Unknown voice {voice_name!r}. Use --list-voices to see the free options.")

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CrikkGuestTTS/1.0)",
        "Origin": "https://crikk.com",
        "Referer": PAGE_URL,
        "Accept": "audio/mpeg, application/json",
    }

    with requests.Session() as session:
        # Load the public page first, as the browser does; retain ordinary guest cookies.
        page = session.get(PAGE_URL, headers={"User-Agent": headers["User-Agent"]}, timeout=30)
        page.raise_for_status()
        response = session.post(
            GUEST_TTS_URL,
            json={"text": text, "voice": VOICE_IDS[voice_name]},
            headers=headers,
            timeout=timeout,
        )

    if response.status_code != 200:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text[:500]
        raise RuntimeError(f"Crikk returned HTTP {response.status_code}: {detail}")

    content_type = response.headers.get("Content-Type", "").lower()
    if "audio/mpeg" not in content_type or not response.content:
        raise RuntimeError(
            f"Expected an MP3 response, got Content-Type={content_type!r}; body={response.text[:300]!r}"
        )

    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(response.content)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Crikk Burmese guest TTS using requests only (no Playwright/API token).")
    parser.add_argument("text", nargs="?", help="Burmese text to speak (script cap: 5,000; page UI shows 2,500)")
    parser.add_argument("-o", "--output", default="crikk_burmese.mp3", help="Output MP3 path")
    parser.add_argument("--voice", default="Nilar", choices=tuple(VOICE_IDS), help="Free voice to use (default: Nilar)")
    parser.add_argument("--timeout", type=int, default=600, help="Request timeout in seconds (default: 600)")
    parser.add_argument("--list-voices", action="store_true", help="Print all free voice choices shown on the Burmese page and exit")
    args = parser.parse_args()

    if args.list_voices:
        for name, voice_id in VOICE_IDS.items():
            print(f"{name}\t{voice_id}")
        return 0
    if not args.text:
        parser.error("text is required unless --list-voices is used")

    try:
        output = generate(args.text, args.voice, Path(args.output), args.timeout)
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        print(f"TTS failed: {exc}", file=sys.stderr)
        return 1

    print(f"Voice: {args.voice} ({VOICE_IDS[args.voice]})")
    print(f"Saved: {output}")
    print(f"Size: {output.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
