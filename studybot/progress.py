"""
Μνήμη προόδου: αποθηκεύει σε αρχείο JSON τα σκορ και τα σημεία όπου
ο μαθητής έκανε λάθος, ξεχωριστά για κάθε αρχείο σημειώσεων.
Έτσι το επόμενο quiz δίνει έμφαση σε ό,τι δεν ξέρει ακόμα.
"""

import json
import threading
from datetime import datetime
from pathlib import Path

PROGRESS_FILE = Path("data/progress.json")
MAX_WEAK_POINTS = 5   # πόσα αδύναμα σημεία στέλνουμε στο μοντέλο κάθε φορά

# Στο online demo πολλοί χρήστες μοιράζονται τον ίδιο server. Εκεί η πρόοδος
# κρατιέται στη μνήμη της συνεδρίας κάθε χρήστη (όχι σε κοινό αρχείο).
# Το threading.local κρατά ξεχωριστή τιμή ανά νήμα: το Streamlit τρέχει κάθε
# συνεδρία σε δικό της νήμα, οπότε οι χρήστες δεν βλέπουν ο ένας τα δεδομένα του άλλου.
_local = threading.local()


def use_memory_store(store: dict) -> None:
    """Από εδώ και πέρα (σε αυτό το νήμα) η πρόοδος γράφεται στο dict, όχι σε αρχείο."""
    _local.store = store


def _load() -> dict:
    store = getattr(_local, "store", None)
    if store is not None:
        return store
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save(data: dict) -> None:
    if getattr(_local, "store", None) is not None:
        return   # στη μνήμη οι αλλαγές έχουν ήδη γίνει πάνω στο ίδιο dict
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
