from __future__ import annotations

import re
import unicodedata

STOPWORDS = {
    "a", "au", "aux", "avec", "ce", "ces", "dans", "de", "des", "du", "elle",
    "en", "est", "et", "il", "la", "le", "les", "leur", "mais", "ou", "par",
    "pas", "pour", "que", "qui", "sur", "un", "une", "the", "of", "and", "in",
}


def tokenize(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return [token for token in re.findall(r"[a-z0-9]+", folded) if token not in STOPWORDS]

