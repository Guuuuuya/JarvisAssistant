# JARVIS Assistant

Voice-first AI assistant. Talk to it, it talks back — British accent, glowing orb, Google Calendar/Gmail/Tasks integration. 100% free stack.

## Features

- Voice in (Chrome Web Speech API), wake word `jarvis, ...`
- Spoken replies (Edge TTS, British "Ryan" voice)
- 3D audio-reactive orb (Three.js)
- Brain: Gemini API (free tier), OpenRouter fallback
- Google Calendar (today's events), Gmail (unread subjects), Google Tasks (list/add)
- SQLite long-term memory
- Terminal-style live trace panel (bottom right)
- Orange = small error, red = big error UI states

## Setup

1. Install: Python 3.10+, Node 18+, Chrome
2. `pip install -r requirements.txt`
3. `cd frontend && npm install`
4. `.env` with `GEMINI_API_KEY`, `OPENROUTER_API_KEY`
5. Google: enable Calendar/Gmail/Tasks APIs, OAuth Desktop client → `credentials.json`
6. `python server.py` and `cd frontend && npm run dev`
7. Open http://localhost:5173, click mic, say "Jarvis, ..."

## Voice commands

- "Jarvis, what's on my calendar today?"
- "Jarvis, any unread emails?"
- "Jarvis, what are my tasks?"
- "Jarvis, add task: buy milk"
- "Jarvis, open YouTube"
- "Jarvis, remember that my name is ..."
