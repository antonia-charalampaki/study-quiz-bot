"""Κοινά σφάλματα για όλους τους providers (Gemini, Ollama)."""


class LLMError(Exception):
    """Φιλικό σφάλμα που μπορεί να δείξει το UI (terminal ή web)."""
