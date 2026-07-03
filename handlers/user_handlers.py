import re
from datetime import time as dt_time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from config import ADMIN_ID, TIMEZONE
from database import (
    register_user, is_banned,
    add_task, get_tasks, get_task_by_user_num, complete_task, delete_task,
    add_reminder, get_reminders, get_user_stats, get_streak,
)

class SafeQueryWrapper:
    def __init__(self, query):
        object.__setattr__(self, "_query", query)

    def __getattr__(self, name):
        return getattr(self._query, name)

    def __setattr__(self, name, value):
        return setattr(self._query, name, value)

    async def edit_message_text(self, *args, **kwargs):
        try:
            return await self._query.edit_message_text(*args, **kwargs)
        except BadRequest as e:
            if "Message is not modified" in str(e):
                return
            raise e

_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


# ═══════════════════════════════════════════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════════════════════════════════════════

def main_menu_kb(user_id: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("📋 My Tasks",   callback_data="my_tasks"),
            InlineKeyboardButton("➕ Add Task",    callback_data="add_task"),
        ],
        [
            InlineKeyboardButton("📊 My Stats",   callback_data="my_stats"),
            InlineKeyboardButton("⏰ Reminders",   callback_data="reminders"),
        ],
        [
            InlineKeyboardButton("📚 Study Plan",  callback_data="study"),
            InlineKeyboardButton("💪 Motivate Me", callback_data="motivate"),
        ],
        [
            InlineKeyboardButton("🤖 Chat with AI", callback_data="chat_mode"),
        ],
    ]
    if user_id == ADMIN_ID:
        rows.append([InlineKeyboardButton("🔐 Admin Panel", callback_data="admin")])
    return InlineKeyboardMarkup(rows)


def tasks_kb(tasks) -> InlineKeyboardMarkup:
    rows = []
    for t in tasks:
        n = t["user_task_num"]
        label = t["task"][:22] + "…" if len(t["task"]) > 22 else t["task"]
        rows.append([InlineKeyboardButton(f"#{n} — {label}", callback_data=f"noop")])
        rows.append([
            InlineKeyboardButton("✅ Done",   callback_data=f"done_{n}"),
            InlineKeyboardButton("🗑️ Delete", callback_data=f"del_{n}"),
            InlineKeyboardButton("⏰ Remind", callback_data=f"rmnd_{n}"),
        ])
    rows.append([
        InlineKeyboardButton("➕ Add Task",  callback_data="add_task"),
        InlineKeyboardButton("🏠 Menu",      callback_data="menu"),
    ])
    return InlineKeyboardMarkup(rows)


