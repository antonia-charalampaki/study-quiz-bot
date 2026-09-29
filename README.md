# 📚 Study Quiz Bot

Ένα AI chatbot που βοηθά μαθητές και φοιτητές να διαβάζουν: του δίνεις τις σημειώσεις ενός μαθήματος, φτιάχνει ερωτήσεις **μόνο από αυτή την ύλη**, σε εξετάζει και σου εξηγεί τα λάθη σου με παραπομπή στις σημειώσεις.

> 🚧 Σε εξέλιξη. Μέρα 1: έκδοση για terminal.

## Εγκατάσταση
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # και βάλε το Gemini API key σου μέσα
```

## Εκτέλεση
```bash
python quiz_bot.py                          # με το δείγμα σημειώσεων
python quiz_bot.py notes/my_notes.txt 10    # δικές σου σημειώσεις, 10 ερωτήσεις
```

## Τεχνολογίες
Python · Google Gemini API · Pydantic (structured output)
