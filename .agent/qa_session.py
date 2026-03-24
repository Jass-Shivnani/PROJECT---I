"""
Dione AI — Agent Q&A Session Script
====================================
Interactive script for your AI agent (me!) to ask you questions
and record your answers. This helps me understand exactly what 
you want so I can build the right things.

Usage:
    python .agent/qa_session.py

Your answers are saved to .agent/qa_answers.json
"""

import json
import os
from pathlib import Path
from datetime import datetime

AGENT_DIR = Path(__file__).parent
ANSWERS_FILE = AGENT_DIR / "qa_answers.json"

# ─── Color helpers ──────────────────────────────────────────

def cyan(text): return f"\033[96m{text}\033[0m"
def yellow(text): return f"\033[93m{text}\033[0m"
def green(text): return f"\033[92m{text}\033[0m"
def magenta(text): return f"\033[95m{text}\033[0m"
def bold(text): return f"\033[1m{text}\033[0m"
def dim(text): return f"\033[2m{text}\033[0m"

def print_header():
    print()
    print(cyan("=" * 60))
    print(cyan("  🌙 Dione AI — Agent Q&A Session"))
    print(cyan("  I've analyzed your codebase. Now I need your input!"))
    print(cyan("=" * 60))
    print()
    print(dim("  Type your answer and press Enter."))
    print(dim("  Type 'skip' to skip a question."))
    print(dim("  Type 'quit' to stop (answers so far will be saved)."))
    print()

QUESTIONS = [
    # ─── Personalisation ────────────────────────────────────
    {
        "id": "assistant_name",
        "category": "🎭 Personalisation",
        "question": "What should users be able to name the assistant? Should 'Dione' be the default name, or do you want a different default?",
        "context": "Right now the assistant is always called 'Dione'. You mentioned you want it customizable."
    },
    {
        "id": "onboarding_style",
        "category": "🎭 Personalisation",
        "question": "For the onboarding flow — when a new user starts, how should Dione ask questions? Should it:\n   (a) Ask all setup questions upfront before anything else\n   (b) Ask 1-2 questions AFTER each normal response (gradually learn)\n   (c) Both — quick essential setup, then gradual learning\n   Which approach do you prefer?",
        "context": "You mentioned when not set up, after answering, it should also add personalization questions."
    },
    {
        "id": "onboarding_questions",
        "category": "🎭 Personalisation",
        "question": "What ESSENTIAL info should Dione ask during setup? I'm thinking:\n   - Name\n   - What to call the assistant\n   - Profession / field of work\n   - Communication style preference (formal/casual/technical)\n   - Active hours (when they usually work)\n   Anything else you want added or removed?",
        "context": "This defines the onboarding questionnaire."
    },

    # ─── Profession Knowledge ───────────────────────────────
    {
        "id": "profession_data",
        "category": "📚 Profession Knowledge",
        "question": "When the user tells their profession, you want Dione to fetch and save domain knowledge. What kind of data should it fetch?\n   Examples: industry terminology, common tools, best practices, news sources, key frameworks\n   Should it use web search to gather this? Or do you have specific sources in mind?",
        "context": "You said: 'the agent should look for data and save it in an organised way... AI summarized, not AI generated'"
    },
    {
        "id": "profession_update_freq",
        "category": "📚 Profession Knowledge",
        "question": "How often should the profession knowledge be refreshed/updated?\n   (a) Once at setup, then manual refresh\n   (b) Weekly auto-refresh\n   (c) When the user asks about something new in their field\n   (d) Other?",
        "context": "This data will be kept as context for reference."
    },

    # ─── Social Media & Messaging ──────────────────────────
    {
        "id": "priority_integrations",
        "category": "📱 Social Media & Messaging",
        "question": "You mentioned Gmail, Slack, Instagram. Which integrations should I build FIRST? Rank these by priority:\n   1. Gmail (read/send emails)\n   2. Slack (read messages, post)\n   3. Instagram (DM monitoring)\n   4. WhatsApp (already has a directory)\n   5. Discord\n   6. Telegram\n   Which 2-3 should I focus on first?",
        "context": "Each integration takes significant work. We need to prioritize."
    },
    {
        "id": "gmail_scope",
        "category": "📱 Social Media & Messaging",
        "question": "For Gmail specifically — what should Dione be able to do?\n   (a) Just read/summarize new emails\n   (b) Read + draft replies (user approves before sending)\n   (c) Read + auto-respond to certain categories\n   (d) Full send capability\n   How much autonomy?",
        "context": "The Gmail integration stub exists but has no real API code."
    },
    {
        "id": "social_monitoring",
        "category": "📱 Social Media & Messaging",
        "question": "For social media monitoring — should Dione:\n   (a) Just notify about new messages/mentions\n   (b) Also summarize message threads\n   (c) Also draft responses\n   (d) Track user's online status across platforms",
        "context": "You want it to check messaging apps and social media."
    },

    # ─── Heartbeat & Presence ────────────────────────────────
    {
        "id": "heartbeat_sleep",
        "category": "💓 Heartbeat & Presence",
        "question": "For the adaptive heartbeat / sleep detection — how should Dione detect the user is asleep?\n   (a) Based on active hours from profile (e.g., 11PM-7AM = sleep)\n   (b) Track when user last interacted with the app\n   (c) Both — use active hours as baseline, refine with real interaction data\n   Which approach?",
        "context": "You want the heartbeat to slow down when user is inactive/sleeping."
    },
    {
        "id": "heartbeat_intervals",
        "category": "💓 Heartbeat & Presence",
        "question": "What intervals make sense for the heartbeat?\n   - Active user: check every __ minutes? (currently 1 min)\n   - Slightly inactive: check every __ minutes?\n   - Sleeping/away: check every __ minutes?\n   Give me the numbers you think work.",
        "context": "Currently it's a flat 60 seconds. You want it adaptive."
    },

    # ─── Gemini Audio ────────────────────────────────────────
    {
        "id": "gemini_audio",
        "category": "🎤 Gemini Audio",
        "question": "You mentioned Gemini Audio Model. What's the use case?\n   (a) Voice-to-text input (user speaks, Dione processes as text)\n   (b) Text-to-speech output (Dione speaks responses)\n   (c) Full voice conversation (both input and output)\n   (d) Audio processing (analyze audio files, meeting recordings)\n   Which should I focus on?",
        "context": "You said you want to use Gemini audio model. Need to understand the scope."
    },
    {
        "id": "gemini_api_key",
        "category": "🎤 Gemini Audio",
        "question": "Do you already have a Gemini API key set up? (yes/no)\n   If yes, is it in your .env file?\n   If no, should I help you get one?",
        "context": "You mentioned you'd give API keys. Need to know current state."
    },

    # ─── Architecture Decisions ──────────────────────────────
    {
        "id": "llm_backend",
        "category": "⚙️ Architecture",
        "question": "Your config shows backend='copilot' but .env.example defaults to 'gemini'. Which LLM backend should be the PRIMARY one going forward?\n   (a) Gemini (cloud, fast, good for audio)\n   (b) Copilot/GitHub Models (what you're using now)\n   (c) Ollama (local, private)\n   (d) Keep all options, make it easy to switch",
        "context": "There's a config mismatch I found. Need to align."
    },
    {
        "id": "security_priority",
        "category": "⚙️ Architecture",
        "question": "The credential vault currently stores tokens as PLAINTEXT JSON. For the capstone demo:\n   (a) This is fine, just document it as a known limitation\n   (b) I should add basic encryption (Fernet symmetric key)\n   (c) Use OS keyring (most secure, but adds complexity)\n   How secure do you want it?",
        "context": "Found that CredentialVault has no actual encryption despite the docstring."
    },

    # ─── Priority & Scope ────────────────────────────────────
    {
        "id": "next_work",
        "category": "🎯 What's Next?",
        "question": "Given everything I've found, what should I work on FIRST?\n   (a) Fix the bugs I found (KG extraction, mood saturation, confirmation flow)\n   (b) Build the personalisation onboarding system\n   (c) Implement a real integration (Gmail, Slack, etc.)\n   (d) Adaptive heartbeat system\n   (e) Gemini audio integration\n   (f) Something else? Tell me!",
        "context": "I want to prioritize what matters most to you."
    },
    {
        "id": "deadline",
        "category": "🎯 What's Next?",
        "question": "Do you have a deadline for the capstone? When is the next submission/presentation?",
        "context": "This helps me plan the work intensity."
    },
    {
        "id": "anything_else",
        "category": "🎯 What's Next?",
        "question": "Anything else you want to tell me? Any features I missed? Any concerns about the current code?",
        "context": "Open-ended — catch anything I might have missed."
    },
]


