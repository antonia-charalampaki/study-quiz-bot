"""
Δείχνει ποια μοντέλα μπορείς να χρησιμοποιήσεις:
- τα μοντέλα Gemini του API key σου
- τα τοπικά μοντέλα που έχεις κατεβάσει στο Ollama

Εκτέλεση:  python list_models.py
"""
from studybot import gemini_client, ollama_client
from studybot.errors import LLMError
from studybot.llm import describe

print(f"Ρύθμιση τώρα (LLM_PROVIDER): {describe()}\n")

print("☁️  Gemini:")
try:
    for name in gemini_client.available_models(gemini_client.get_client()):
        mark = "  ← χρησιμοποιείς αυτό" if name == gemini_client.MODEL else ""
        print(f"  • {name}{mark}")
except LLMError as e:
    print(f"  ({e})")
except Exception as e:
    print(f"  (δεν ήταν δυνατή η σύνδεση: {e})")

print("\n🖥️  Ollama (τοπικά):")
local = ollama_client.available_models()
if not local:
    print("  (το Ollama δεν τρέχει ή δεν έχεις κατεβάσει μοντέλα: ollama pull qwen2.5:3b)")
for name in local:
    mark = "  ← χρησιμοποιείς αυτό" if name == ollama_client.OLLAMA_MODEL else ""
    print(f"  • {name}{mark}")
