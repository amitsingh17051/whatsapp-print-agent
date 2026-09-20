"""Agent helper tools for loading local domain knowledge without vector DBs."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"


def load_faq_knowledge() -> str:
    """Read the local FAQ knowledge base."""
    faq_path = KNOWLEDGE_DIR / "faq.md"
    if faq_path.exists():
        return faq_path.read_text(encoding="utf-8")
    return ""


def load_pricing_knowledge() -> str:
    """Read the local pricing reference."""
    pricing_path = KNOWLEDGE_DIR / "pricing.md"
    if pricing_path.exists():
        return pricing_path.read_text(encoding="utf-8")
    return ""


def load_options_knowledge() -> str:
    """Read the supported print options reference."""
    options_path = KNOWLEDGE_DIR / "printing-options.md"
    if options_path.exists():
        return options_path.read_text(encoding="utf-8")
    return ""
