"""
Δείχνει ποια μοντέλα Gemini μπορεί να χρησιμοποιήσει το API key σου.
Χρήσιμο για να διαλέξεις GEMINI_MODEL ή GEMINI_FALLBACK_MODEL στο .env.

Εκτέλεση:  python list_models.py
"""
from studybot.gemini_client import get_client, available_models, MODEL

for name in available_models(get_client()):
    mark = "  ← χρησιμοποιείς αυτό" if name == MODEL else ""
    print(f"• {name}{mark}")
