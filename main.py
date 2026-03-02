# pyright: reportAny=false, reportUnusedCallResult=false
import argparse
import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from pprint import pprint
from typing import Any, cast

import pypinyin
from phonemizer import phonemize

import phoneme_to_viseme
import pinyin_to_phoneme

SOME_ISO_639_3: list[str] = ["en", "cmn"]
frame = 30
min_gap_seconds = 0.075
max_duration_seconds = 0
silence_seconds = 0.08
min_hold_frames = (
    3  # Minimum frames a viseme must hold before changing (prevents flickering)
)


## ======= Utils =======
def remove_lang_codes(text: str) -> str:
    t = text
    for lang_code in SOME_ISO_639_3:
        t = t.replace(f"({lang_code})", "")
    return t


def calc_frame(seconds: float) -> int:
    return round(seconds * frame)


## =====================


@dataclass
class Word:
    """This means a word including start time and end time."""

    text: str
    start_time: float
    end_time: float


def get_words_data(filename: str) -> tuple[list[Word], list[str]]:
    with open(filename) as f:
        audio_data = json.load(f)

    words: list[Word] = []
    words_only_text: list[str] = []

    for segment in audio_data["segments"]:
        for word in segment["words"]:
            words_only_text.append(word["word"])
            words.append(Word(word["word"], word["start"], word["end"]))

    return (words, words_only_text)


def read_viseme_map(filename: str) -> dict[str, int]:
    with open(filename) as f:
        data = cast(dict[str, int], json.load(f))

    # Check for original phoneme/viseme keys
    original_keys = {
        "sli",
        "PP",
        "FF",
        "TH",
        "DD",
        "kk",
        "CH",
        "SS",
        "nn",
        "RR",
        "aa",
        "E",
        "ih",
        "oh",
        "ou",
    }
    # Check for Rhubarb keys
    rhubarb_keys = {"A", "B", "C", "D", "E", "F", "G", "H", "X"}

    keys = set(data.keys())
    if not (keys == original_keys or keys.issuperset(rhubarb_keys)):
        logging.warning(
            f"Viseme map in {filename} does not match expected keys for either Whisper or Rhubarb."
        )

    logging.info(f"Read viseme map file: {filename}")

    return data


def get_phonemes(words_only_text: list[str], language: str) -> list[Any]:
    """Return phoneme data per word.

    For Chinese: returns list[list[list[str]]] — per-word, per-syllable groups.
      e.g. "辛苦" -> [["ɕ","i","n"], ["k","u"]]
    For English: returns list[str] — per-word flat phoneme strings.
    """
    if language == "zh":
        phonemes_list: list[list[list[str]]] = []
        for text in words_only_text:
            pinyins = pypinyin.lazy_pinyin(
                text, style=pypinyin.Style.TONE3, neutral_tone_with_five=True
            )
            # Each pinyin syllable becomes its own group
            syllable_groups: list[list[str]] = []
            for p in pinyins:
                p_clean = "".join([c for c in p if c.isalpha()]).lower()
                if p_clean in pinyin_to_phoneme.pinyin_to_ipa_map:
                    syl_phonemes = pinyin_to_phoneme.convert_pinyin_to_phonemes(p)
                    if syl_phonemes:
                        syllable_groups.append(syl_phonemes)
                else:
                    # English fallback
                    if any(c.isalpha() for c in p):
                        eng_phonemes = phonemize(
                            p, language="en-us", backend="espeak", strip=True
                        )
                        if isinstance(eng_phonemes, str):
                            cleaned = remove_lang_codes(eng_phonemes).strip()
                            if cleaned:
                                syllable_groups.append(list(cleaned))
            phonemes_list.append(syllable_groups)

        logging.info("Get phonemes (Chinese engine).")
        return phonemes_list

    phonemes = cast(list[str], phonemize(words_only_text, language="cmn", strip=True))
    phonemes_removed_lang_codes: list[str] = list(map(remove_lang_codes, phonemes))

    logging.info("Get phonemes.")

    return phonemes_removed_lang_codes


