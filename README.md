# 📚 Study Quiz Bot

Ένα AI chatbot που βοηθά μαθητές και φοιτητές στο διάβασμα. Του δίνεις τις σημειώσεις ενός μαθήματος και φτιάχνει quiz και flashcards **μόνο από αυτή την ύλη**. Σε κάθε λάθος εξηγεί τη σωστή απάντηση με **αυτούσιο απόσπασμα από τις σημειώσεις**, και ο κώδικας ελέγχει ότι το απόσπασμα υπάρχει πράγματι στο κείμενο.

🔗 **Online demo:** _(βάλε εδώ το link του Streamlit Cloud)_

## ✨ Λειτουργίες
- Σημειώσεις από αρχεία **.txt, .md, .pdf και .docx**
- Ερωτήσεις πολλαπλής επιλογής και **flashcards** αποκλειστικά από την ύλη του χρήστη (grounded generation)
- **Έλεγχος παραπομπών:** κάθε `source_quote` αναζητείται στο κείμενο και ό,τι δεν τεκμηριώνεται απορρίπτεται
- **Προσαρμοστική μελέτη:** αποθηκεύει τα λάθη και τα επόμενα quiz δίνουν έμφαση σε αυτά
- **Provider-agnostic:** Google Gemini (cloud) ή τοπικό ανοιχτό μοντέλο μέσω **Ollama**, με αυτόματη εναλλαγή
- **Αντοχή σε σφάλματα:** retry με αυξανόμενη αναμονή σε 503/429, αυτόματο εφεδρικό μοντέλο, φιλικά μηνύματα
- **Structured output:** JSON schema με Pydantic, ώστε οι απαντήσεις του μοντέλου να έχουν πάντα σωστή μορφή
- Web εφαρμογή (Streamlit) με γράφημα προόδου, και έκδοση για terminal

## 🧱 Αρχιτεκτονική
```
 UI           app.py (Streamlit)        quiz_bot.py (terminal)
                       \                  /
 Λογική        loaders → generator → grounding      progress
                            |
 LLM layer               llm.py  (αλυσίδα providers)
                        /        \
               gemini_client    ollama_client
               (cloud API)      (τοπικό μοντέλο)
```

| Αρχείο | Ρόλος |
|---|---|
| `app.py` | Web εφαρμογή (Streamlit) |
| `quiz_bot.py` | Εφαρμογή terminal |
| `list_models.py` | Δείχνει τα διαθέσιμα μοντέλα Gemini και Ollama |
| `studybot/loaders.py` | Ανάγνωση txt / md / pdf / docx |
| `studybot/generator.py` | Prompts, schemas (Pydantic), ερωτήσεις και flashcards |
| `studybot/grounding.py` | Έλεγχος ότι κάθε παραπομπή υπάρχει στις σημειώσεις |
| `studybot/llm.py` | Ενιαίο σημείο κλήσης LLM, αλυσίδα providers |
| `studybot/gemini_client.py` | Gemini API, retry και fallback μοντέλων |
| `studybot/ollama_client.py` | Τοπικό μοντέλο μέσω του REST API του Ollama |
| `studybot/progress.py` | Ιστορικό και αδύναμα σημεία (αρχείο JSON ή μνήμη συνεδρίας) |

## 🛠️ Τεχνολογίες
Python · Streamlit · Google Gemini API (`google-genai`) · Ollama · httpx · Pydantic · pypdf · python-docx · Altair · pandas · python-dotenv

## 🚀 Εγκατάσταση
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
```
Στο `.env` διαλέγεις provider με το `LLM_PROVIDER`:
- **Gemini:** βάλε το API key σου (δωρεάν από το [Google AI Studio](https://aistudio.google.com)).
- **Ollama:** εγκατάστησε το [Ollama](https://ollama.com) και κατέβασε ένα μοντέλο, π.χ. `ollama pull qwen2.5:3b`.
- `LLM_PROVIDER=gemini,ollama`: πρώτα Gemini, κι αν αποτύχει, τοπικό μοντέλο.

## ▶️ Εκτέλεση
```bash
streamlit run app.py                                # web εφαρμογή
python quiz_bot.py notes/biology.pdf -n 10          # terminal: 10 ερωτήσεις από PDF
python quiz_bot.py notes/biology.docx --mode cards  # flashcards
python quiz_bot.py notes/biology.pdf --stats        # η πρόοδός σου
python list_models.py                               # διαθέσιμα μοντέλα
```

## ☁️ Online demo (Streamlit Community Cloud)
1. Στο [share.streamlit.io](https://share.streamlit.io) σύνδεση με GitHub → **Create app** → αυτό το repo, branch `main`, αρχείο `app.py`.
2. Στις ρυθμίσεις της εφαρμογής, στα **Secrets**:
   ```toml
   GEMINI_API_KEY = "..."
   LLM_PROVIDER = "gemini"
   STUDYBOT_STORAGE = "session"
   APP_PASSWORD = "..."        # προαιρετικό
   ```
   Το Ollama δεν τρέχει στο cloud, γι' αυτό εκεί ο provider είναι μόνο `gemini`. Με `STUDYBOT_STORAGE=session` κάθε επισκέπτης έχει τη δική του πρόοδο.

## 🗺️ Roadmap
- [x] Quiz και flashcards με εξηγήσεις και παραπομπές
- [x] PDF / DOCX, προσαρμοστική επανάληψη λαθών
- [x] Web εφαρμογή (Streamlit)
- [x] Τοπικά μοντέλα (Ollama) και αλυσίδα providers
- [x] Αυτόματος έλεγχος παραπομπών
- [ ] Online demo
- [ ] Αξιολόγηση ποιότητας ερωτήσεων σε test set
- [ ] RAG με chunking για πολύ μεγάλα αρχεία