def back_kb(target="menu", label="🏠 Main Menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=target)]])


def cancel_kb(target="menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=target)]])


# ═══════════════════════════════════════════════════════════════════════════════
#  GUARD
# ═══════════════════════════════════════════════════════════════════════════════

async def _guard_msg(update: Update) -> bool:
    u = update.effective_user
    register_user(u.id, u.username, u.first_name)
    if is_banned(u.id):
        await update.message.reply_text("❌ You are banned from using this bot.")
        return True
    return False


async def _guard_cb(query, user) -> bool:
    register_user(user.id, user.username, user.first_name)
    if is_banned(user.id):
        await query.answer("❌ You are banned.", show_alert=True)
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
#  BADGE HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def _badges(completed: int, streak: int, today: int) -> list[str]:
    b = []
    if completed >= 1:   b.append("🥉 First Task")
    if completed >= 10:  b.append("🥈 Task Warrior")
    if completed >= 50:  b.append("🥇 Task Master")
    if completed >= 100: b.append("💎 Legend")
    if streak >= 3:      b.append("🔥 On Fire")
    if streak >= 7:      b.append("⚡ Week Warrior")
    if streak >= 30:     b.append("🌟 Monthly Champion")
    if today >= 5:       b.append("🚀 Superstar Day")
    return b


# ═══════════════════════════════════════════════════════════════════════════════
#  /start
# ═══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _guard_msg(update):
        return
    user = update.effective_user
    await update.message.reply_text(
        f"👋 *Hey {user.first_name}!* Welcome to your *AI Productivity Bot* 🚀\n\n"
        "Powered by *Gemini 2.5 Flash* — I help you:\n"
        "  ✅  Manage your to-do list\n"
        "  ⏰  Set smart daily reminders\n"
        "  📚  Get personalized study plans\n"
        "  💪  Stay motivated every day\n"
        "  🏆  Track streaks & earn badges\n\n"
        "👇 *Pick an option to get started:*",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(user.id),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  MASTER CALLBACK HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = SafeQueryWrapper(update.callback_query)
    await query.answer()
    user  = update.effective_user

    if await _guard_cb(query, user):
        return

    data = query.data

    # ── Noop (task label rows) ─────────────────────────────────────────────
    if data == "noop":
        return

    # ── Admin callbacks → delegate ─────────────────────────────────────────
    if data.startswith("admin"):
        from handlers.admin_handlers import handle_admin_callback
        await handle_admin_callback(update, context)
        return

    # ── Main menu ──────────────────────────────────────────────────────────
    if data == "menu":
        await query.edit_message_text(
            f"🏠 *Main Menu*\n\n_What would you like to do, {user.first_name}?_",
            parse_mode="Markdown",
            reply_markup=main_menu_kb(user.id),
        )

    # ── Task list ──────────────────────────────────────────────────────────
    elif data == "my_tasks":
        await _show_tasks(query, user)

    # ── Add task ──────────────────────────────────────────────────────────
    elif data == "add_task":
        context.user_data["mode"] = "add_task"
        await query.edit_message_text(
            "➕ *Add a New Task*\n\n📝 Just type your task and send it:",
            parse_mode="Markdown",
            reply_markup=cancel_kb("menu"),
        )

    # ── Stats ─────────────────────────────────────────────────────────────
    elif data == "my_stats":
        await _show_stats(query, user)

    # ── Reminders ─────────────────────────────────────────────────────────
    elif data == "reminders":
        await _show_reminders(query, user)

    # ── Study plan ────────────────────────────────────────────────────────
    elif data == "study":
        await query.edit_message_text("📚 _Building your study plan…_", parse_mode="Markdown")
        from gemini import get_study_plan
        try:
            tasks = [dict(t) for t in get_tasks(user.id)]
            plan  = await get_study_plan(tasks)
            await query.edit_message_text(
                f"📚 *Your Study Plan:*\n\n{plan}",
                parse_mode="Markdown",
                reply_markup=back_kb(),
            )
        except Exception:
            await query.edit_message_text("❌ Couldn't generate plan. Try again!", reply_markup=back_kb())

    # ── Motivate ──────────────────────────────────────────────────────────
    elif data == "motivate":
        await query.edit_message_text("✨ _Crafting your motivation boost…_", parse_mode="Markdown")
        from gemini import get_motivation
        try:
            quote = await get_motivation()
            await query.edit_message_text(
                f"💪 *Your Motivation:*\n\n{quote}",
                parse_mode="Markdown",
                reply_markup=back_kb(),
            )
        except Exception:
            await query.edit_message_text("❌ Couldn't reach AI. Try again!", reply_markup=back_kb())

    # ── Chat mode ─────────────────────────────────────────────────────────
    elif data == "chat_mode":
        context.user_data["mode"] = "chat"
        await query.edit_message_text(
            "🤖 *Chat with Gemini AI*\n\n_Ask me anything! I'm listening…_",
            parse_mode="Markdown",
            reply_markup=cancel_kb("menu"),
        )

    # ── Done task ─────────────────────────────────────────────────────────
    elif data.startswith("done_"):
        num = int(data.split("_", 1)[1])
        task = get_task_by_user_num(num, user.id)
        if not task:
            await query.answer("❌ Task not found!", show_alert=True); return
        if task["completed"]:
            await query.answer("✅ Already done!", show_alert=True); return
        success = complete_task(user.id, num)
        if success:
            stats  = get_user_stats(user.id)
            streak, _ = get_streak(user.id)
            streak_ln = f"\n🔥 *{streak}-day streak!*" if streak > 1 else ""
            # Achievement unlock
            ach = ""
            if stats["completed"] == 1:   ach = "\n🥉 *Achievement: First Task!*"
            elif stats["completed"] == 10: ach = "\n🥈 *Achievement: Task Warrior!*"
            elif stats["completed"] == 50: ach = "\n🥇 *Achievement: Task Master!*"
            elif stats["today"] == 5:      ach = "\n🚀 *Achievement: Superstar Day!*"
            await query.answer("🎉 Task complete!", show_alert=False)
            await _show_tasks(
                query, user,
                banner=f"✅ *Done!* _{task['task']}_\n📅 Today: *{stats['today']}* task(s){streak_ln}{ach}"
            )
        else:
            await query.answer("❌ Error completing task.", show_alert=True)

    # ── Delete task ───────────────────────────────────────────────────────
    elif data.startswith("del_"):
        num  = int(data.split("_", 1)[1])
        task = get_task_by_user_num(num, user.id)
        if not task:
            await query.answer("❌ Task not found!", show_alert=True); return
        delete_task(user.id, num)
        await query.answer("🗑️ Deleted!", show_alert=False)
        await _show_tasks(query, user, banner=f"🗑️ Deleted: _{task['task']}_")

    # ── Remind task ───────────────────────────────────────────────────────
    elif data.startswith("rmnd_"):
        num  = int(data.split("_", 1)[1])
        task = get_task_by_user_num(num, user.id)
        if not task:
            await query.answer("❌ Task not found!", show_alert=True); return
        context.user_data.update({"mode": "set_reminder", "remind_task_num": num, "remind_task": task["task"]})
        await query.edit_message_text(
            f"⏰ *Set a Daily Reminder*\n\n📌 _{task['task']}_\n\n"
            "Send me the time in *HH:MM* format (24-hour)\nExample: `18:30`",
            parse_mode="Markdown",
            reply_markup=cancel_kb("my_tasks"),
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  INLINE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

async def _show_tasks(query, user, banner: str = ""):
    tasks = get_tasks(user.id)
    if not tasks:
        text = (
            f"{banner}\n\n" if banner else ""
        ) + "📭 *No pending tasks!*\n\nYour plate is clean 🎉 — tap *Add Task* to start!"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Task", callback_data="add_task")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
        ])
    else:
        header = (f"{banner}\n\n" if banner else "") + "📋 *Your To-Do List:*\n"
        lines  = [header]
        for t in tasks:
            lines.append(f"🔹 *#{t['user_task_num']}* — {t['task']}")
        lines.append(f"\n_📊 {len(tasks)} pending_  |  ✅=Done  🗑️=Delete  ⏰=Remind")
        text = "\n".join(lines)
        kb   = tasks_kb(tasks)
    try:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    except Exception:
        pass


async def _show_stats(query, user):
    stats  = get_user_stats(user.id)
    streak, best = get_streak(user.id)
    rate   = (stats["completed"] / stats["total"] * 100) if stats["total"] else 0
    filled = int(rate / 10)
    bar    = "█" * filled + "░" * (10 - filled)
    badge_list = _badges(stats["completed"], streak, stats["today"])
    badge_line = ("\n\n🎖️ *Your Badges:*\n" + "  ".join(badge_list)) if badge_list else ""
    msg = (
        f"📊 *Achievement Stats — {user.first_name}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📅 *Today:*      {stats['today']} task(s)\n"
        f"📆 *This Week:*  {stats['week']} task(s)\n"
        f"✅ *All Time:*   {stats['completed']} completed\n"
        f"🔸 *Pending:*    {stats['pending']} task(s)\n\n"
        f"📈 *Completion:* `{bar}` {rate:.0f}%\n\n"
        f"🔥 *Streak:*     {streak} day(s)\n"
        f"🏆 *Best:*       {best} day(s)"
        f"{badge_line}\n\n_Keep it up, {user.first_name}!_ 💪"
    )
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_kb())


async def _show_reminders(query, user):
    reminders = get_reminders(user.id)
    if not reminders:
        text = "📭 *No active reminders.*\n\nOpen your tasks and tap ⏰ on one to set a reminder!"
    else:
        lines = ["⏰ *Your Daily Reminders:*\n"]
        for r in reminders:
            lines.append(f"🔔 *{r['remind_time']}* — _{r['task']}_")
        text = "\n".join(lines)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_kb())


