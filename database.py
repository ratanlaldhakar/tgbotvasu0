import sqlite3
from datetime import date, timedelta, datetime
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id    INTEGER PRIMARY KEY,
            username   TEXT,
            first_name TEXT,
            banned     INTEGER DEFAULT 0,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            user_task_num INTEGER DEFAULT 0,
            task          TEXT    NOT NULL,
            completed     INTEGER DEFAULT 0,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at  TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            task_id     INTEGER NOT NULL,
            remind_time TEXT    NOT NULL,
            active      INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)

    conn.commit()

    # ── Migration: add user_task_num if missing ──────────────────────────────
    try:
        conn.execute("ALTER TABLE tasks ADD COLUMN user_task_num INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass  # Column already exists

    # Backfill user_task_num for rows where it is 0
    rows = conn.execute(
        "SELECT id, user_id FROM tasks WHERE user_task_num = 0 ORDER BY id ASC"
    ).fetchall()
    counters = {}
    for row in rows:
        uid = row["user_id"]
        counters[uid] = counters.get(uid, 0) + 1
        conn.execute(
            "UPDATE tasks SET user_task_num = ? WHERE id = ?",
            (counters[uid], row["id"])
        )
    if rows:
        conn.commit()

    conn.close()


# ─── USER ────────────────────────────────────────────────────────────────────

def register_user(user_id: int, username: str, first_name: str):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
        (user_id, username, first_name),
    )
    conn.commit()
    conn.close()


def is_banned(user_id: int) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT banned FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return bool(row and row["banned"])


def get_all_users():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM users ORDER BY registered_at DESC").fetchall()
    conn.close()
    return rows


def ban_user(user_id: int):
    conn = get_connection()
    conn.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def unban_user(user_id: int):
    conn = get_connection()
    conn.execute("UPDATE users SET banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# ─── TASKS ───────────────────────────────────────────────────────────────────

def add_task(user_id: int, task_text: str) -> int:
    """Add a task and return the per-user task number."""
    conn = get_connection()
    row = conn.execute(
        "SELECT COALESCE(MAX(user_task_num), 0) + 1 FROM tasks WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    user_task_num = row[0]
    conn.execute(
        "INSERT INTO tasks (user_id, user_task_num, task) VALUES (?, ?, ?)",
        (user_id, user_task_num, task_text)
    )
    conn.commit()
    conn.close()
    return user_task_num


def get_tasks(user_id: int, include_completed: bool = False):
    conn = get_connection()
    if include_completed:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY user_task_num ASC", (user_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE user_id = ? AND completed = 0 ORDER BY user_task_num ASC",
            (user_id,),
        ).fetchall()
    conn.close()
    return rows


def get_task_by_user_num(user_task_num: int, user_id: int):
    """Get a task by per-user number (what users see)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM tasks WHERE user_task_num = ? AND user_id = ?",
        (user_task_num, user_id)
    ).fetchone()
    conn.close()
    return row


def get_task_by_id(task_id: int, user_id: int):
    """Get a task by internal DB id (used by reminders)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)
    ).fetchone()
    conn.close()
    return row


def complete_task(user_id: int, user_task_num: int) -> bool:
    conn = get_connection()
    cur = conn.execute(
        "UPDATE tasks SET completed = 1, completed_at = CURRENT_TIMESTAMP "
        "WHERE user_task_num = ? AND user_id = ? AND completed = 0",
        (user_task_num, user_id),
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def delete_task(user_id: int, user_task_num: int) -> bool:
    conn = get_connection()
    cur = conn.execute(
        "DELETE FROM tasks WHERE user_task_num = ? AND user_id = ?",
        (user_task_num, user_id)
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# ─── STATS & ACHIEVEMENTS ────────────────────────────────────────────────────

def get_user_stats(user_id: int) -> dict:
    conn = get_connection()
    total = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    completed = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completed = 1", (user_id,)
    ).fetchone()[0]
    today = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completed = 1 AND date(completed_at) = date('now')",
        (user_id,),
    ).fetchone()[0]
    week = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completed = 1 AND date(completed_at) >= date('now', '-6 days')",
        (user_id,),
    ).fetchone()[0]
    conn.close()
    return {"total": total, "completed": completed, "pending": total - completed, "today": today, "week": week}


def get_streak(user_id: int) -> tuple[int, int]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT date(completed_at) AS day FROM tasks "
        "WHERE user_id = ? AND completed = 1 ORDER BY day DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    if not rows:
        return 0, 0
    day_dates = [datetime.strptime(r["day"], "%Y-%m-%d").date() for r in rows]
    today = date.today()
    current = 0
    if day_dates[0] >= today - timedelta(days=1):
        current = 1
        for i in range(1, len(day_dates)):
            if day_dates[i - 1] - day_dates[i] == timedelta(days=1):
                current += 1
            else:
                break
    best, temp = 1, 1
    for i in range(1, len(day_dates)):
        if day_dates[i - 1] - day_dates[i] == timedelta(days=1):
            temp += 1
            best = max(best, temp)
        else:
            temp = 1
    return current, max(best, current)


def get_users_with_tasks_today():
    conn = get_connection()
    rows = conn.execute(
        """SELECT DISTINCT u.user_id, u.first_name FROM users u
           JOIN tasks t ON u.user_id = t.user_id
           WHERE t.completed = 1 AND date(t.completed_at) = date('now') AND u.banned = 0"""
    ).fetchall()
    conn.close()
    return rows


def get_bot_stats() -> dict:
    conn = get_connection()
    total_users    = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    active_users   = conn.execute("SELECT COUNT(*) FROM users WHERE banned = 0").fetchone()[0]
    total_tasks    = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    completed_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE completed = 1").fetchone()[0]
    conn.close()
    return {"total_users": total_users, "active_users": active_users,
            "total_tasks": total_tasks, "completed_tasks": completed_tasks}


# ─── REMINDERS ───────────────────────────────────────────────────────────────

def add_reminder(user_id: int, task_id: int, remind_time: str) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO reminders (user_id, task_id, remind_time) VALUES (?, ?, ?)",
        (user_id, task_id, remind_time),
    )
    reminder_id = cur.lastrowid
    conn.commit()
    conn.close()
    return reminder_id


def get_reminders(user_id: int):
    conn = get_connection()
    rows = conn.execute(
        """SELECT r.*, t.task FROM reminders r
           JOIN tasks t ON r.task_id = t.id
           WHERE r.user_id = ? AND r.active = 1 AND t.completed = 0""",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def get_all_active_reminders():
    conn = get_connection()
    rows = conn.execute(
        """SELECT r.*, t.task FROM reminders r
           JOIN tasks t ON r.task_id = t.id
           WHERE r.active = 1 AND t.completed = 0"""
    ).fetchall()
    conn.close()
    return rows


def deactivate_reminder(reminder_id: int):
    conn = get_connection()
    conn.execute("UPDATE reminders SET active = 0 WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()
