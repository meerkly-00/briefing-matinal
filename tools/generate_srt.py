#!/usr/bin/env python3
"""
generate_srt.py — Generate a .srt subtitle file from a Presto XML script.

Usage:
    python tools/generate_srt.py <script.xml> <duration_seconds> <output.srt>
"""

import sys
import xml.etree.ElementTree as ET


CHAPTER_PAUSE = 0.3  # seconds between chapters
MAX_WORDS = 12       # max words per subtitle segment


def format_timestamp(seconds: float) -> str:
    """Convert seconds (float) to SRT timestamp HH:MM:SS,mmm."""
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def split_into_segments(text: str, max_words: int = MAX_WORDS) -> list[str]:
    """Split text into segments of at most max_words words."""
    words = text.split()
    segments = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        if chunk:
            segments.append(chunk)
    return segments


def word_count(text: str) -> int:
    return len(text.split())


def parse_script(xml_path: str) -> list[dict]:
    """
    Parse the XML script and return a flat list of blocks.
    Each block: {"type": "text"|"chapter_title", "text": str}
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    blocks = []

    # intro element
    intro = root.find("intro")
    if intro is not None and intro.text:
        text = intro.text.strip()
        if text:
            for seg in split_into_segments(text):
                blocks.append({"type": "text", "text": seg})

    # chapitre elements
    chapitres = root.findall("chapitre")
    for chapitre in chapitres:
        titre = chapitre.get("titre", "").strip()
        if titre:
            blocks.append({"type": "chapter_title", "text": f"── {titre} ──"})

        content = (chapitre.text or "").strip()
        if content:
            for seg in split_into_segments(content):
                blocks.append({"type": "text", "text": seg})

    return blocks


def assign_timings(blocks: list[dict], total_duration: float) -> list[dict]:
    """
    Assign start/end times to each block.

    Strategy:
    - chapter_title blocks get a fixed short duration (based on word-equivalent weight).
    - pauses (CHAPTER_PAUSE) are inserted before each chapter_title.
    - remaining time is distributed proportionally by word count among text blocks.
    """
    # Calculate total pause time consumed by chapter separators.
    num_chapters = sum(1 for b in blocks if b["type"] == "chapter_title")
    total_pause = num_chapters * CHAPTER_PAUSE

    # Assign a word-weight to chapter titles for timing purposes (display ~2s each).
    # We treat them as having a fixed duration of 2.0s.
    CHAPTER_TITLE_DURATION = 2.0
    total_chapter_title_time = num_chapters * CHAPTER_TITLE_DURATION

    available_for_text = total_duration - total_pause - total_chapter_title_time
    if available_for_text <= 0:
        available_for_text = total_duration * 0.6  # fallback

    # Count total words in text blocks.
    total_words = sum(word_count(b["text"]) for b in blocks if b["type"] == "text")
    if total_words == 0:
        total_words = 1  # avoid division by zero

    seconds_per_word = available_for_text / total_words

    # Walk through blocks and assign times.
    timed = []
    cursor = 0.0

    for block in blocks:
        if block["type"] == "chapter_title":
            # Insert pause before chapter title.
            cursor += CHAPTER_PAUSE
            start = cursor
            end = cursor + CHAPTER_TITLE_DURATION
            timed.append({**block, "start": start, "end": end})
            cursor = end
        else:
            # Text segment: duration proportional to word count.
            wc = word_count(block["text"])
            duration = wc * seconds_per_word
            start = cursor
            end = cursor + duration
            timed.append({**block, "start": start, "end": end})
            cursor = end

    # Clamp everything to total_duration.
    if cursor > total_duration:
        scale = total_duration / cursor
        for b in timed:
            b["start"] *= scale
            b["end"] *= scale

    return timed


def write_srt(timed_blocks: list[dict], output_path: str) -> None:
    lines = []
    index = 1
    for block in timed_blocks:
        start_ts = format_timestamp(block["start"])
        end_ts = format_timestamp(block["end"])
        lines.append(str(index))
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(block["text"])
        lines.append("")  # blank line between entries
        index += 1

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python tools/generate_srt.py <script.xml> <duration_seconds> <output.srt>",
            file=sys.stderr,
        )
        sys.exit(1)

    xml_path = sys.argv[1]
    try:
        duration = float(sys.argv[2])
    except ValueError:
        print(f"Error: duration_seconds must be a number, got: {sys.argv[2]}", file=sys.stderr)
        sys.exit(1)
    output_path = sys.argv[3]

    if duration <= 0:
        print(f"Error: duration_seconds must be positive, got: {duration}", file=sys.stderr)
        sys.exit(1)

    blocks = parse_script(xml_path)
    if not blocks:
        print("Error: no content found in XML script.", file=sys.stderr)
        sys.exit(1)

    timed_blocks = assign_timings(blocks, duration)
    write_srt(timed_blocks, output_path)

    print(f"Generated {len(timed_blocks)} subtitle entries -> {output_path}")


if __name__ == "__main__":
    main()