# ═══════════════════════════════════════════════════════════════════════════════
#  TEXT MESSAGE HANDLER (handles modes + free AI chat)
# ═══════════════════════════════════════════════════════════════════════════════

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user.id, user.username, user.first_name)
    if is_banned(user.id):
        return

    # Let admin handler grab it first if in admin mode
    from handlers.admin_handlers import handle_admin_text
    if await handle_admin_text(update, context):
        return

    text = update.message.text.strip()
    mode = context.user_data.get("mode")

    # ── Add task mode ──────────────────────────────────────────────────────
    if mode == "add_task":
        context.user_data.pop("mode")
        task_num = add_task(user.id, text)
        await update.message.reply_text(
            f"✅ *Task #{task_num} Added!*\n\n📌 _{text}_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 My Tasks", callback_data="my_tasks"),
                 InlineKeyboardButton("➕ Add More",  callback_data="add_task")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
            ]),
        )

    # ── Set reminder mode ─────────────────────────────────────────────────
    elif mode == "set_reminder":
        if not _TIME_RE.match(text):
            await update.message.reply_text(
                "❌ Invalid format. Use *HH:MM* e.g. `18:30`. Try again:",
                parse_mode="Markdown",
            )
            return  # keep mode active
        task_num  = context.user_data.pop("remind_task_num", None)
        task_name = context.user_data.pop("remind_task", "")
        context.user_data.pop("mode")
        task = get_task_by_user_num(task_num, user.id)
        if task:
            hour, minute = map(int, text.split(":"))
            rid = add_reminder(user.id, task["id"], text)
            context.job_queue.run_daily(
                send_reminder,
                time=dt_time(hour=hour, minute=minute, tzinfo=TIMEZONE),
                data={"user_id": user.id, "task": task_name, "task_id": task["id"], "reminder_id": rid},
                name=f"reminder_{rid}",
            )
            await update.message.reply_text(
                f"⏰ *Reminder Set!*\n\n📌 _{task_name}_\n🕐 Every day at *{text}*",
                parse_mode="Markdown",
                reply_markup=back_kb("my_tasks", "📋 Back to Tasks"),
            )
        else:
            await update.message.reply_text("❌ Task not found.", reply_markup=back_kb())

    # ── Chat mode or free text → AI ───────────────────────────────────────
    else:
        from gemini import chat
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        try:
            reply = await chat(text, user.first_name)
            await update.message.reply_text(
                f"🤖 {reply}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")]
                ]),
            )
        except Exception:
            await update.message.reply_text("❌ AI is taking a break. Try again!")


