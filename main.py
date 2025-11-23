# pyright: reportAny=false, reportUnusedCallResult=false
import argparse
import json
import logging
import math
from dataclasses import dataclass
from typing import cast

from phonemizer import phonemize

import phoneme_to_viseme

SOME_ISO_639_3: list[str] = ["en", "cmn"]
frame = 30
min_gap_seconds = 0.18
silence_seconds = 0.22


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


def get_words_data() -> tuple[list[Word], list[str]]:
    with open("audio.json") as f:
        audio_data = json.load(f)  # pyright: ignore[reportAny]

    words: list[Word] = []
    words_only_text: list[str] = []

    for segment in audio_data["segments"]:  # pyright: ignore[reportAny]
        for word in segment["words"]:  # pyright: ignore[reportAny]
            words_only_text.append(word["word"])
            words.append(Word(word["word"], word["start"], word["end"]))

    return (words, words_only_text)


def read_viseme_map(filename: str) -> dict[str, int]:
    with open(filename) as f:
        data = cast(dict[str, int], json.load(f))

    if set(data) != {
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
    }:
        raise Exception(f"A wrong in {filename}")

    logging.info("Read viseme map file.")

    return data


def get_phonemes(words_only_text: list[str]) -> list[str]:
    phonemes = cast(list[str], phonemize(words_only_text, language="cmn", strip=True))
    phonemes_removed_lang_codes: list[str] = list(map(remove_lang_codes, phonemes))

    logging.info("Get phonemes.")

    return phonemes_removed_lang_codes


def get_visemes(phonemes: str) -> list[str]:
    visemes: list[str] = [
        phoneme_to_viseme.phoneme_to_viseme_arkit_v2.get(p, "UNK") for p in phonemes
    ]
    while "UNK" in visemes:
        visemes.remove("UNK")

    return visemes


def calc_frame_data(
    words: list[Word], phonemes: list[str], viseme_map: dict[str, int]
) -> str:
    logging.info("Calculating frame data...")

    output: dict[int, int] = {}

    for index, word in enumerate(words):
        phoneme = phonemes[index]
        visemes = get_visemes(phoneme)
        visemes_no_sli = visemes[:]

        # Give a slience
        if (
            index != len(words) - 1
            and words[index + 1].start_time - silence_seconds >= word.end_time
        ):
            visemes.append("sli")

        visemes_num = len(visemes_no_sli)
        duration = word.end_time - word.start_time

        if duration <= 0:
            continue

        if duration >= visemes_num * min_gap_seconds:
            now_gap_seconds = duration / visemes_num
            gap_frame = calc_frame(now_gap_seconds)
            current_frame = calc_frame(word.start_time)
            for viseme in visemes_no_sli:
                output.setdefault(current_frame, viseme_map[viseme])
                current_frame += gap_frame

        else:
            duration_count = 0
            current_frame = calc_frame(word.start_time)
            gap_frame = calc_frame(min_gap_seconds)
            radio = visemes_num * min_gap_seconds / duration
            if radio > 2:
                radio_floored = math.floor(radio)
                for i in range(0, visemes_num, radio_floored):
                    output.setdefault(current_frame, viseme_map[visemes_no_sli[i]])
                    current_frame += gap_frame
            else:
                for viseme in visemes:
                    if duration_count > duration:
                        break

                    output.setdefault(current_frame, viseme_map[viseme])
                    duration_count += min_gap_seconds
                    current_frame += gap_frame

        if visemes[-1] == "sli":
            output[current_frame] = viseme_map["sli"]

    frame_data = "\n".join([f"{frame} {viseme}" for frame, viseme in output.items()])

    logging.info("Calculate frame data.")

    return frame_data


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
        "--viseme_map",
        "-m",
        help="The path to the viseme map file.",
        default="viseme_map.json",
    )
    parser.add_argument("input_file", help="The path to the whisper json file.")

    args = parser.parse_args()

    return args


# ======= Main ========


def main():
    args = setup_argparse()

    global frame
    global min_gap_seconds
    global silence_seconds

    if args.input_file:
        frame = int(args.frame)
        min_gap_seconds = float(args.min_gap_seconds)
        silence_seconds = float(args.silence_seconds)

        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

        viseme_map = read_viseme_map(args.viseme_map)
        words, words_only_text = get_words_data()
        phonemes = get_phonemes(words_only_text)
        frame_data = calc_frame_data(words, phonemes, viseme_map)
        write_to_file("output.txt", frame_data)


if __name__ == "__main__":
    main()
