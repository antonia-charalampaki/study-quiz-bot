"""
Study Quiz Bot: web εφαρμογή (Streamlit)
-----------------------------------------
Εκτέλεση:  streamlit run app.py

Χρησιμοποιεί τα ίδια modules με την έκδοση terminal (studybot/),
οπότε εδώ υπάρχει μόνο το κομμάτι της διεπαφής.
"""

import os
import random

import streamlit as st

# ---------- Κλειδί API ----------
# Τοπικά διαβάζεται από το .env. Όταν η εφαρμογή τρέχει online (Streamlit Cloud),
# το κλειδί μπαίνει στα "Secrets" της πλατφόρμας και το περνάμε εδώ στο περιβάλλον.
# Πρέπει να γίνει ΠΡΙΝ φορτωθεί το studybot (διαβάζει τις ρυθμίσεις κατά τη φόρτωση).
try:
    for key in ("GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_FALLBACK_MODEL", "LLM_PROVIDER",
                "OLLAMA_MODEL", "OLLAMA_URL", "STUDYBOT_STORAGE", "APP_PASSWORD"):
        if key in st.secrets and not os.getenv(key):
            os.environ[key] = str(st.secrets[key])
except Exception:
    pass  # δεν υπάρχουν secrets τοπικά, κανένα πρόβλημα

import altair as alt
import pandas as pd

from studybot.errors import LLMError
from studybot.llm import describe
from studybot.loaders import extract_text, NotesError, SUPPORTED
from studybot.generator import generate_questions, generate_flashcards
from studybot import progress

LETTERS = "ΑΒΓΔ"

st.set_page_config(page_title="Study Quiz Bot", page_icon="📚", layout="centered")

# Στο online demo (STUDYBOT_STORAGE=session) η πρόοδος μένει στη συνεδρία κάθε επισκέπτη
if os.getenv("STUDYBOT_STORAGE", "file") == "session":
    progress.use_memory_store(st.session_state.setdefault("progress_db", {}))


# ---------- Βοηθητικά ----------
@st.cache_data(show_spinner=False)
def read_file(name: str, data: bytes) -> str:
    """Κρατάμε στη μνήμη το κείμενο, για να μη διαβάζεται ξανά σε κάθε κλικ."""
    return extract_text(name, data)


def reset_session() -> None:
    """Καθαρίζει το τρέχον quiz / flashcards."""
    for key in ("questions", "submitted", "answers", "last_score", "cards","card_idx", "show_back", "known", "unknown",
                "cards_done"):
        st.session_state.pop(key, None)
    for key in list(st.session_state.keys()):
        if key.startswith("q_"):
            del st.session_state[key]


def generate(kind: str, notes: str, notes_name: str, n: int) -> None:
    """Καλεί το Gemini και αποθηκεύει το αποτέλεσμα στο session_state."""
    reset_session()
    weak = progress.weak_points(notes_name)
    label = "ερωτήσεις" if kind == "quiz" else "flashcards"
    try:
        with st.status(f"🤖 Φτιάχνω {n} {label}...", expanded=False) as status:
            if weak:
                status.write(f"🎯 Δίνω έμφαση σε {len(weak)} σημεία όπου δυσκολεύτηκες.")
            if kind == "quiz":
                st.session_state.questions = generate_questions(
                    notes, n, weak, on_status=status.write)
                st.session_state.submitted = False
            else:
                cards = generate_flashcards(notes, n, weak, on_status=status.write)
                random.shuffle(cards)
                st.session_state.update(cards=cards, card_idx=0, show_back=False,
                                        known=[], unknown=[], cards_done=False)
            status.update(label=f"✅ Έτοιμα τα {label}!", state="complete")
    except LLMError as e:
        status.update(label="Δεν ήταν δυνατή η δημιουργία", state="error")
        st.error(f"❌ {e}")


