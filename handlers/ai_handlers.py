from telegram import Update
from telegram.ext import ContextTypes

from database import register_user, is_banned, get_tasks
from gemini import get_motivation, get_study_plan, chat


# ─── /motivate ───────────────────────────────────────────────────────────────

async def motivate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user.id, user.username, user.first_name)
    if is_banned(user.id):
        return

    thinking = await update.message.reply_text("✨ Thinking of something just for you...")
    try:
        quote = await get_motivation()
        await thinking.edit_text(f"💪 *Your Motivation Boost:*\n\n{quote}", parse_mode="Markdown")
    except Exception as e:
        await thinking.edit_text("❌ Couldn't reach AI right now. Try again in a moment!")


# ─── /study ──────────────────────────────────────────────────────────────────

async def study_session_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user.id, user.username, user.first_name)
    if is_banned(user.id):
        return

    thinking = await update.message.reply_text("📚 Building your personalized study plan...")
    try:
        tasks = [dict(t) for t in get_tasks(user.id)]
        plan = await get_study_plan(tasks)
        await thinking.edit_text(f"📚 *Your Study Plan:*\n\n{plan}", parse_mode="Markdown")
    except Exception:
        await thinking.edit_text("❌ Couldn't generate a plan right now. Try again shortly!")


# ─── /chat + free-text ───────────────────────────────────────────────────────

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user.id, user.username, user.first_name)
    if is_banned(user.id):
        return

    # Accept both /chat <message> and plain text messages
    if context.args:
        user_message = " ".join(context.args)
    elif update.message and update.message.text:
        user_message = update.message.text
    else:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        reply = await chat(user_message, user.first_name)
        await update.message.reply_text(f"🤖 {reply}")
    except Exception:
        await update.message.reply_text(
            "❌ AI is taking a short break. Try /chat again in a moment!"
        )
