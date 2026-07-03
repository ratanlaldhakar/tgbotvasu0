import asyncio
import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-2.5-flash")


async def _ask(prompt: str) -> str:
    """Run Gemini synchronously in a thread to avoid blocking the event loop."""
    response = await asyncio.to_thread(_model.generate_content, prompt)
    return response.text


async def get_motivation() -> str:
    prompt = (
        "Give me a short, powerful motivational message for someone working on their to-do list and studies. "
        "Make it personal, warm, and encouraging. Include 1-2 relevant emojis. Keep it under 4 sentences."
    )
    return await _ask(prompt)


async def get_study_plan(tasks: list[dict]) -> str:
    if not tasks:
        prompt = (
            "The user has no pending tasks right now. "
            "Give them encouraging advice to start fresh, set new goals, and maintain productivity. "
            "Be warm and motivating. Use emojis. Keep it concise."
        )
    else:
        task_list = "\n".join(f"  • {t['task']}" for t in tasks)
        prompt = f"""The user has these pending tasks:
{task_list}

Create a friendly, encouraging study/productivity plan for today. Include:
1. A short motivational opening (1-2 sentences)
2. Suggested order to tackle tasks with rough time estimates
3. One focus tip to stay on track
4. An uplifting closing line

Use emojis to make it engaging. Keep it practical and concise."""
    return await _ask(prompt)


async def chat(user_message: str, user_name: str) -> str:
    prompt = f"""You are a friendly, supportive AI productivity coach inside a Telegram bot.
The user's name is {user_name}.
Be helpful, warm, and concise — keep responses under 250 words and suitable for a chat app.
If the user asks about their tasks or productivity, give practical advice.
User message: {user_message}"""
    return await _ask(prompt)


async def get_daily_achievement_message(user_name: str, tasks_today: int, streak: int) -> str:
    prompt = f"""Write a short, warm end-of-day achievement message for {user_name} who completed {tasks_today} task(s) today.
Their current streak is {streak} consecutive day(s) of completing tasks.
Include:
- Celebration of today's wins
- Recognition of their streak (if > 1)
- Encouragement for tomorrow
Keep it under 5 sentences. Use emojis to make it feel special."""
    return await _ask(prompt)