def get_visemes(phonemes: str | list[str]) -> list[str]:
    visemes: list[str] = [
        phoneme_to_viseme.phoneme_to_viseme_arkit_v2.get(p, "UNK") for p in phonemes
    ]
    while "UNK" in visemes:
        visemes.remove("UNK")

    return visemes


def calc_frame_data(
    words: list[Word], phonemes: list[Any], viseme_map: dict[str, int], stats: bool
) -> str:
    logging.info("Calculating frame data...")

    output: dict[int, int] = {}
    vieseme_stats_data: dict[str, int] = {}

    VOWEL_VISEMES = {"aa", "E", "ih", "oh", "ou"}

    def get_viseme_weight(viseme: str) -> float:
        if viseme in VOWEL_VISEMES:
            return 2.0
        return 1.0

    def add_to_output(frame_num: int, viseme: str):
        output[frame_num] = viseme_map[viseme]
        if stats:
            vieseme_stats_data[viseme] = vieseme_stats_data.get(viseme, 0) + 1

    def pick_primary_vowel(viseme_list: list[str]) -> str:
        """If we can only show one viseme for a syllable, pick the main vowel."""
        for v in viseme_list:
            if v in VOWEL_VISEMES:
                return v
        return viseme_list[0] if viseme_list else "sli"

    def place_syllable_visemes(
        syl_visemes: list[str],
        syl_start: float,
        syl_end: float,
        cur_frame: int,
    ) -> int:
        """Place visemes for one syllable within its time window.
        Returns updated current_frame."""
        if not syl_visemes:
            return cur_frame

        syl_start_frame = calc_frame(syl_start)
        syl_end_frame = calc_frame(syl_end)

        # Ensure we start at or after current_frame
        effective_start = max(cur_frame, syl_start_frame)

        # How many frames available for this syllable?
        available_frames = syl_end_frame - effective_start

        # If we can't even fit one viseme, place only the primary vowel
        if available_frames < min_hold_frames:
            frame_idx = effective_start
            add_to_output(frame_idx, pick_primary_vowel(syl_visemes))
            return frame_idx

        # Weighted duration within this syllable
        syl_duration = syl_end - syl_start
        if syl_duration <= 0:
            return cur_frame

        total_weight = sum(get_viseme_weight(v) for v in syl_visemes)
        if total_weight == 0:
            total_weight = float(len(syl_visemes))

        local_time = 0.0
        local_frame = effective_start
        first_in_syllable = True

        for i, viseme in enumerate(syl_visemes):
            weight = get_viseme_weight(viseme)
            if i == len(syl_visemes) - 1:
                v_dur = syl_duration - local_time
            else:
                v_dur = (weight / total_weight) * syl_duration

            frame_idx = calc_frame(syl_start + local_time)

            if first_in_syllable:
                frame_idx = max(frame_idx, effective_start)
                first_in_syllable = False
            else:
                if frame_idx < local_frame + min_hold_frames:
                    frame_idx = local_frame + min_hold_frames

            # Don't exceed syllable boundary
            if frame_idx > syl_end_frame:
                break

            add_to_output(frame_idx, viseme)
            local_frame = frame_idx
            local_time += v_dur

        return local_frame

    # --- Initial silence ---
    if words and words[0].start_time > 0.01:
        add_to_output(0, "sli")

    current_frame = 0

    for index, word in enumerate(words):
        phoneme_data = phonemes[index]

        word_start_frame = calc_frame(word.start_time)

        # --- Silence for gaps ---
        if index == 0:
            if word.start_time > silence_seconds:
                sli_frame = max(
                    current_frame + min_hold_frames,
                    calc_frame(word.start_time - 0.03),
                )
                add_to_output(sli_frame, "sli")
                current_frame = sli_frame
        else:
            prev_word = words[index - 1]
            gap = word.start_time - prev_word.end_time
            if gap >= silence_seconds:
                sli_frame = calc_frame(prev_word.end_time + 0.02)
                if sli_frame < current_frame + min_hold_frames:
                    sli_frame = current_frame + min_hold_frames
                add_to_output(sli_frame, "sli")
                current_frame = sli_frame

        current_frame = max(current_frame, word_start_frame)

        duration = word.end_time - word.start_time
        if duration <= 0:
            continue

        # --- Detect grouped (Chinese) vs flat (English) ---
        is_grouped = (
            phoneme_data
            and isinstance(phoneme_data, list)
            and phoneme_data
            and isinstance(phoneme_data[0], list)
        )

        if is_grouped:
            # Chinese: phoneme_data is list[list[str]] — syllable groups
            syllable_groups: list[list[str]] = phoneme_data
            num_syls = len(syllable_groups)
            if num_syls == 0:
                continue

            syl_duration = duration / num_syls

            for syl_idx, syl_phonemes in enumerate(syllable_groups):
                syl_visemes = get_visemes(syl_phonemes)
                if not syl_visemes:
                    continue

                syl_start = word.start_time + syl_idx * syl_duration
                syl_end = syl_start + syl_duration

                current_frame = place_syllable_visemes(
                    syl_visemes, syl_start, syl_end, current_frame
                )
        else:
            # English or flat: treat entire word as one syllable
            flat_phonemes = (
                phoneme_data if isinstance(phoneme_data, (str, list)) else []
            )
            word_visemes = get_visemes(flat_phonemes)
            if not word_visemes:
                continue

            current_frame = place_syllable_visemes(
                word_visemes, word.start_time, word.end_time, current_frame
            )

    # --- Final silence ---
    if words:
        last_end_frame = calc_frame(words[-1].end_time)
        sli_frame = max(current_frame + min_hold_frames, last_end_frame + 1)
        add_to_output(sli_frame, "sli")

    # --- Post-processing: deduplicate + enforce min gap ---
    sorted_frames = sorted(output.items())
    final: list[tuple[int, int]] = []
    for frame_num, viseme_id in sorted_frames:
        if final:
            if final[-1][1] == viseme_id:
                continue
            if frame_num - final[-1][0] < min_hold_frames:
                continue
        final.append((frame_num, viseme_id))

    frame_data = "\n".join([f"{f} {v}" for f, v in final])

    logging.info("Calculate frame data.")

    if stats:
        sorted_vieseme_stats_data = sorted(
            vieseme_stats_data.items(), key=lambda x: x[1], reverse=True
        )
        pprint(sorted_vieseme_stats_data)

    return frame_data