# ═══════════════════════════════════════════════════════════════════════════════
#  REMINDER JOB
# ═══════════════════════════════════════════════════════════════════════════════

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    await context.bot.send_message(
        chat_id=data["user_id"],
        text=(
            f"⏰ *Daily Reminder!*\n\n📌 _{data['task']}_\n\nYou've got this! 💪"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Open Tasks", callback_data="my_tasks")]
        ]),
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  LEGACY COMMAND HANDLERS (still supported)
# ═══════════════════════════════════════════════════════════════════════════════

async def add_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _guard_msg(update):
        return
    if not context.args:
        context.user_data["mode"] = "add_task"
        await update.message.reply_text(
            "➕ *What's your new task?* Type it below:",
            parse_mode="Markdown",
            reply_markup=cancel_kb(),
        )
        return
    task_num = add_task(update.effective_user.id, " ".join(context.args))
    await update.message.reply_text(
        f"✅ *Task #{task_num} Added!*",
        parse_mode="Markdown",
        reply_markup=back_kb("my_tasks", "📋 View Tasks"),
    )


async def list_tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _guard_msg(update):
        return
    user  = update.effective_user
    tasks = get_tasks(user.id)
    if not tasks:
        await update.message.reply_text(
            "📭 *No pending tasks!*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Task",   callback_data="add_task")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")],
            ]),
        )
        return
    lines = ["📋 *Your To-Do List:*\n"]
    for t in tasks:
        lines.append(f"🔹 *#{t['user_task_num']}* — {t['task']}")
    lines.append(f"\n_📊 {len(tasks)} pending_")
    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=tasks_kb(tasks)
    )