# ---------- Quiz ----------
def show_quiz(notes_name: str) -> None:
    questions = st.session_state.questions

    # ---- Βήμα 1: ο μαθητής απαντά ----
    if not st.session_state.get("submitted"):
        with st.form("quiz_form"):
            for i, q in enumerate(questions):
                st.markdown(f"**{i + 1}. {q.question}**")
                st.radio(
                    "Επίλεξε απάντηση", options=list(range(len(q.options))),
                    format_func=lambda j, q=q: f"{LETTERS[j]}) {q.options[j]}",
                    index=None, key=f"q_{i}", label_visibility="collapsed",
                )
                st.divider()
            done = st.form_submit_button("Υποβολή απαντήσεων", type="primary")

        if done:
            answers = [st.session_state.get(f"q_{i}") for i in range(len(questions))]
            unanswered = [i + 1 for i, a in enumerate(answers) if a is None]
            if unanswered:
                st.warning(f"Δεν απάντησες στις ερωτήσεις: {', '.join(map(str, unanswered))}")
                return
            score, wrong, right = 0, [], []
            for q, a in zip(questions, answers):
                if a == q.correct_index:
                    score += 1
                    right.append(q.source_quote)
                else:
                    wrong.append((q.question, q.source_quote))
            progress.record_session(notes_name, "quiz", score, len(questions), wrong, right)
            # κρατάμε τις απαντήσεις ξεχωριστά: τα widgets "ξεχνούν" την τιμή τους
            # όταν δεν εμφανίζονται πια στη σελίδα
            st.session_state.update(submitted=True, answers=answers,
                                    last_score=(score, len(questions)))
            st.rerun()
        return

    # ---- Βήμα 2: αποτελέσματα ----
    score, total = st.session_state.last_score
    st.metric("Βαθμολογία", f"{score}/{total} ({round(100 * score / total)}%)")
    if score == total:
        st.balloons()
    else:
        st.caption("📌 Την επόμενη φορά θα δώσω έμφαση στα σημεία που έχασες.")

    for i, (q, a) in enumerate(zip(questions, st.session_state.answers)):
        st.markdown(f"**{i + 1}. {q.question}**")
        if a == q.correct_index:
            st.success(f"✅ {LETTERS[a]}) {q.options[a]}")
        else:
            st.error(f"❌ Η απάντησή σου: {LETTERS[a]}) {q.options[a]}")
            st.success(f"Σωστή απάντηση: {LETTERS[q.correct_index]}) {q.options[q.correct_index]}")
            st.info(f"💡 {q.explanation}\n\n📖 *«{q.source_quote}»*")
        st.divider()


# ---------- Flashcards ----------
def show_flashcards(notes_name: str) -> None:
    cards = st.session_state.cards
    idx = st.session_state.card_idx

    if st.session_state.cards_done:
        known = len(st.session_state.known)
        st.metric("Ήξερες", f"{known}/{len(cards)} κάρτες")
        if st.session_state.unknown:
            st.markdown("**Για επανάληψη:**")
            for c in st.session_state.unknown:
                with st.expander(c.front):
                    st.write(c.back)
                    st.caption(f"📖 «{c.source_quote}»")
        return

    card = cards[idx]
    st.progress(idx / len(cards), text=f"Κάρτα {idx + 1} από {len(cards)}")
    with st.container(border=True):
        st.markdown(f"### ❓ {card.front}")
        if st.session_state.show_back:
            st.markdown(f"#### ✅ {card.back}")
            st.caption(f"📖 «{card.source_quote}»")

    if not st.session_state.show_back:
        if st.button("Δείξε την απάντηση", type="primary", width="stretch"):
            st.session_state.show_back = True
            st.rerun()
        return

    col1, col2 = st.columns(2)
    knew = col1.button("👍 Το ήξερα", width="stretch")
    didnt = col2.button("🔁 Δεν το ήξερα", width="stretch")
    if knew or didnt:
        (st.session_state.known if knew else st.session_state.unknown).append(card)
        st.session_state.show_back = False
        if idx + 1 < len(cards):
            st.session_state.card_idx += 1
        else:
            st.session_state.cards_done = True
            progress.record_session(
                notes_name, "flashcards", len(st.session_state.known), len(cards),
                wrong=[(c.front, c.source_quote) for c in st.session_state.unknown],
                right_quotes=[c.source_quote for c in st.session_state.known],
            )
        st.rerun()


