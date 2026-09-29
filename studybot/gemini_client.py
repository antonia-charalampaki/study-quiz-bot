"""
Σύνδεση με το Gemini.
Εδώ είναι μαζεμένα: οι ρυθμίσεις από το .env, η δημιουργία client
και η κλήση με επαναλήψεις (retry) όταν ο server είναι φορτωμένος.
"""

import os
import re
import time
import logging

from dotenv import load_dotenv
from google import genai
from google.genai import types, errors

# κρύβουμε μια ακίνδυνη προειδοποίηση της βιβλιοθήκης για το AFC
logging.getLogger("google_genai.models").setLevel(logging.ERROR)

load_dotenv()  # διαβάζει το κρυφό αρχείο .env

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "")
RETRY_WAITS = [5, 15, 30]   # δευτερόλεπτα αναμονής ανάμεσα στις προσπάθειες
MAX_FALLBACKS = 2            # πόσα εφεδρικά μοντέλα δοκιμάζουμε το πολύ


class GeminiError(Exception):
    """Φιλικό σφάλμα που μπορεί να δείξει το UI (terminal ή web)."""


def get_client() -> genai.Client:
    if not API_KEY:
        raise GeminiError("Λείπει το GEMINI_API_KEY. Φτιάξε αρχείο .env (δες το .env.example).")
    return genai.Client(api_key=API_KEY)


def available_models(client: genai.Client) -> list[str]:
    """Τα μοντέλα Gemini που μπορεί να χρησιμοποιήσει ο λογαριασμός σου για κείμενο."""
    names = []
    for m in client.models.list():
        actions = m.supported_actions or []
        name = (m.name or "").removeprefix("models/")
        if "generateContent" in actions and name.startswith("gemini"):
            names.append(name)
    return names


EXCLUDE = ("image", "tts", "audio", "live", "embedding", "transcribe",
           "robotics", "computer-use", "omni")


def _version(name: str) -> float:
    """Βγάζει τον αριθμό έκδοσης από το όνομα, π.χ. gemini-3.7-flash -> 3.7"""
    match = re.search(r"gemini-(\d+(?:\.\d+)?)", name)
    return float(match.group(1)) if match else 0.0


def fallback_models(client: genai.Client, exclude: str) -> list[str]:
    """
    Η σειρά των εφεδρικών μοντέλων:
    - αν έχεις ορίσει GEMINI_FALLBACK_MODEL στο .env (ένα ή περισσότερα, χωρισμένα με κόμμα), αυτά
    - αλλιώς, τα νεότερα 'flash' μοντέλα του λογαριασμού σου (όχι preview / εικόνας / ήχου)
    """
    if FALLBACK_MODEL:
        return [m.strip() for m in FALLBACK_MODEL.split(",") if m.strip()]
    try:
        names = available_models(client)
    except Exception:
        return []
    candidates = [m for m in names
                  if "flash" in m and m != exclude and "preview" not in m
                  and "latest" not in m and not any(x in m for x in EXCLUDE)]
    # νεότερη έκδοση πρώτα· στην ίδια έκδοση, πρώτα το κανονικό και μετά το lite
    candidates.sort(key=lambda m: (-_version(m), "lite" in m))
    return candidates[:MAX_FALLBACKS]


def call_gemini(client: genai.Client, contents: str, config: types.GenerateContentConfig,
                on_status=print):
    """
    Καλεί το Gemini με ασφάλεια:
    - σε 503 (φορτωμένος server) ή 429 (όριο αιτημάτων) περιμένει και ξαναδοκιμάζει
    - αν αποτύχει, δοκιμάζει εφεδρικό μοντέλο (από το .env ή όποιο άλλο 'flash' βρει)
    on_status: συνάρτηση που δείχνει μηνύματα προόδου (print στο terminal, κάτι άλλο στο web)
    """
    fallbacks = None                      # τα βρίσκουμε μόνο αν χρειαστούν
    queue = [MODEL]

    while queue:
        model = queue.pop(0)
        for attempt, wait in enumerate(RETRY_WAITS + [None], start=1):
            try:
                return client.models.generate_content(model=model, contents=contents, config=config)
            except errors.ServerError as e:
                reason = f"ο server του {model} είναι φορτωμένος ({e.code})"
            except errors.ClientError as e:
                if e.code == 429:
                    reason = f"ξεπεράστηκε το δωρεάν όριο αιτημάτων του {model} (429)"
                elif e.code == 404:
                    on_status(f"⚠️  Το μοντέλο {model} δεν είναι διαθέσιμο.")
                    break
                elif e.code in (400, 401, 403):
                    raise GeminiError(f"Πρόβλημα με το API key ή το αίτημα ({e.code}): {e.message}")
                else:
                    raise
            if wait is None:
                break
            on_status(f"⏳ {reason}. Ξαναδοκιμάζω σε {wait} δευτερόλεπτα... "
                      f"({attempt}/{len(RETRY_WAITS)})")
            time.sleep(wait)

        if fallbacks is None:
            fallbacks = [m for m in fallback_models(client, exclude=MODEL) if m != MODEL]
            queue.extend(fallbacks)
        if queue:
            on_status(f"🔁 Δοκιμάζω το εφεδρικό μοντέλο {queue[0]}...")

    raise GeminiError("Το Gemini δεν απαντά αυτή τη στιγμή. Δοκίμασε ξανά σε λίγα λεπτά.")
