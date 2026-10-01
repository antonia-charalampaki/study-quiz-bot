"""
Έλεγχος τεκμηρίωσης (grounding check).

Το μοντέλο υπόσχεται ότι κάθε source_quote είναι αυτούσια φράση από τις
σημειώσεις. Εδώ το ΕΛΕΓΧΟΥΜΕ με κώδικα, αντί να το εμπιστευτούμε τυφλά:
αν το απόσπασμα δεν βρεθεί στο κείμενο, η ερώτηση απορρίπτεται.
"""

import re
import unicodedata
from difflib import SequenceMatcher

MIN_MATCH = 0.85   # πόσο από το απόσπασμα πρέπει να βρεθεί αυτούσιο (85%)


def normalize(text: str) -> str:
    """Πεζά, χωρίς τόνους και σημεία στίξης, με απλά κενά.
    Έτσι το «Η Φωτοσύνθεση,» ταιριάζει με το «η φωτοσυνθεση»."""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")  # αφαιρεί τόνους
    text = re.sub(r"[^\w]+", " ", text)
    return " ".join(text.split())


def quote_score(quote: str, normalized_notes: str) -> float:
    """0 έως 1: πόσο από το απόσπασμα υπάρχει αυτούσιο μέσα στις σημειώσεις."""
    q = normalize(quote)
    if not q:
        return 0.0
    if q in normalized_notes:
        return 1.0
    # αλλιώς: το μεγαλύτερο κοινό κομμάτι (μικρές διαφορές π.χ. αλλαγή γραμμής στο PDF)
    matcher = SequenceMatcher(None, q, normalized_notes, autojunk=False)
    match = matcher.find_longest_match(0, len(q), 0, len(normalized_notes))
    return match.size / len(q)


def keep_grounded(items: list, notes: str) -> tuple[list, list]:
    """Χωρίζει τα αποτελέσματα σε (τεκμηριωμένα, απορριφθέντα)."""
    norm_notes = normalize(notes)
    kept, dropped = [], []
    for item in items:
        (kept if quote_score(item.source_quote, norm_notes) >= MIN_MATCH else dropped).append(item)
    return kept, dropped
