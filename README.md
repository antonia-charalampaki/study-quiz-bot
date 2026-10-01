# 📚 Study Quiz Bot

Ένα AI chatbot που βοηθά μαθητές και φοιτητές στο διάβασμα. Του δίνεις τις σημειώσεις ενός μαθήματος και φτιάχνει ερωτήσεις **μόνο από αυτή την ύλη**. Μετά σε εξετάζει και σου εξηγεί κάθε λάθος με **παραπομπή στο σημείο των σημειώσεων** από όπου βγαίνει η σωστή απάντηση.

> 🚧 Σε εξέλιξη: web εφαρμογή (Streamlit) και έκδοση terminal. Ακολουθεί online demo.

## ✨ Λειτουργίες
- Σημειώσεις από αρχεία **.txt, .md, .pdf και .docx**
- Ερωτήσεις πολλαπλής επιλογής αποκλειστικά από την ύλη που δίνει ο χρήστης (grounded generation)
- **Flashcards** με αυτοαξιολόγηση και επανάληψη των καρτών που δεν ήξερες
- **Προσαρμοστική μελέτη**: αποθηκεύει τα λάθη και τα επόμενα quiz δίνουν έμφαση σε αυτά
- Ιστορικό προόδου ανά μάθημα, με γράφημα στη web εφαρμογή
- **Web εφαρμογή** (Streamlit) με ανέβασμα αρχείων, quiz με κουμπιά και flashcards
- Εξήγηση κάθε λάθους με αυτούσιο απόσπασμα από τις σημειώσεις
- Βαθμολογία και λίστα με τα σημεία για επανάληψη
- Structured output (JSON schema με Pydantic), ώστε οι απαντήσεις του μοντέλου να έχουν πάντα σωστή μορφή
- Αντοχή σε σφάλματα: επαναλήψεις με exponential backoff σε 503/429 και προαιρετικό εφεδρικό μοντέλο

## 🛠️ Τεχνολογίες
Python · Streamlit · Google Gemini API (`google-genai`) · Pydantic · pypdf · python-docx · Altair · python-dotenv

## 🚀 Εγκατάσταση
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
```
Βάλε το Gemini API key σου στο `.env`. Μπορείς να πάρεις δωρεάν κλειδί από το [Google AI Studio](https://aistudio.google.com).

## ▶️ Εκτέλεση
**Web εφαρμογή:**
```bash
streamlit run app.py
```
**Terminal:**
```bash
python quiz_bot.py                                  # quiz με το δείγμα σημειώσεων
python quiz_bot.py notes/biology.pdf -n 10          # 10 ερωτήσεις από PDF
python quiz_bot.py notes/biology.docx --mode cards  # flashcards
python quiz_bot.py notes/biology.pdf --stats        # η πρόοδός σου
```

## 🧱 Δομή
```
app.py                   # web εφαρμογή (Streamlit)
quiz_bot.py              # εφαρμογή terminal
list_models.py           # δείχνει τα διαθέσιμα μοντέλα Gemini
studybot/
  gemini_client.py       # σύνδεση με Gemini, retry & fallback
  loaders.py             # ανάγνωση txt / md / pdf / docx
  generator.py           # prompts & structured output (ερωτήσεις, flashcards)
  progress.py            # ιστορικό & αδύναμα σημεία (JSON)
```

## 🗺️ Roadmap
- [x] Quiz στο terminal με εξηγήσεις και παραπομπές
- [x] Ανέβασμα PDF / DOCX
- [x] Λειτουργία flashcards
- [x] Προσαρμοστική επανάληψη λαθών
- [x] Web εφαρμογή (Streamlit)
- [ ] Αξιολόγηση ποιότητας ερωτήσεων
- [ ] Online demo