async def done_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _guard_msg(update):
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❌ Usage: /done `<task_number>`", parse_mode="Markdown")
        return
    user = update.effective_user
    num  = int(context.args[0])
    task = get_task_by_user_num(num, user.id)
    if not task:
        await update.message.reply_text("❌ Task not found. Use /list to see your tasks.")
        return
    if task["completed"]:
        await update.message.reply_text("✅ Already completed!")
        return
    complete_task(user.id, num)
    stats  = get_user_stats(user.id)
    streak, _ = get_streak(user.id)
    await update.message.reply_text(
        f"🎉 *Done!* _{task['task']}_\n📅 Today: *{stats['today']}*  🔥 Streak: *{streak}* days",
        parse_mode="Markdown",
        reply_markup=back_kb("my_tasks", "📋 My Tasks"),
    )


async def delete_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _guard_msg(update):
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❌ Usage: /delete `<task_number>`", parse_mode="Markdown")
        return
    user = update.effective_user
    num  = int(context.args[0])
    task = get_task_by_user_num(num, user.id)
    if not task:
        await update.message.reply_text("❌ Task not found.")
        return
    delete_task(user.id, num)
    await update.message.reply_text(f"🗑️ Deleted: _{task['task']}_", parse_mode="Markdown", reply_markup=back_kb())


async def set_reminder_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _guard_msg(update):
        return
    if len(context.args) < 2 or not context.args[0].isdigit():
        await update.message.reply_text("❌ Usage: /remind `<task_num> <HH:MM>`", parse_mode="Markdown")
        return
    user     = update.effective_user
    num      = int(context.args[0])
    time_str = context.args[1]
    if not _TIME_RE.match(time_str):
        await update.message.reply_text("❌ Use HH:MM format, e.g. `18:30`", parse_mode="Markdown")
        return
    task = get_task_by_user_num(num, user.id)
    if not task:
        await update.message.reply_text("❌ Task not found.")
        return
    hour, minute = map(int, time_str.split(":"))
    rid = add_reminder(user.id, task["id"], time_str)
    context.job_queue.run_daily(
        send_reminder,
        time=dt_time(hour=hour, minute=minute, tzinfo=TIMEZONE),
        data={"user_id": user.id, "task": task["task"], "task_id": task["id"], "reminder_id": rid},
        name=f"reminder_{rid}",
    )
    await update.message.reply_text(
        f"⏰ *Reminder set!* Daily at *{time_str}* for:\n_{task['task']}_",
        parse_mode="Markdown",
        reply_markup=back_kb(),
    )


async def list_reminders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _guard_msg(update):
        return
    reminders = get_reminders(update.effective_user.id)
    if not reminders:
        await update.message.reply_text("📭 No active reminders.", reply_markup=back_kb())
        return
    lines = ["⏰ *Your Reminders:*\n"]
    for r in reminders:
        lines.append(f"🔔 *{r['remind_time']}* — _{r['task']}_")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=back_kb())


async def my_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _guard_msg(update):
        return
    user   = update.effective_user
    stats  = get_user_stats(user.id)
    streak, best = get_streak(user.id)
    rate   = (stats["completed"] / stats["total"] * 100) if stats["total"] else 0
    bar    = "█" * int(rate / 10) + "░" * (10 - int(rate / 10))
    badge_list = _badges(stats["completed"], streak, stats["today"])
    badge_line = ("\n\n🎖️ *Badges:* " + "  ".join(badge_list)) if badge_list else ""
    await update.message.reply_text(
        f"📊 *Stats — {user.first_name}*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📅 *Today:*     {stats['today']} task(s)\n"
        f"📆 *This Week:* {stats['week']} task(s)\n"
        f"✅ *All Time:*  {stats['completed']} completed\n"
        f"🔸 *Pending:*   {stats['pending']}\n\n"
        f"📈 `{bar}` {rate:.0f}%\n\n"
        f"🔥 *Streak:* {streak} days  🏆 *Best:* {best} days"
        f"{badge_line}\n\n_Keep going!_ 💪",
        parse_mode="Markdown",
        reply_markup=back_kb(),
    )
