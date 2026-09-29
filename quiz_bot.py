"""
Study Quiz Bot - Μέρα 1
-----------------------
Διαβάζει τις σημειώσεις ενός μαθήματος, ζητά από το Gemini να φτιάξει
ερωτήσεις πολλαπλής επιλογής ΜΟΝΟ από αυτή την ύλη, εξετάζει τον μαθητή
στο terminal και εξηγεί τα λάθη με απόσπασμα από τις σημειώσεις.

Εκτέλεση:
    python quiz_bot.py                         (χρησιμοποιεί το δείγμα)
    python quiz_bot.py notes/my_notes.txt 5    (δικό σου αρχείο, 5 ερωτήσεις)
"""

import os
import sys
import json
import logging
import time
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel
from google import genai
from google.genai import types, errors


# ---------- 1. Ρυθμίσεις ----------
# κρύβουμε μια ακίνδυνη προειδοποίηση της βιβλιοθήκης για το AFC
logging.getLogger("google_genai.models").setLevel(logging.ERROR)

load_dotenv()  # διαβάζει το κρυφό αρχείο .env με το API key

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
# προαιρετικό: δεύτερο μοντέλο αν το πρώτο είναι υπερφορτωμένο
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "")
MAX_RETRIES = 3          # πόσες φορές ξαναδοκιμάζουμε αν ο server είναι φορτωμένος

DEFAULT_NOTES = Path("notes/sample_notes.txt")
DEFAULT_NUM_QUESTIONS = 5


# ---------- 2. Η "μορφή" κάθε ερώτησης ----------
# Λέμε στο Gemini ακριβώς τι πεδία θέλουμε, ώστε να μας επιστρέφει
# καθαρά δεδομένα (JSON) και όχι ελεύθερο κείμενο.
class Question(BaseModel):
    question: str          # η ερώτηση
    options: list[str]     # 4 πιθανές απαντήσεις
    correct_index: int     # ποια είναι η σωστή (0-3)
    explanation: str       # γιατί είναι σωστή
    source_quote: str      # αυτούσιο απόσπασμα από τις σημειώσεις


# ---------- 3. Οδηγίες προς το μοντέλο ----------
SYSTEM_INSTRUCTION = """
Είσαι βοηθός μελέτης για μαθητές και φοιτητές.
Φτιάχνεις ερωτήσεις πολλαπλής επιλογής ΑΠΟΚΛΕΙΣΤΙΚΑ από τις σημειώσεις
που σου δίνονται. Κανόνες:
- Μη χρησιμοποιείς γνώσεις που δεν υπάρχουν στις σημειώσεις.
- Κάθε ερώτηση έχει ακριβώς 4 επιλογές και μία σωστή.
- Οι λάθος επιλογές είναι αληθοφανείς, όχι προφανώς λάθος.
- Η εξήγηση είναι σύντομη (1-2 προτάσεις) και φιλική.
- Το source_quote είναι αυτούσια φράση από τις σημειώσεις που τεκμηριώνει
  τη σωστή απάντηση.
- Γράφεις στη γλώσσα των σημειώσεων.
"""


