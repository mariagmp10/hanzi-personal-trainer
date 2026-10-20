import unicodedata


def pinyin_plain(pinyin: str) -> str:
    """Quita los tonos (diacríticos) del pinyin para poder comparar por
    pronunciación sin importar el tono: "nǐ hǎo" -> "ni hao"."""
    decomposed = unicodedata.normalize("NFKD", pinyin)
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return without_marks.lower().strip()
