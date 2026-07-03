from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from config import ADMIN_ID
from database import get_all_users, ban_user, unban_user, get_bot_stats

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


def _is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ═══════════════════════════════════════════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════════════════════════════════════════

def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Statistics",  callback_data="admin_stats"),
            InlineKeyboardButton("👥 Users",        callback_data="admin_users"),
        ],
        [
            InlineKeyboardButton("📢 Broadcast",   callback_data="admin_broadcast"),
        ],
        [InlineKeyboardButton("🏠 Main Menu",      callback_data="menu")],
    ])


def back_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Admin Panel", callback_data="admin")]])


# ═══════════════════════════════════════════════════════════════════════════════
#  CALLBACK HANDLER (called from user_handlers.button_callback)
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = SafeQueryWrapper(update.callback_query)
    user  = update.effective_user

    if not _is_admin(user.id):
        await query.answer("❌ Admin access only.", show_alert=True)
        return

    data = query.data

    # ── Admin home ─────────────────────────────────────────────────────────
    if data == "admin":
        await query.edit_message_text(
            "🔐 *Admin Panel*\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Welcome back, *{user.first_name}*!\nChoose an action below:",
            parse_mode="Markdown",
            reply_markup=admin_kb(),
        )

    # ── Statistics ────────────────────────────────────────────────────────
    elif data == "admin_stats":
        s    = get_bot_stats()
        rate = f"{s['completed_tasks'] / s['total_tasks'] * 100:.0f}%" if s["total_tasks"] else "N/A"
        await query.edit_message_text(
            "📊 *Bot Statistics*\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 Total Users:     *{s['total_users']}*\n"
            f"✅ Active Users:    *{s['active_users']}*\n"
            f"🚫 Banned:          *{s['total_users'] - s['active_users']}*\n"
            f"📋 Total Tasks:     *{s['total_tasks']}*\n"
            f"✔️  Completed:       *{s['completed_tasks']}*\n"
            f"📈 Completion Rate: *{rate}*",
            parse_mode="Markdown",
            reply_markup=back_admin_kb(),
        )

    # ── User list ─────────────────────────────────────────────────────────
    elif data == "admin_users":
        users = get_all_users()
        lines = [f"👥 *All Users ({len(users)}):*\n"]
        for u in users[:25]:
            uname  = f"@{u['username']}" if u["username"] else "—"
            status = "🚫" if u["banned"] else "✅"
            lines.append(f"{status} `{u['user_id']}` — *{u['first_name']}* ({uname})")
        if len(users) > 25:
            lines.append(f"\n_...and {len(users) - 25} more_")
        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=back_admin_kb(),
        )

    # ── Broadcast prompt ──────────────────────────────────────────────────
    elif data == "admin_broadcast":
        context.user_data["mode"] = "admin_broadcast"
        await query.edit_message_text(
            "📢 *Broadcast Message*\n\n"
            "Type your message below and it will be sent to *all users*:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin")]]),
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  TEXT HANDLER (called from combined text handler in bot.py)
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle admin text input modes. Returns True if handled."""
    user = update.effective_user
    mode = context.user_data.get("mode")

    if mode == "admin_broadcast" and _is_admin(user.id):
        context.user_data.pop("mode")
        message = update.message.text
        users   = get_all_users()
        sent = failed = 0
        status = await update.message.reply_text(f"📢 Sending to {len(users)} users…")
        for u in users:
            if u["banned"]:
                continue
            try:
                await context.bot.send_message(
                    chat_id=u["user_id"],
                    text=f"📢 *Announcement:*\n\n{message}",
                    parse_mode="Markdown",
                )
                sent += 1
            except Exception:
                failed += 1
        await status.edit_text(
            f"✅ *Broadcast Complete!*\n\n✔️ Sent: *{sent}*\n❌ Failed: *{failed}*",
            parse_mode="Markdown",
            reply_markup=back_admin_kb(),
        )
        return True

    return False


# ═══════════════════════════════════════════════════════════════════════════════
#  COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not _is_admin(user.id):
        await update.message.reply_text("❌ Admin access only.")
        return
    await update.message.reply_text(
        f"🔐 *Admin Panel*\n━━━━━━━━━━━━━━━━━━━━\n\nWelcome, *{user.first_name}*!",
        parse_mode="Markdown",
        reply_markup=admin_kb(),
    )


async def bot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access only.")
        return
    s    = get_bot_stats()
    rate = f"{s['completed_tasks'] / s['total_tasks'] * 100:.0f}%" if s["total_tasks"] else "N/A"
    await update.message.reply_text(
        "📊 *Bot Statistics*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Total Users:     *{s['total_users']}*\n"
        f"✅ Active Users:    *{s['active_users']}*\n"
        f"📋 Total Tasks:     *{s['total_tasks']}*\n"
        f"✔️  Completed:       *{s['completed_tasks']}*\n"
        f"📈 Completion Rate: *{rate}*",
        parse_mode="Markdown",
        reply_markup=admin_kb(),
    )


async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access only.")
        return
    users = get_all_users()
    lines = [f"👥 *All Users ({len(users)}):*\n"]
    for u in users[:25]:
        uname  = f"@{u['username']}" if u["username"] else "—"
        status = "🚫" if u["banned"] else "✅"
        lines.append(f"{status} `{u['user_id']}` — *{u['first_name']}* ({uname})")
    if len(users) > 25:
        lines.append(f"\n_...and {len(users) - 25} more_")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("❌ Usage: /broadcast `<message>`", parse_mode="Markdown")
        return
    message = " ".join(context.args)
    users   = get_all_users()
    sent = failed = 0
    status = await update.message.reply_text(f"📢 Sending to {len(users)} users…")
    for u in users:
        if u["banned"]:
            continue
        try:
            await context.bot.send_message(
                chat_id=u["user_id"],
                text=f"📢 *Announcement:*\n\n{message}",
                parse_mode="Markdown",
            )
            sent += 1
        except Exception:
            failed += 1
    await status.edit_text(
        f"✅ *Broadcast Complete!*\n\n✔️ Sent: *{sent}*\n❌ Failed: *{failed}*",
        parse_mode="Markdown",
    )


async def ban_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❌ Usage: /ban `<user_id>`", parse_mode="Markdown")
        return
    target_id = int(context.args[0])
    if target_id == ADMIN_ID:
        await update.message.reply_text("❌ You cannot ban yourself.")
        return
    ban_user(target_id)
    await update.message.reply_text(f"🚫 User `{target_id}` has been *banned*.", parse_mode="Markdown")


async def unban_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❌ Usage: /unban `<user_id>`", parse_mode="Markdown")
        return
    target_id = int(context.args[0])
    unban_user(target_id)
    await update.message.reply_text(f"✅ User `{target_id}` has been *unbanned*.", parse_mode="Markdown")
