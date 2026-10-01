"""
Σύνδεση με τοπικό ανοιχτό μοντέλο μέσω Ollama (https://ollama.com).
Το Ollama τρέχει στον υπολογιστή σου και δίνει ένα REST API στη θύρα 11434.
Δωρεάν, χωρίς όρια αιτημάτων, και τα δεδομένα δεν φεύγουν από τον υπολογιστή.
"""

import os
import re

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError, create_model

from .errors import LLMError

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
# Πόσα tokens "βλέπει" το μοντέλο. Το προεπιλεγμένο του Ollama είναι μικρό
# και θα έκοβε τις σημειώσεις, οπότε το μεγαλώνουμε.
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "16384"))
TIMEOUT_SECONDS = 600     # τα τοπικά μοντέλα είναι πιο αργά, ειδικά χωρίς κάρτα γραφικών


class OllamaError(LLMError):
    pass


def available_models() -> list[str]:
    """Τα μοντέλα που έχεις κατεβάσει στο Ollama (ollama pull ...)."""
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
    except httpx.HTTPError:
        return []
    return [m["name"] for m in r.json().get("models", [])]


def generate_structured(instruction: str, prompt: str, schema: type[BaseModel],
                        on_status=print) -> list[BaseModel]:
    """
    Ζητά από το τοπικό μοντέλο μια λίστα αντικειμένων με τη μορφή του schema.
    Το Ollama δέχεται JSON schema στο πεδίο "format" και αναγκάζει το μοντέλο
    να απαντήσει σε αυτή τη μορφή (structured output).
    """
    # Τυλίγουμε τη λίστα σε αντικείμενο {"items": [...]}: τα μοντέλα τα πάνε καλύτερα έτσι
    Wrapper = create_model("Items", items=(list[schema], ...))

    body = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": instruction},
            {"role": "user", "content": prompt + '\n\nΑπάντησε ΜΟΝΟ με JSON της μορφής {"items": [...]}.'},
        ],
        "format": Wrapper.model_json_schema(),
        "stream": False,
        "options": {"temperature": 0.4, "num_ctx": OLLAMA_NUM_CTX},
    }

    on_status(f"🖥️ Τοπικό μοντέλο {OLLAMA_MODEL}: μπορεί να πάρει 1-3 λεπτά...")
    for attempt in (1, 2):   # μία επανάληψη αν το JSON βγει χαλασμένο
        try:
            r = httpx.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=TIMEOUT_SECONDS)
        except httpx.ConnectError:
            raise OllamaError("Το Ollama δεν τρέχει. Άνοιξε την εφαρμογή Ollama και ξαναδοκίμασε.")
        except httpx.TimeoutException:
            raise OllamaError("Το τοπικό μοντέλο άργησε πολύ. Δοκίμασε λιγότερες ερωτήσεις ή μικρότερο μοντέλο.")

        if r.status_code == 404:
            raise OllamaError(f"Το μοντέλο {OLLAMA_MODEL} δεν υπάρχει. Κατέβασέ το με: ollama pull {OLLAMA_MODEL}")
        if r.status_code != 200:
            raise OllamaError(f"Σφάλμα Ollama ({r.status_code}): {r.text[:200]}")

        content = r.json().get("message", {}).get("content", "")
        # μερικά μοντέλα "σκέφτονται φωναχτά" μέσα σε <think>...</think>: το αφαιρούμε
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        try:
            return Wrapper.model_validate_json(content).items
        except ValidationError:
            if attempt == 1:
                on_status("⚠️ Το τοπικό μοντέλο έδωσε μη έγκυρο JSON. Ξαναδοκιμάζω...")

    raise OllamaError("Το τοπικό μοντέλο δεν έδωσε έγκυρη απάντηση. Δοκίμασε μεγαλύτερο μοντέλο.")