def load_existing_answers() -> dict:
    """Load previously saved answers, if any."""
    if ANSWERS_FILE.exists():
        try:
            return json.loads(ANSWERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_answers(answers: dict):
    """Save answers to disk."""
    ANSWERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ANSWERS_FILE.write_text(
        json.dumps(answers, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def run_qa():
    """Run the interactive Q&A session."""
    print_header()
    
    answers = load_existing_answers()
    if answers:
        existing = len([q for q in QUESTIONS if q["id"] in answers])
        print(yellow(f"  📋 Found {existing}/{len(QUESTIONS)} previously answered questions."))
        resume = input(yellow("  Resume where you left off? (y/n): ")).strip().lower()
        if resume != "y":
            answers = {}
        print()

    current_category = ""
    answered = 0
    skipped = 0
    
    for i, q in enumerate(QUESTIONS, 1):
        # Skip already answered
        if q["id"] in answers:
            continue
            
        # Print category header
        if q["category"] != current_category:
            current_category = q["category"]
            print()
            print(magenta(f"  ━━━ {current_category} ━━━"))
            print()

        # Print question
        print(bold(f"  Q{i}/{len(QUESTIONS)}: {q['question']}"))
        print(dim(f"  💡 Context: {q['context']}"))
        print()
        
        answer = input(green("  Your answer: ")).strip()
        
        if answer.lower() == "quit":
            print()
            print(yellow("  Saving your answers so far..."))
            save_answers(answers)
            print(green(f"  ✅ Saved {answered} answers to {ANSWERS_FILE.name}"))
            print(dim(f"  Run this script again to resume."))
            return
        
        if answer.lower() == "skip":
            skipped += 1
            print(dim("  ⏭️  Skipped"))
            print()
            continue
        
        answers[q["id"]] = {
            "answer": answer,
            "answered_at": datetime.now().isoformat(),
        }
        answered += 1
        
        # Auto-save after each answer
        save_answers(answers)
        print(dim(f"  ✅ Saved"))
        print()
    
    # Done!
    print()
    print(cyan("=" * 60))
    print(cyan("  🎉 All questions answered!"))
    print(cyan(f"  Answered: {answered} | Skipped: {skipped}"))
    print(cyan(f"  Saved to: {ANSWERS_FILE}"))
    print(cyan("=" * 60))
    print()
    print(dim("  Now come back to the chat and tell me:"))
    print(dim("  'I've answered the questions, let's continue!'"))
    print()


if __name__ == "__main__":
    run_qa()
