"""
Study Quiz Bot: έκδοση για terminal
------------------------------------
Διαβάζει σημειώσεις (.txt, .md, .pdf, .docx), φτιάχνει quiz ή flashcards
ΜΟΝΟ από αυτή την ύλη και θυμάται πού δυσκολεύτηκες.

Παραδείγματα:
    python quiz_bot.py                                   (quiz με το δείγμα)
    python quiz_bot.py notes/biology.pdf                 (quiz από PDF)
    python quiz_bot.py notes/biology.pdf -n 10           (10 ερωτήσεις)
    python quiz_bot.py notes/biology.docx --mode cards   (flashcards)
    python quiz_bot.py notes/biology.pdf --stats         (η πρόοδός σου)
"""

import sys
import random
import argparse
from pathlib import Path

from studybot.errors import LLMError
from studybot.llm import describe
from studybot.loaders import load_notes, NotesError
from studybot.generator import generate_questions, generate_flashcards, Question, Flashcard
from studybot import progress

LETTERS = "ΑΒΓΔ"
LATIN = "ABCD"


# ---------- Βοηθητικά για την είσοδο του χρήστη ----------
def ask_answer(num_options: int) -> int:
    """Ζητά Α/Β/Γ/Δ (ή A-D, ή 1-4) μέχρι να δοθεί έγκυρη απάντηση."""
    while True:
        answer = input("Η απάντησή σου: ").strip().upper()
        if answer and answer in LETTERS[:num_options]:
            return LETTERS.index(answer)
        if answer and answer in LATIN[:num_options]:
            return LATIN.index(answer)
        if answer.isdigit() and 1 <= int(answer) <= num_options:
            return int(answer) - 1
        print("Γράψε Α, Β, Γ ή Δ (ή 1-4).")


def ask_yes_no(prompt: str) -> bool:
    while True:
        answer = input(prompt).strip().lower()
        if answer in ("ν", "ναι", "y", "yes"):
            return True
        if answer in ("ο", "οχι", "όχι", "o", "no", "n"):
            return False
        print("Γράψε ν (ναι) ή ο (όχι).")


# ---------- Quiz ----------
def run_quiz(questions: list[Question], notes_name: str) -> None:
    score, wrong, right_quotes = 0, [], []

    for i, q in enumerate(questions, start=1):
        print(f"\n--- Ερώτηση {i}/{len(questions)} ---")
        print(q.question)
        for j, option in enumerate(q.options):
            print(f"  {LETTERS[j]}) {option}")

        if ask_answer(len(q.options)) == q.correct_index:
            score += 1
            right_quotes.append(q.source_quote)
            print("✅ Σωστά!")
        else:
            print(f"❌ Λάθος. Σωστή απάντηση: {LETTERS[q.correct_index]}) {q.options[q.correct_index]}")
            print(f"💡 Εξήγηση: {q.explanation}")
            print(f"📖 Από τις σημειώσεις: «{q.source_quote}»")
            wrong.append((q.question, q.source_quote))

    print("\n==============================")
    print(f"Βαθμολογία: {score}/{len(questions)}")
    if wrong:
        print("Ξαναδιάβασε τα σημεία για:")
        for question, _ in wrong:
            print(f"  • {question}")
        print("📌 Την επόμενη φορά θα σε ξαναρωτήσω σε αυτά.")
    else:
        print("Τέλεια! Τα ξέρεις όλα 🎉")

    progress.record_session(notes_name, "quiz", score, len(questions), wrong, right_quotes)


# ---------- Flashcards ----------
def run_flashcards(cards: list[Flashcard], notes_name: str) -> None:
    random.shuffle(cards)
    known, unknown = [], []

    for i, card in enumerate(cards, start=1):
        print(f"\n--- Κάρτα {i}/{len(cards)} ---")
        print(f"❓ {card.front}")
        input("   (πάτα Enter για να δεις την απάντηση)")
        print(f"✅ {card.back}")
        print(f"📖 «{card.source_quote}»")
        (known if ask_yes_no("Το ήξερες; (ν/ο): ") else unknown).append(card)

    # οι κάρτες που δεν ήξερες ξαναέρχονται μία φορά στο τέλος
    if unknown:
        print(f"\n🔁 Ας δούμε ξανά τις {len(unknown)} κάρτες που δεν ήξερες.")
        for card in unknown:
            print(f"\n❓ {card.front}")
            input("   (Enter)")
            print(f"✅ {card.back}")

    print("\n==============================")
    print(f"Ήξερες {len(known)}/{len(cards)} κάρτες.")
    progress.record_session(
        notes_name, "flashcards", len(known), len(cards),
        wrong=[(c.front, c.source_quote) for c in unknown],
        right_quotes=[c.source_quote for c in known],
    )


# ---------- Στατιστικά ----------
def show_stats(notes_name: str) -> None:
    sessions = progress.history(notes_name)
    if not sessions:
        print("Δεν υπάρχει ακόμα ιστορικό για αυτές τις σημειώσεις.")
        return
    print(f"📊 Πρόοδος για: {notes_name}")
    for s in sessions[-10:]:
        pct = round(100 * s["score"] / s["total"]) if s["total"] else 0
        print(f"  {s['date']}  {s['mode']:<10} {s['score']}/{s['total']}  ({pct}%)")
    weak = progress.weak_points(notes_name)
    if weak:
        print("\nΣημεία για επανάληψη:")
        for w in weak:
            print(f"  • {w}")


# ---------- Κύριο πρόγραμμα ----------
def parse_args():
    parser = argparse.ArgumentParser(description="Quiz και flashcards από τις σημειώσεις σου.")
    parser.add_argument("notes", nargs="?", default="notes/sample_notes.txt",
                        help="αρχείο σημειώσεων (.txt, .md, .pdf, .docx)")
    parser.add_argument("-n", "--num", type=int, default=5, help="πόσες ερωτήσεις/κάρτες (1-20)")
    parser.add_argument("--mode", choices=["quiz", "cards"], default="quiz", help="quiz ή flashcards")
    parser.add_argument("--stats", action="store_true", help="δείξε την πρόοδό σου")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    notes_path = Path(args.notes)

    if args.stats:
        show_stats(notes_path.name)
        return

    n = max(1, min(args.num, 20))
    try:
        notes = load_notes(notes_path)
        weak = progress.weak_points(notes_path.name)

        print(f"📚 Διαβάζω τις σημειώσεις: {notes_path.name} ({len(notes):,} χαρακτήρες)")
        if weak:
            print(f"🎯 Θα δώσω έμφαση σε {len(weak)} σημεία όπου δυσκολεύτηκες.")

        if args.mode == "quiz":
            print(f"🤖 Φτιάχνω {n} ερωτήσεις με: {describe()}")
            run_quiz(generate_questions(notes, n, weak), notes_path.name)
        else:
            print(f"🤖 Φτιάχνω {n} flashcards με: {describe()}")
            run_flashcards(generate_flashcards(notes, n, weak), notes_path.name)

    except (NotesError, LLMError) as e:
        sys.exit(f"❌ {e}")
    except KeyboardInterrupt:
        sys.exit("\n👋 Τα λέμε!")


if __name__ == "__main__":
    main()
