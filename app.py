import logging
from datetime import time as dt_time

from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters,
)

from config import BOT_TOKEN, TIMEZONE
from database import init_db, get_all_active_reminders, get_users_with_tasks_today, get_user_stats, get_streak
from gemini import get_daily_achievement_message

from handlers.user_handlers import (
    start, button_callback, text_message_handler, send_reminder,
    add_task_handler, list_tasks_handler, done_task_handler,
    delete_task_handler, set_reminder_handler, list_reminders_handler,
    my_stats_handler,
)
from handlers.admin_handlers import (
    admin_panel, bot_stats, list_users, broadcast,
    ban_user_handler, unban_user_handler,
)
from handlers.ai_handlers import motivate_handler, study_session_handler

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  NIGHTLY SUMMARY JOB
# ═══════════════════════════════════════════════════════════════════════════════

async def send_nightly_summaries(context):
    users = get_users_with_tasks_today()
    logger.info(f"Nightly summary: {len(users)} user(s) active today.")
    for u in users:
        try:
            stats  = get_user_stats(u["user_id"])
            streak, _ = get_streak(u["user_id"])
            msg    = await get_daily_achievement_message(u["first_name"], stats["today"], streak)
            await context.bot.send_message(
                chat_id=u["user_id"],
                text=f"🌙 *Daily Achievement Summary*\n\n{msg}",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Nightly summary failed for {u['user_id']}: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  POST-INIT: restore reminders + schedule nightly summary
# ═══════════════════════════════════════════════════════════════════════════════

async def post_init(application):
    reminders = get_all_active_reminders()
    for r in reminders:
        hour, minute = map(int, r["remind_time"].split(":"))
        application.job_queue.run_daily(
            send_reminder,
            time=dt_time(hour=hour, minute=minute, tzinfo=TIMEZONE),
            data={
                "user_id":    r["user_id"],
                "task":       r["task"],
                "task_id":    r["task_id"],
                "reminder_id": r["id"],
            },
            name=f"reminder_{r['id']}",
        )
    logger.info(f"Restored {len(reminders)} reminder(s) from database.")

    application.job_queue.run_daily(
        send_nightly_summaries,
        time=dt_time(hour=22, minute=0, tzinfo=TIMEZONE),
        name="nightly_summary",
    )
    logger.info("Nightly summary scheduled at 22:00 (with local timezone).")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    init_db()
    logger.info("Database initialised.")

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # ── User commands ──────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",     start))
    app.add_handler(CommandHandler("add",       add_task_handler))
    app.add_handler(CommandHandler("list",      list_tasks_handler))
    app.add_handler(CommandHandler("done",      done_task_handler))
    app.add_handler(CommandHandler("delete",    delete_task_handler))
    app.add_handler(CommandHandler("remind",    set_reminder_handler))
    app.add_handler(CommandHandler("reminders", list_reminders_handler))
    app.add_handler(CommandHandler("mystats",   my_stats_handler))

    # ── AI commands ────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("motivate",  motivate_handler))
    app.add_handler(CommandHandler("study",     study_session_handler))

    # ── Admin commands ─────────────────────────────────────────────────────
    app.add_handler(CommandHandler("admin",     admin_panel))
    app.add_handler(CommandHandler("stats",     bot_stats))
    app.add_handler(CommandHandler("users",     list_users))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("ban",       ban_user_handler))
    app.add_handler(CommandHandler("unban",     unban_user_handler))

    # ── Inline buttons (all routes through button_callback) ────────────────
    app.add_handler(CallbackQueryHandler(button_callback))

    # ── Text messages (modes + free AI chat) ──────────────────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    logger.info("Bot is live! Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