def load_notes(path: Path) -> str:
    """Διαβάζει το αρχείο με τις σημειώσεις."""
    if not path.exists():
        sys.exit(f"Δεν βρέθηκε το αρχείο: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if len(text) < 200:
        sys.exit("Οι σημειώσεις είναι πολύ λίγες. Βάλε τουλάχιστον μία παράγραφο.")
    return text



def call_gemini(client: genai.Client, contents: str, config: types.GenerateContentConfig):
    """
    Καλεί το Gemini με ασφάλεια:
    - αν ο server είναι φορτωμένος (503) ή ξεπεράσαμε το όριο (429),
      περιμένει και ξαναδοκιμάζει (5s, 10s, 20s)
    - αν αποτύχει ξανά και έχουμε ορίσει FALLBACK_MODEL, δοκιμάζει εκείνο
    """
    models = [MODEL] + ([FALLBACK_MODEL] if FALLBACK_MODEL else [])

    for model in models:
        wait = 5
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return client.models.generate_content(
                    model=model, contents=contents, config=config
                )
            except errors.ServerError as e:          # 5xx: πρόβλημα στον server
                reason = f"ο server είναι φορτωμένος ({e.code})"
            except errors.ClientError as e:          # 4xx: πρόβλημα στο αίτημά μας
                if e.code == 429:
                    reason = "ξεπεράστηκε το δωρεάν όριο αιτημάτων (429)"
                elif e.code == 404:
                    print(f"⚠️  Το μοντέλο {model} δεν είναι διαθέσιμο.")
                    break                            # πάμε στο επόμενο μοντέλο
                elif e.code in (400, 401, 403):
                    sys.exit(f"❌ Πρόβλημα με το API key ή το αίτημα ({e.code}): {e.message}")
                else:
                    raise
            if attempt < MAX_RETRIES:
                print(f"⏳ {reason}. Ξαναδοκιμάζω σε {wait} δευτερόλεπτα... ({attempt}/{MAX_RETRIES})")
                time.sleep(wait)
                wait *= 2
        if model != models[-1]:
            print(f"🔁 Δοκιμάζω το εφεδρικό μοντέλο {models[-1]}...")

    sys.exit("❌ Το Gemini δεν απαντά αυτή τη στιγμή. Δοκίμασε ξανά σε λίγα λεπτά.")

def generate_questions(client: genai.Client, notes: str, n: int) -> list[Question]:
    """Στέλνει τις σημειώσεις στο Gemini και παίρνει πίσω n ερωτήσεις."""
    prompt = f"Φτιάξε {n} ερωτήσεις από τις παρακάτω σημειώσεις.\n\n<notes>\n{notes}\n</notes>"

    response = call_gemini(
        client,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.4,                      # λίγη ποικιλία, αλλά όχι "φαντασία"
            response_mime_type="application/json",
            response_schema=list[Question],       # επιβάλλει τη μορφή της κλάσης Question
            # δεν χρησιμοποιούμε εργαλεία, οπότε κλείνουμε το AFC (και την προειδοποίησή του)
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )

    if response.parsed:
        return response.parsed
    # εφεδρικά: αν για κάποιο λόγο δεν έγινε αυτόματα η μετατροπή
    return [Question(**q) for q in json.loads(response.text)]


def ask_answer(num_options: int) -> int:
    """Ζητά από τον χρήστη Α/Β/Γ/Δ (ή 1-4) μέχρι να δώσει έγκυρη απάντηση."""
    letters = "ΑΒΓΔ"
    while True:
        answer = input("Η απάντησή σου: ").strip().upper()
        if answer and answer in letters[:num_options]:
            return letters.index(answer)
        if answer and answer in "ABCD"[:num_options]:   # λατινικά γράμματα
            return "ABCD".index(answer)
        if answer.isdigit() and 1 <= int(answer) <= num_options:
            return int(answer) - 1
        print("Γράψε Α, Β, Γ ή Δ (ή 1-4).")


def run_quiz(questions: list[Question]) -> None:
    """Εξετάζει τον μαθητή και εξηγεί τα λάθη."""
    letters = "ΑΒΓΔ"
    score = 0
    mistakes = []

    for i, q in enumerate(questions, start=1):
        print(f"\n--- Ερώτηση {i}/{len(questions)} ---")
        print(q.question)
        for j, option in enumerate(q.options):
            print(f"  {letters[j]}) {option}")

        chosen = ask_answer(len(q.options))

        if chosen == q.correct_index:
            score += 1
            print("✅ Σωστά!")
        else:
            correct = q.options[q.correct_index]
            print(f"❌ Λάθος. Η σωστή απάντηση είναι: {letters[q.correct_index]}) {correct}")
            print(f"💡 Εξήγηση: {q.explanation}")
            print(f"📖 Από τις σημειώσεις: «{q.source_quote}»")
            mistakes.append(q.question)

    # ---------- Τελικό αποτέλεσμα ----------
    print("\n==============================")
    print(f"Βαθμολογία: {score}/{len(questions)}")
    if mistakes:
        print("Ξαναδιάβασε τα σημεία για:")
        for m in mistakes:
            print(f"  • {m}")
    else:
        print("Τέλεια! Τα ξέρεις όλα 🎉")


def main() -> None:
    if not API_KEY:
        sys.exit("Λείπει το GEMINI_API_KEY. Φτιάξε αρχείο .env (δες το .env.example).")

    notes_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_NOTES
    n = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_NUM_QUESTIONS

    notes = load_notes(notes_path)
    client = genai.Client(api_key=API_KEY)

    print(f"📚 Διαβάζω τις σημειώσεις: {notes_path.name}")
    print(f"🤖 Φτιάχνω {n} ερωτήσεις με το {MODEL}...")
    questions = generate_questions(client, notes, n)
    run_quiz(questions)


if __name__ == "__main__":
    main()
