# https://github.com/Charley3d/lip-sync/blob/master/Core/phoneme_to_viseme.py
# Original Author:  Charley 3D
# He is great man.
phoneme_to_viseme_arkit_v2 = {
    # Silence
    # No required
    # "": "sil",
    # "ʔ": "sil",
    # "UNK": "sil",
    # PP – closed lips
    "m": "PP",
    "b": "PP",
    "p": "PP",
    # FF – upper teeth and lower lip
    "f": "FF",
    "v": "FF",
    # TH – tongue between teeth
    "θ": "TH",
    "ð": "TH",
    # CH – affricates
    "tʃ": "CH",
    "dʒ": "CH",
    # SS – narrow gap fricatives
    "s": "SS",
    "z": "SS",
    # SH → grouped visually into SS
    "ʃ": "SS",
    "ʒ": "SS",
    "ɕ": "SS",
    "ʑ": "SS",
    # RR – r-like sounds
    "r": "RR",
    "ɾ": "RR",
    "ʁ": "RR",
    "ʀ": "RR",
    "ɹ": "RR",
    "ɻ": "RR",
    # DD – default consonants
    "t": "DD",
    "d": "DD",
    "ʈ": "DD",
    "ɖ": "DD",
    "c": "DD",
    "ɟ": "DD",
    "x": "DD",
    "ɣ": "DD",
    "h": "DD",
    "ɦ": "DD",
    "j": "DD",
    "ç": "DD",
    "ʝ": "DD",
    # kk – velar stops
    "k": "kk",
    "g": "kk",
    # nn – nasal group + "L"
    "n": "nn",
    "ŋ": "nn",
    "ɲ": "nn",
    "ɳ": "nn",
    "l": "nn",
    "ɫ": "nn",
    # aa – open and low/mid front vowels
    "a": "aa",
    "aː": "aa",
    "ä": "aa",
    "æ": "aa",
    "ɐ": "aa",
    "ɑ": "aa",
    "ɑ̃": "aa",
    "aɪ": "aa",
    "ɛ": "aa",
    "ɛː": "aa",
    # E – mid/closed front vowels
    "e": "E",
    "eː": "E",
    "œ": "E",
    "ø": "E",
    "ə": "E",
    # ih – high front
    "i": "ih",
    "ɪ": "ih",
    "y": "ih",
    "iː": "ih",
    "ʏ": "ih",
    # oh – mid back / open-mid
    "o": "oh",
    "ɔ": "oh",
    "ɔ̃": "oh",
    "ɒ": "oh",
    "oː": "oh",
    "ʌ": "oh",
    # ou – high back rounded
    "u": "ou",
    "uː": "ou",
    "ɯ": "ou",
    "ɰ": "ou",
    "ʊ": "ou",
    "w": "ou",
}

visemes_priority = {"sil": 0, "pp": 1, "th": 2}
UNSKIPPABLE_VISEMES = ["sil", "pp", "th", "ff"]


def get_viseme_priority(viseme: str) -> int:
    """Get viseme priority. Lower number = higher priority."""
    if not viseme:
        return 999  # Lowest priority for invalid visemes

    try:
        return getattr(visemes_priority, viseme.lower(), 999)
    except (AttributeError, TypeError):
        return 999  # Default to lowest priority on any error