# ---------- Πρόοδος ----------
def show_progress(notes_name: str) -> None:
    sessions = progress.history(notes_name)
    if not sessions:
        st.info("Δεν υπάρχει ακόμα ιστορικό. Κάνε ένα quiz ή flashcards για να ξεκινήσεις!")
        return

    df = pd.DataFrame(sessions)
    df["Ποσοστό"] = (100 * df["score"] / df["total"]).round()
    df["Προσπάθεια"] = range(1, len(df) + 1)
    df["Τύπος"] = df["mode"].map({"quiz": "Quiz", "flashcards": "Flashcards"})

    c1, c2, c3 = st.columns(3)
    c1.metric("Προσπάθειες", len(df))
    c2.metric("Τελευταίο σκορ", f"{int(df['Ποσοστό'].iloc[-1])}%")
    c3.metric("Μέσος όρος", f"{int(df['Ποσοστό'].mean())}%")

    chart = (
        alt.Chart(df)
        .mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=80, filled=True))
        .encode(
            x=alt.X("Προσπάθεια:O", title="Προσπάθεια", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Ποσοστό:Q", title="Σωστές απαντήσεις (%)",
                    scale=alt.Scale(domain=[0, 100])),
            tooltip=["Προσπάθεια", "date", "Τύπος", "score", "total", "Ποσοστό"],
        )
        .properties(height=260, title="Η πρόοδός σου")
    )
    st.altair_chart(chart, width="stretch")

    weak = progress.weak_points(notes_name)
    if weak:
        st.markdown("**🎯 Σημεία για επανάληψη**")
        for w in weak:
            st.markdown(f"- {w}")

    with st.expander("Όλες οι προσπάθειες (πίνακας)"):
        st.dataframe(df[["date", "Τύπος", "score", "total", "Ποσοστό"]],
                     hide_index=True, width="stretch")


# ---------- Σελίδα ----------
# Προαιρετικός κωδικός, για να μη "φάει" κάποιος το δωρεάν όριο του API key στο online demo
password = os.getenv("APP_PASSWORD")
if password and not st.session_state.get("unlocked"):
    st.title("📚 Study Quiz Bot")
    typed = st.text_input("Κωδικός πρόσβασης", type="password")
    if typed == password:
        st.session_state.unlocked = True
        st.rerun()
    elif typed:
        st.error("Λάθος κωδικός.")
    st.stop()

st.title("📚 Study Quiz Bot")
st.caption("Ανέβασε τις σημειώσεις σου και διάβασε με quiz και flashcards, "
           "φτιαγμένα **μόνο** από τη δική σου ύλη.")

with st.sidebar:
    st.header("1. Σημειώσεις")
    uploaded = st.file_uploader("Ανέβασε αρχείο", type=[s.strip(".") for s in SUPPORTED])
    use_sample = st.checkbox("ή δοκίμασε με δείγμα (Βιολογία)", value=uploaded is None)

    st.header("2. Ρυθμίσεις")
    mode = st.radio("Τρόπος μελέτης", ["📝 Quiz", "🃏 Flashcards"], horizontal=True)
    n = st.slider("Πόσες ερωτήσεις / κάρτες", 3, 15, 5)
    st.caption(f"Μοντέλο: `{describe()}`")

# φόρτωση σημειώσεων
notes, notes_name = None, None
try:
    if uploaded is not None:
        notes_name = uploaded.name
        notes = read_file(uploaded.name, uploaded.getvalue())
    elif use_sample:
        notes_name = "sample_notes.txt"
        with open("notes/sample_notes.txt", "rb") as f:
            notes = read_file(notes_name, f.read())
except NotesError as e:
    st.error(f"❌ {e}")

if not notes:
    st.info("👈 Ανέβασε ένα αρχείο (.pdf, .docx, .txt, .md) από την πλαϊνή μπάρα για να ξεκινήσεις.")
    st.stop()

# αν άλλαξε αρχείο, καθαρίζουμε ό,τι υπήρχε
if st.session_state.get("notes_name") != notes_name:
    reset_session()
    st.session_state.notes_name = notes_name

st.success(f"📄 **{notes_name}**: {len(notes):,} χαρακτήρες")

tab_study, tab_progress = st.tabs(["📝 Μελέτη", "📊 Πρόοδος"])

with tab_study:
    kind = "quiz" if "Quiz" in mode else "cards"
    button_label = "✨ Φτιάξε νέο quiz" if kind == "quiz" else "✨ Φτιάξε νέες κάρτες"
    if st.button(button_label, type="primary", width="stretch"):
        generate(kind, notes, notes_name, n)

    if kind == "quiz" and st.session_state.get("questions"):
        show_quiz(notes_name)
    elif kind == "cards" and st.session_state.get("cards"):
        show_flashcards(notes_name)

with tab_progress:
    show_progress(notes_name)
