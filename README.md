# 🤖 AI Study Telegram Bot

A complete, production-ready AI-powered study assistant for Telegram.

## Features

- 🤖 AI Chat (Gemini 2.5 Flash)
- 📚 Study tools: Explain, Summarize, MCQ, Flashcards, Planner
- 🧠 Interactive Quizzes with leaderboard
- 📝 Notes manager (create, edit, delete, favorite, search)
- 📄 PDF processing (summarize, MCQ, notes, Q&A)
- 🧮 Math solver (step-by-step, formulas, graphs, calculator)
- 🌐 Translation (100+ languages with detection)
- 🖼️ OCR (image to text, handwriting recognition)
- 👤 User profiles with streaks, achievements, referrals
- 🛡️ Admin panel (broadcast, ban, stats, maintenance)
- 📅 Exam countdown tracker
- 💾 Firebase Realtime Database storage
- ⚡ Rate limiting & flood protection

## Deployment (Railway)

### 1. Set Environment Variables

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram Bot Token from @BotFather |
| `GOOGLE_API_KEY` | Google Gemini API key |
| `FIREBASE_DATABASE_URL` | Firebase Realtime DB URL |
| `FIREBASE_PROJECT_ID` | Firebase project ID |
| `FIREBASE_CLIENT_EMAIL` | Firebase service account email |
| `FIREBASE_PRIVATE_KEY` | Firebase private key (with `\n`) |
| `OWNER_ID` | Your Telegram user ID |
| `CHANNEL_USERNAME` | Channel username for force-join (optional) |

### 2. Deploy

```bash
git init
git add .
git commit -m "Initial deploy"
# Connect to Railway and push