def check_rhubarb():
    if not shutil.which("rhubarb"):
        raise FileNotFoundError(
            "Rhubarb executable not found in PATH. Please install Rhubarb Lip Sync."
        )


def run_rhubarb(audio_file: str, output_file: str):
    check_rhubarb()
    cmd = [
        "rhubarb",
        audio_file,
        "-r",
        "phonetic",
        "-f",
        "tsv",
        "--extendedShapes",
        "X",
        "-o",
        output_file,
    ]
    logging.info(f"Running Rhubarb: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Rhubarb failed: {e.stderr.decode()}")
        raise


def process_rhubarb_output(
    file_path: str,
    viseme_map: dict[str, int],
    min_gap: float = 0.05,
    max_duration: float = 0,
    frame_rate: int = 30,
) -> str:
    with open(file_path, "r") as f:
        lines = f.readlines()

    # Rhubarb tsv format:
    # <timestamp> <viseme>
    raw_events: list[tuple[float, str]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            try:
                timestamp = float(parts[0])
                viseme_char = parts[1]
                raw_events.append((timestamp, viseme_char))
            except ValueError:
                logging.warning(f"Skipping invalid line: {line}")

    if not raw_events:
        return ""

    # 1. Min Gap Filter (Anti-jitter) using time
    stack: list[tuple[float, str]] = []

    for t, viseme in raw_events:
        if not stack:
            stack.append((t, viseme))
            continue

        while stack:
            prev_t, _ = stack[-1]
            diff = t - prev_t

            if diff < min_gap:
                stack.pop()
            else:
                break

        stack.append((t, viseme))

    if stack and stack[0][0] > 0:
        stack.insert(0, (0.0, "X"))
    elif not stack:
        stack.append((0.0, "X"))

    # 2. Max Duration Filter
    final_events: list[tuple[float, str]] = []

    for i in range(len(stack)):
        curr_t, curr_vis = stack[i]
        final_events.append((curr_t, curr_vis))

        if i < len(stack) - 1:
            next_t = stack[i + 1][0]
            duration = next_t - curr_t
        else:
            continue

        if max_duration > 0 and curr_vis != "X" and duration > max_duration:
            break_t = curr_t + max_duration
            if break_t < next_t:
                final_events.append((break_t, "X"))

    # 3. Map to output frames
    output_lines: list[str] = []
    for t, vis in final_events:
        frame_num = round(t * frame_rate)

        # Mapping
        val = viseme_map.get(vis)
        if val is not None:
            output_lines.append(f"{frame_num} {val}")
        else:
            logging.warning(f"Unknown viseme char: {vis}")

    return "\n".join(output_lines)


def write_to_file(filename: str, content: str) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    logging.info("Write frame data.")


def setup_argparse():
    parser = argparse.ArgumentParser(
        description="A simple script to 2d lip sync frame data from whisper json data."
    )
    parser.add_argument(
        "--output", "-o", help="The path to the output file.", default="output.txt"
    )
    parser.add_argument("--frame", "-f", help="Frame.", default=30)
    parser.add_argument(
        "--min-gap-seconds",
        "-g",
        help="Minimum interval time between keyframes (seconds).",
        default=min_gap_seconds,
    )
    parser.add_argument(
        "--silence-seconds",
        "-s",
        help="Minimum duration of a silence keyframe",
        default=silence_seconds,
    )
    parser.add_argument(
        "--max-duration-seconds",
        help="Maximum duration of a non-silence keyframe (seconds). 0 to disable.",
        default=max_duration_seconds,
        type=float,
    )
    parser.add_argument(
        "--viseme_map",
        "-m",
        help="The path to the viseme map file.",
        default="viseme_map.json",
    )
    parser.add_argument(
        "--language",
        "-l",
        help="Language of the input audio (en, zh). Default is en.",
        default="en",
    )
    parser.add_argument("--stats", "-t", help="Print stats", action="store_true")
    parser.add_argument("input_file", help="The path to the whisper json file.")

    args = parser.parse_args()

    return args


# ======= Main ========


def main():
    args = setup_argparse()

    global frame
    global min_gap_seconds
    global silence_seconds
    global min_hold_frames
    global max_duration_seconds

    if args.input_file:
        frame = int(args.frame)
        min_gap_seconds = float(args.min_gap_seconds)
        silence_seconds = float(args.silence_seconds)
        max_duration_seconds = float(args.max_duration_seconds)

        # Update min_hold_frames based on min_gap_seconds
        min_hold_frames = max(1, round(min_gap_seconds * frame))

        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

        input_path = Path(args.input_file)
        suffix = input_path.suffix.lower()

        if suffix in [".wav", ".ogg"]:
            # Rhubarb mode
            logging.info("Detected audio file. Using Rhubarb Lip Sync.")

            map_file = args.viseme_map
            # If the user used the default map file, and it's an audio file,
            # prefer rhubarb_map.json if it exists.
            if map_file == "viseme_map.json" and Path("rhubarb_map.json").exists():
                logging.info("Using rhubarb_map.json for audio input.")
                map_file = "rhubarb_map.json"

            viseme_map = read_viseme_map(map_file)

            # Temporary output file for Rhubarb
            temp_dat = input_path.with_suffix(".tsv")
            try:
                run_rhubarb(str(input_path), str(temp_dat))
                frame_data = process_rhubarb_output(
                    str(temp_dat),
                    viseme_map,
                    min_gap=min_gap_seconds,
                    max_duration=max_duration_seconds,
                    frame_rate=frame,
                )
                write_to_file(args.output, frame_data)
            finally:
                if temp_dat.exists():
                    try:
                        temp_dat.unlink()
                    except OSError:
                        pass

        else:
            # Existing Whisper/Json mode
            viseme_map = read_viseme_map(args.viseme_map)
            words, words_only_text = get_words_data(args.input_file)
            phonemes = get_phonemes(words_only_text, args.language)
            frame_data = calc_frame_data(words, phonemes, viseme_map, args.stats)
            write_to_file(args.output, frame_data)


if __name__ == "__main__":
    main()
