"""
Μνήμη προόδου: αποθηκεύει σε αρχείο JSON τα σκορ και τα σημεία όπου
ο μαθητής έκανε λάθος, ξεχωριστά για κάθε αρχείο σημειώσεων.
Έτσι το επόμενο quiz δίνει έμφαση σε ό,τι δεν ξέρει ακόμα.
"""

import json
from datetime import datetime
from pathlib import Path

PROGRESS_FILE = Path("data/progress.json")
MAX_WEAK_POINTS = 5   # πόσα αδύναμα σημεία στέλνουμε στο μοντέλο κάθε φορά


def _load() -> dict:
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save(data: dict) -> None:
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _entry(data: dict, notes_name: str) -> dict:
    return data.setdefault(notes_name, {"history": [], "weak_points": {}})


def record_session(notes_name: str, mode: str, score: int, total: int,
                   wrong: list[tuple[str, str]], right_quotes: list[str]) -> None:
    """
    wrong: λίστα από (θέμα, απόσπασμα) για ό,τι απαντήθηκε λάθος
    right_quotes: αποσπάσματα που απαντήθηκαν σωστά (μειώνουν τα αδύναμα σημεία)
    """
    data = _load()
    entry = _entry(data, notes_name)
    entry["history"].append({
        "date": datetime.now().isoformat(timespec="minutes"),
        "mode": mode, "score": score, "total": total,
    })

    weak = entry["weak_points"]           # {απόσπασμα: {"topic": ..., "misses": n}}
    for topic, quote in wrong:
        item = weak.setdefault(quote, {"topic": topic, "misses": 0})
        item["misses"] += 1
    for quote in right_quotes:
        if quote in weak:
            weak[quote]["misses"] -= 1
            if weak[quote]["misses"] <= 0:
                del weak[quote]           # το έμαθε!
    _save(data)


def weak_points(notes_name: str) -> list[str]:
    """Τα σημεία με τα περισσότερα λάθη, σε μορφή κειμένου για το prompt."""
    weak = _entry(_load(), notes_name)["weak_points"]
    top = sorted(weak.items(), key=lambda kv: kv[1]["misses"], reverse=True)[:MAX_WEAK_POINTS]
    return [f"{v['topic']} (σχετικό απόσπασμα: «{quote}»)" for quote, v in top]


def history(notes_name: str) -> list[dict]:
    return _entry(_load(), notes_name)["history"]
