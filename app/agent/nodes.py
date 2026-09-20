"""LangGraph nodes for intent detection and print option extraction."""

import re
from typing import Any

from app.agent.state import AgentState

# Number words mapping for natural language parsing
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "once": 1, "twice": 2, "thrice": 3,
}


def detect_intent(state: AgentState) -> AgentState:
    """Classify user message intent adhering strictly to EVALS.md specifications."""
    message = (state.get("user_message") or "").strip().lower()

    if not message:
        return {**state, "intent": "unknown"}

    # Pricing check
    if any(keyword in message for keyword in ["how much", "price", "pricing", "rate", "cost", "how expensive"]):
        return {**state, "intent": "pricing"}

    # Order status check
    if any(keyword in message for keyword in ["where is my order", "order status", "track", "my print", "pickup status", "is it ready", "where is my job"]):
        return {**state, "intent": "order_status"}

    # Print request check
    if any(keyword in message for keyword in ["print", "photocopy", "xerox", "upload pdf", "start print"]):
        return {**state, "intent": "print"}

    # Greeting check
    if any(message.startswith(greet) for greet in ["hi", "hello", "hey", "good morning", "good evening"]):
        return {**state, "intent": "greeting"}

    # FAQ check
    if any(keyword in message for keyword in ["format", "hours", "location", "payment method", "how do i", "support", "help"]):
        return {**state, "intent": "faq"}

    return {**state, "intent": "unknown"}


def extract_options(state: AgentState) -> AgentState:
    """
    Extract print options (copies, color, duplex) from user message.
    Conforms to EVALS.md cases (e.g. 'Print this three times in black and white.').
    """
    message = (state.get("user_message") or "").lower()
    options: dict[str, Any] = dict(state.get("options") or {})

    # Extract Copies
    # Check digit regex: "3 copies", "3 times", "copies: 3"
    digit_match = re.search(r"(\d+)\s*(?:copies|copy|times|sets)?", message)
    if digit_match and int(digit_match.group(1)) > 0:
        options["copies"] = int(digit_match.group(1))
    else:
        # Check word numbers: "three times", "two copies"
        for word, val in NUMBER_WORDS.items():
            pattern = rf"\b{word}\s*(?:times|copies|copy|sets)?\b"
            if re.search(pattern, message):
                options["copies"] = val
                break

    # Extract Color Mode
    if any(term in message for term in ["black and white", "black & white", "b&w", "bw", "monochrome", "grayscale"]):
        options["color"] = "bw"
    elif any(term in message for term in ["color", "colour", "colored", "full color"]):
        options["color"] = "color"

    # Extract Duplex
    if any(term in message for term in ["double sided", "double-sided", "both sides", "duplex", "two sided", "two-sided"]):
        options["duplex"] = "double"
    elif any(term in message for term in ["single sided", "single-sided", "one side", "one-sided", "simplex"]):
        options["duplex"] = "single"

    # Paper size default A4
    if "paper_size" not in options:
        options["paper_size"] = "A4"

    return {**state, "options": options}


def process_response(state: AgentState) -> AgentState:
    """Generate conversational response based on intent and extracted options."""
    intent = state.get("intent")
    options = state.get("options") or {}

    if intent == "greeting":
        msg = (
            "Hello! Welcome to the WhatsApp Print Agent. 🖨️\n\n"
            "Here is what I can do for you:\n"
            "1. Upload a PDF to start printing.\n"
            "2. Type 'Pricing' to see our current rates.\n"
            "3. Ask about supported print options (A4, B&W, Color, Duplex)."
        )
    elif intent == "pricing":
        msg = (
            "📄 *Current Printing Rates (A4)*:\n"
            "• Black & White: ₹2.00 per page\n"
            "• Color: ₹10.00 per page\n\n"
            "To print, simply send your PDF file!"
        )
    elif intent == "order_status":
        msg = "To check your order status, please provide your Job ID (e.g. 'Status for <Job_ID>')."
    elif intent == "print":
        copies = options.get("copies", 1)
        color = options.get("color", "bw")
        color_label = "Black & White" if color == "bw" else "Color"
        msg = (
            f"Got it! Ready to print {copies} {'copy' if copies == 1 else 'copies'} in {color_label}.\n"
            "Please upload your PDF file to proceed with page count and pricing."
        )
    elif intent == "faq":
        msg = (
            "ℹ️ *Frequently Asked Questions*:\n"
            "• Supported Format: PDF only (up to 25 MB)\n"
            "• Supported Paper: A4\n"
            "• Duplex: Single-sided and Double-sided supported\n"
            "• Payment: Instant digital mock payment before printing."
        )
    else:
        msg = (
            "I'm here to help you print documents. "
            "You can upload a PDF, type 'Pricing' to check rates, or say 'Print' to get started."
        )

    return {**state, "response_message": msg}
