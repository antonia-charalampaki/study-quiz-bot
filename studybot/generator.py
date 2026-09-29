"""
Δημιουργία ερωτήσεων και flashcards από τις σημειώσεις, με το Gemini.
"""

import json

from pydantic import BaseModel
from google import genai
from google.genai import types

from .gemini_client import call_gemini


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


# ---------- Οδηγίες προς το μοντέλο ----------
COMMON_RULES = """
Είσαι βοηθός μελέτης για μαθητές και φοιτητές.
- Χρησιμοποιείς ΑΠΟΚΛΕΙΣΤΙΚΑ πληροφορίες από τις σημειώσεις που σου δίνονται.
- Το source_quote είναι αυτούσια φράση από τις σημειώσεις που τεκμηριώνει την απάντηση.
- Γράφεις στη γλώσσα των σημειώσεων, με απλό και φιλικό ύφος.
- Καλύπτεις διαφορετικά σημεία της ύλης, όχι μόνο την αρχή.
"""

QUIZ_INSTRUCTION = COMMON_RULES + """
Φτιάχνεις ερωτήσεις πολλαπλής επιλογής:
- Ακριβώς 4 επιλογές, μία σωστή, σε τυχαία θέση.
- Οι λάθος επιλογές είναι αληθοφανείς, όχι προφανώς λάθος.
- Η εξήγηση είναι 1-2 προτάσεις.
"""

FLASHCARD_INSTRUCTION = COMMON_RULES + """
Φτιάχνεις flashcards για επανάληψη:
- front: μια βασική έννοια, όρος ή σύντομη ερώτηση.
- back: σύντομη, σαφής απάντηση (έως 2 προτάσεις).
"""


def _focus_text(weak_points: list[str]) -> str:
    """Αν ο μαθητής έχει κάνει λάθη στο παρελθόν, ζητάμε να δοθεί έμφαση εκεί."""
    if not weak_points:
        return ""
    bullets = "\n".join(f"- {w}" for w in weak_points)
    return (
        "\n\nΟ μαθητής δυσκολεύτηκε στο παρελθόν στα παρακάτω σημεία. "
        "Περίπου οι μισές ερωτήσεις να τα ελέγχουν, με ΝΕΑ διατύπωση:\n" + bullets
    )


def _generate(client, instruction: str, prompt: str, schema, on_status):
    response = call_gemini(
        client,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=instruction,
            temperature=0.4,
            response_mime_type="application/json",
            response_schema=list[schema],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
        on_status=on_status,
    )
    if response.parsed:
        return response.parsed
    return [schema(**item) for item in json.loads(response.text)]


def generate_questions(client: genai.Client, notes: str, n: int,
                       weak_points: list[str] | None = None, on_status=print) -> list[Question]:
    prompt = (f"Φτιάξε {n} ερωτήσεις από τις παρακάτω σημειώσεις."
              f"{_focus_text(weak_points or [])}\n\n<notes>\n{notes}\n</notes>")
    questions = _generate(client, QUIZ_INSTRUCTION, prompt, Question, on_status)
    # ασφάλεια: κρατάμε μόνο ερωτήσεις με έγκυρη σωστή απάντηση
    return [q for q in questions if 0 <= q.correct_index < len(q.options)]


def generate_flashcards(client: genai.Client, notes: str, n: int,
                        weak_points: list[str] | None = None, on_status=print) -> list[Flashcard]:
    prompt = (f"Φτιάξε {n} flashcards από τις παρακάτω σημειώσεις."
              f"{_focus_text(weak_points or [])}\n\n<notes>\n{notes}\n</notes>")
    return _generate(client, FLASHCARD_INSTRUCTION, prompt, Flashcard, on_status)
