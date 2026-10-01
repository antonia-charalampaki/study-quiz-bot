"""
Δημιουργία ερωτήσεων και flashcards από τις σημειώσεις.
Δεν ξέρει ποιο LLM απαντά: καλεί το llm.generate_structured().
"""

from pydantic import BaseModel

from . import llm
from .errors import LLMError
from .grounding import keep_grounded


# ---------- Η "μορφή" των δεδομένων που θέλουμε από το μοντέλο ----------
class Question(BaseModel):
    question: str          # η ερώτηση
    options: list[str]     # 4 πιθανές απαντήσεις
    correct_index: int     # ποια είναι η σωστή (0-3)
    explanation: str       # γιατί είναι σωστή
    source_quote: str      # αυτούσιο απόσπασμα από τις σημειώσεις


class Flashcard(BaseModel):
    front: str             # έννοια ή ερώτηση
    back: str              # σύντομη απάντηση / ορισμός
    source_quote: str      # αυτούσιο απόσπασμα από τις σημειώσεις


# ---------- Οδηγίες προς το μοντέλο (system instructions) ----------
COMMON_RULES = """
Είσαι βοηθός μελέτης για μαθητές και φοιτητές.
- Χρησιμοποιείς ΑΠΟΚΛΕΙΣΤΙΚΑ πληροφορίες από τις σημειώσεις που σου δίνονται.
- Το source_quote είναι αυτούσια φράση (αντιγραφή λέξη προς λέξη) από τις σημειώσεις
  που τεκμηριώνει την απάντηση.
- Γράφεις στη γλώσσα των σημειώσεων, με απλό και φιλικό ύφος.
- Καλύπτεις διαφορετικά σημεία της ύλης, όχι μόνο την αρχή.
"""

QUIZ_INSTRUCTION = COMMON_RULES + """
Φτιάχνεις ερωτήσεις πολλαπλής επιλογής:
- Ακριβώς 4 επιλογές, μία σωστή, σε τυχαία θέση (correct_index από 0 έως 3).
- Οι λάθος επιλογές είναι αληθοφανείς, όχι προφανώς λάθος.
- Η εξήγηση είναι 1-2 προτάσεις.
"""

FLASHCARD_INSTRUCTION = COMMON_RULES + """
Φτιάχνεις flashcards για επανάληψη:
- front: μια βασική έννοια, όρος ή σύντομη ερώτηση.
- back: σύντομη, σαφής απάντηση (έως 2 προτάσεις).
"""

EXTRA = 2   # ζητάμε λίγες παραπάνω, γιατί όσες δεν τεκμηριώνονται πετιούνται


def _focus_text(weak_points: list[str]) -> str:
    """Αν ο μαθητής έχει κάνει λάθη στο παρελθόν, ζητάμε να δοθεί έμφαση εκεί."""
    if not weak_points:
        return ""
    bullets = "\n".join(f"- {w}" for w in weak_points)
    return ("\n\nΟ μαθητής δυσκολεύτηκε στο παρελθόν στα παρακάτω σημεία. "
            "Περίπου οι μισές ερωτήσεις να τα ελέγχουν, με ΝΕΑ διατύπωση:\n" + bullets)


def _build_prompt(what: str, n: int, notes: str, weak_points) -> str:
    return (f"Φτιάξε {n} {what} από τις παρακάτω σημειώσεις."
            f"{_focus_text(weak_points or [])}\n\n<notes>\n{notes}\n</notes>")


def _finish(items: list, notes: str, n: int, on_status) -> list:
    """Κρατά μόνο όσα έχουν πραγματική παραπομπή στις σημειώσεις, έως n."""
    kept, dropped = keep_grounded(items, notes)
    if dropped:
        on_status(f"🔎 Απορρίφθηκαν {len(dropped)} χωρίς έγκυρη παραπομπή στις σημειώσεις.")
    if not kept:
        raise LLMError("Το μοντέλο δεν έδωσε κανένα αποτέλεσμα τεκμηριωμένο από τις σημειώσεις. "
                       "Ξαναδοκίμασε ή χρησιμοποίησε άλλο μοντέλο.")
    return kept[:n]


def generate_questions(notes: str, n: int, weak_points: list[str] | None = None,
                       on_status=print) -> list[Question]:
    prompt = _build_prompt("ερωτήσεις", n + EXTRA, notes, weak_points)
    questions = llm.generate_structured(QUIZ_INSTRUCTION, prompt, Question, on_status)
    # έλεγχος δομής: ακριβώς 4 επιλογές και έγκυρη σωστή απάντηση
    questions = [q for q in questions
                 if len(q.options) == 4 and 0 <= q.correct_index < 4]
    return _finish(questions, notes, n, on_status)


def generate_flashcards(notes: str, n: int, weak_points: list[str] | None = None,
                        on_status=print) -> list[Flashcard]:
    prompt = _build_prompt("flashcards", n + EXTRA, notes, weak_points)
    cards = llm.generate_structured(FLASHCARD_INSTRUCTION, prompt, Flashcard, on_status)
    return _finish(cards, notes, n, on_status)
