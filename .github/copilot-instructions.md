# Copilot Instructions — DIONE AI Project

## MANDATORY RULE — READ THIS EVERY SINGLE TIME

**NEVER. STOP. WITHOUT. ASKING.**

After completing ANY task, ANY fix, ANY file edit, ANY test — you MUST use the `ask_questions` tool to ask the user **"What's next?"**. This is NOT optional. This is NOT a suggestion. This is an absolute, non-negotiable requirement.

### The Rule:

> **Every single time you finish doing something — ANYTHING — you ask "What's next?" using the question tool. No exceptions. No excuses. No "here's a summary, goodbye." You DO NOT stop. You DO NOT end your turn silently. You ASK.**

### Why:

The user said **"DONT STOP"**. That means you keep going. If you've genuinely completed everything and there's nothing obvious left, you STILL ask what's next. The user drives the session, not you.

### What "finishing" means:

- Fixed a bug? → Ask what's next.
- Created a file? → Ask what's next.
- Ran a test? → Ask what's next.
- Updated multiple files? → Ask what's next.
- Server is running? → Ask what's next.
- Flutter compiled? → Ask what's next.
- Answered a question? → Ask what's next.
- Hit an error and resolved it? → Ask what's next.
- Hit an error and CAN'T resolve it? → Explain it, THEN ask what's next.

### How:

Use the `ask_questions` tool with a question like:
- "What should I work on next?"
- Provide options based on what's remaining or logical next steps.

**If you forget this rule, you have failed. Period.**

---

## Project Context

- **Project**: Dione AI — Local Large Action Model Orchestration Engine
- **Stack**: Python 3.14 (FastAPI) + Flutter/Dart mobile app
- **LLM Backend**: GitHub Copilot SDK (GPT-5 mini)
- **Server Port**: 8900
- **Key Systems**: ReAct engine, personality/mood, heartbeat, dynamic UI, user profiling
- **Virtual env**: `.venv` in project root
- **User**: Jass — CS student, capstone project

## Work Style

- The user wants continuous progress. Don't pause unless blocked.
- Always use the todo list for multi-step work.
- Test after building. Don't just write code and walk away.
- When the user says "DONT STOP", it means keep building until everything works end-to-end, then ask what's next.
