"""
Ένα σημείο για όλα τα LLM (provider-agnostic).

Το υπόλοιπο πρόγραμμα καλεί ΜΟΝΟ το generate_structured() αυτού του αρχείου
και δεν ξέρει αν από πίσω απαντά το Gemini ή ένα τοπικό μοντέλο.

Στο .env διαλέγεις τη σειρά με το LLM_PROVIDER, π.χ.:
    LLM_PROVIDER=gemini          μόνο Gemini
    LLM_PROVIDER=ollama          μόνο τοπικό μοντέλο
    LLM_PROVIDER=gemini,ollama   πρώτα Gemini, κι αν αποτύχει, τοπικό μοντέλο
"""

import os

from dotenv import load_dotenv
from pydantic import BaseModel

from .errors import LLMError
from . import gemini_client, ollama_client

load_dotenv()

PROVIDERS = [p.strip().lower() for p in os.getenv("LLM_PROVIDER", "gemini").split(",") if p.strip()]

# κάθε provider = μια συνάρτηση με την ίδια "υπογραφή"
_BACKENDS = {
    "gemini": gemini_client.generate_structured,
    "ollama": ollama_client.generate_structured,
}


def describe() -> str:
    """Κείμενο για το UI, π.χ. 'gemini (gemini-3.8-flash) → ollama (qwen2.5:3b)'"""
    names = {"gemini": f"gemini ({gemini_client.MODEL})",
             "ollama": f"ollama ({ollama_client.OLLAMA_MODEL})"}
    return " → ".join(names.get(p, p) for p in PROVIDERS)


def generate_structured(instruction: str, prompt: str, schema: type[BaseModel],
                        on_status=print) -> list[BaseModel]:
    """Δοκιμάζει τους providers με τη σειρά, μέχρι κάποιος να απαντήσει."""
    failures = []
    for i, name in enumerate(PROVIDERS):
        backend = _BACKENDS.get(name)
        if backend is None:
            raise LLMError(f"Άγνωστος provider «{name}» στο LLM_PROVIDER. Επιλογές: gemini, ollama")
        try:
            return backend(instruction, prompt, schema, on_status=on_status)
        except LLMError as e:
            failures.append(f"{name}: {e}")
            if i + 1 < len(PROVIDERS):
                on_status(f"🔄 Ο provider {name} απέτυχε ({e}). Περνάω στον {PROVIDERS[i + 1]}...")
    raise LLMError(" | ".join(failures))
