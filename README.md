# 🤖 AI Productivity Bot — Telegram

A feature-rich Telegram bot powered by **Google Gemini AI** for managing to-do lists, study reminders, and daily motivation.

---

## ✨ Features

| Category | Feature |
|---|---|
| ✅ Tasks | Add, list, complete, delete tasks |
| ⏰ Reminders | Daily reminders at a specific time |
| 📚 AI Study Plan | Gemini generates a plan from your tasks |
| 💪 Motivation | Instant AI-generated motivational messages |
| 🤖 AI Chat | Chat freely with Gemini |
| 🏆 Achievements | Badges, streaks, daily/weekly stats |
| 🌙 Nightly Summary | Auto achievement message at 10 PM |
| 🔐 Admin Panel | Broadcast, ban/unban, user list, stats |

---

## 🚀 Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Add your Gemini API key

Open the `.env` file and replace `your_google_ai_studio_api_key_here` with your key from [Google AI Studio](https://aistudio.google.com/):

```
GEMINI_API_KEY=AIza...your_key_here
```

### 3. Run the bot

```bash
python app.py
```

That's it! Open Telegram and message your bot.

---

## 💬 Commands

### User Commands
| Command | Description |
|---|---|
| `/start` | Welcome message & command list |
| `/add <task>` | Add a task (e.g. `/add Study maths`) |
| `/list` | View all pending tasks |
| `/done <id>` | Mark a task as complete |
| `/delete <id>` | Delete a task |
| `/remind <id> <HH:MM>` | Set daily reminder (e.g. `/remind 2 18:30`) |
| `/reminders` | View active reminders |
| `/study` | Get an AI-generated study plan |
| `/motivate` | Get a motivational message from AI |
| `/chat <message>` | Chat with Gemini AI |
| `/mystats` | View your stats, streak & badges |

### Admin Commands
| Command | Description |
|---|---|
| `/admin` | Admin panel |
| `/stats` | Bot usage statistics |
| `/users` | List all registered users |
| `/broadcast <msg>` | Send message to all users |
| `/ban <user_id>` | Ban a user |
| `/unban <user_id>` | Unban a user |

---

## 🏆 Achievement Badges

| Badge | Requirement |
|---|---|
| 🥉 First Task | Complete 1 task |
| 🥈 Task Warrior | Complete 10 tasks |
| 🥇 Task Master | Complete 50 tasks |
| 💎 Legend | Complete 100 tasks |
| 🔥 On Fire | 3-day streak |
| ⚡ Week Warrior | 7-day streak |
| 🌟 Monthly Champion | 30-day streak |
| 🚀 Superstar Day | 5 tasks in one day |

---

## 📁 Project Structure

```
tg bot a/
├── app.py                  # Main entry point
├── config.py               # Environment config
├── database.py             # SQLite database layer
├── gemini.py               # Google Gemini AI wrapper
├── handlers/
│   ├── user_handlers.py    # User commands
│   ├── admin_handlers.py   # Admin commands
│   └── ai_handlers.py      # AI-powered commands
├── .env                    # Your secrets (never share this!)
├── .env.example            # Template
└── requirements.txt        # Python dependencies
```
