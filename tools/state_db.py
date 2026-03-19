"""
SQLite state persistence para el scheduler.
Evita duplicados de noticias, trackea tweets generados y alertas.
DB en data/scheduler_state.db.
"""
import sqlite3
import json
from datetime import date, datetime
from pathlib import Path

from config.settings import DB_PATH


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Crea las tablas si no existen."""
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS processed_news (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            url         TEXT UNIQUE NOT NULL,
            ticker      TEXT NOT NULL,
            title       TEXT NOT NULL,
            summary     TEXT DEFAULT '',
            pub_date    TEXT DEFAULT '',
            fetched_at  TEXT NOT NULL,
            interest_score INTEGER DEFAULT 0,
            tweeted     INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS generated_tweets (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id       INTEGER,
            ticker        TEXT NOT NULL,
            content_type  TEXT DEFAULT 'news',
            tweets_json   TEXT NOT NULL,
            file_path     TEXT DEFAULT '',
            generated_at  TEXT NOT NULL,
            FOREIGN KEY (news_id) REFERENCES processed_news(id)
        );

        CREATE TABLE IF NOT EXISTS alerts_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type  TEXT NOT NULL,
            ticker      TEXT DEFAULT '',
            message     TEXT NOT NULL,
            logged_at   TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_news_url ON processed_news(url);
        CREATE INDEX IF NOT EXISTS idx_news_score ON processed_news(interest_score);
        CREATE INDEX IF NOT EXISTS idx_news_tweeted ON processed_news(tweeted);
        CREATE INDEX IF NOT EXISTS idx_tweets_date ON generated_tweets(generated_at);
        CREATE INDEX IF NOT EXISTS idx_alerts_date ON alerts_log(logged_at);
    """)
    conn.close()


# ─── Noticias ────────────────────────────────────────────────────────────────────

def is_news_processed(url: str) -> bool:
    conn = _connect()
    row = conn.execute("SELECT 1 FROM processed_news WHERE url = ?", (url,)).fetchone()
    conn.close()
    return row is not None


def mark_news_processed(
    url: str, ticker: str, title: str,
    summary: str = "", pub_date: str = "",
) -> int | None:
    """Inserta noticia. Devuelve id si nueva, None si duplicada."""
    conn = _connect()
    try:
        cur = conn.execute(
            """INSERT INTO processed_news (url, ticker, title, summary, pub_date, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (url, ticker, title, summary, pub_date, datetime.now().isoformat()),
        )
        conn.commit()
        news_id = cur.lastrowid
    except sqlite3.IntegrityError:
        news_id = None
    conn.close()
    return news_id


def update_news_score(news_id: int, score: int):
    conn = _connect()
    conn.execute(
        "UPDATE processed_news SET interest_score = ? WHERE id = ?",
        (score, news_id),
    )
    conn.commit()
    conn.close()


def mark_news_tweeted(news_id: int):
    conn = _connect()
    conn.execute(
        "UPDATE processed_news SET tweeted = 1 WHERE id = ?",
        (news_id,),
    )
    conn.commit()
    conn.close()


def get_unscored_news() -> list[dict]:
    """Noticias sin puntuar (interest_score = 0)."""
    conn = _connect()
    rows = conn.execute(
        "SELECT id, ticker, title, summary FROM processed_news WHERE interest_score = 0"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_best_untweeted_news(min_score: int = 6) -> dict | None:
    """Mejor noticia no tuiteada con score >= min_score."""
    conn = _connect()
    row = conn.execute(
        """SELECT id, ticker, title, summary, interest_score
           FROM processed_news
           WHERE tweeted = 0 AND interest_score >= ?
           ORDER BY interest_score DESC, fetched_at DESC
           LIMIT 1""",
        (min_score,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ─── Tweets ──────────────────────────────────────────────────────────────────────

def save_generated_tweets(
    ticker: str, tweets: list[str],
    file_path: str = "", news_id: int | None = None,
    content_type: str = "news",
):
    conn = _connect()
    conn.execute(
        """INSERT INTO generated_tweets (news_id, ticker, content_type, tweets_json, file_path, generated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (news_id, ticker, content_type, json.dumps(tweets, ensure_ascii=False),
         file_path, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_today_tweet_count() -> int:
    today = date.today().isoformat()
    conn = _connect()
    row = conn.execute(
        "SELECT COUNT(*) FROM generated_tweets WHERE generated_at LIKE ?",
        (f"{today}%",),
    ).fetchone()
    conn.close()
    return row[0] if row else 0


# ─── Alertas ─────────────────────────────────────────────────────────────────────

def log_alert(alert_type: str, ticker: str, message: str):
    conn = _connect()
    conn.execute(
        "INSERT INTO alerts_log (alert_type, ticker, message, logged_at) VALUES (?, ?, ?, ?)",
        (alert_type, ticker, message, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_today_alerts() -> list[dict]:
    today = date.today().isoformat()
    conn = _connect()
    rows = conn.execute(
        "SELECT alert_type, ticker, message, logged_at FROM alerts_log WHERE logged_at LIKE ?",
        (f"{today}%",),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Stats ───────────────────────────────────────────────────────────────────────

def get_news_stats(days: int = 7) -> dict:
    """Estadísticas de noticias procesadas en los últimos N días."""
    conn = _connect()
    total = conn.execute(
        "SELECT COUNT(*) FROM processed_news WHERE fetched_at >= date('now', ?)",
        (f"-{days} days",),
    ).fetchone()[0]
    scored = conn.execute(
        "SELECT COUNT(*) FROM processed_news WHERE interest_score > 0 AND fetched_at >= date('now', ?)",
        (f"-{days} days",),
    ).fetchone()[0]
    high_score = conn.execute(
        "SELECT COUNT(*) FROM processed_news WHERE interest_score >= 6 AND fetched_at >= date('now', ?)",
        (f"-{days} days",),
    ).fetchone()[0]
    tweeted = conn.execute(
        "SELECT COUNT(*) FROM processed_news WHERE tweeted = 1 AND fetched_at >= date('now', ?)",
        (f"-{days} days",),
    ).fetchone()[0]
    tweets_today = get_today_tweet_count()
    alerts_today = len(get_today_alerts())
    conn.close()

    return {
        "period_days": days,
        "total_news": total,
        "scored_news": scored,
        "high_interest": high_score,
        "tweeted": tweeted,
        "tweets_today": tweets_today,
        "alerts_today": alerts_today,
    }
