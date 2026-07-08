# main.py
# AI Study Telegram Bot — Complete Production Implementation
# Python 3.13+ | python-telegram-bot v22+ | Firebase | Google Gemini

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import math
import os
import random
import re
import sys
import time
import traceback
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Optional

import aiohttp
import firebase_admin
from firebase_admin import credentials, db as firebase_db
from google import genai
from google.genai import types as genai_types
from telegram import (
    BotCommand,
    CallbackQuery,
    Chat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ChatAction, ParseMode
from telegram.error import Forbidden, TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    filters,
    MessageHandler,
)

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("StudyBot")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT VARIABLES
# ─────────────────────────────────────────────────────────────────────────────

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
GOOGLE_API_KEY: str = os.environ["GOOGLE_API_KEY"]
FIREBASE_DATABASE_URL: str = os.environ["FIREBASE_DATABASE_URL"]
FIREBASE_PROJECT_ID: str = os.environ["FIREBASE_PROJECT_ID"]
FIREBASE_CLIENT_EMAIL: str = os.environ["FIREBASE_CLIENT_EMAIL"]
FIREBASE_PRIVATE_KEY: str = os.environ["FIREBASE_PRIVATE_KEY"].replace("\\n", "\n")
OWNER_ID: int = int(os.environ["OWNER_ID"])
CHANNEL_USERNAME: str = os.environ.get("CHANNEL_USERNAME", "")

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

BOT_VERSION = "2.0.0"
MAX_MESSAGE_LENGTH = 4096
RATE_LIMIT_CALLS = 5
RATE_LIMIT_PERIOD = 10  # seconds
CONVERSATION_HISTORY_LIMIT = 10
AI_MODEL = "gemini-2.5-flash"

# Conversation states
(
    STATE_AI_CHAT,
    STATE_STUDY_CHAPTER,
    STATE_STUDY_SUMMARY,
    STATE_STUDY_MCQ,
    STATE_NOTE_CREATE,
    STATE_NOTE_EDIT,
    STATE_NOTE_SEARCH,
    STATE_NOTE_DELETE,
    STATE_MATH_SOLVE,
    STATE_TRANSLATE_TEXT,
    STATE_TRANSLATE_LANG,
    STATE_QUIZ_TOPIC,
    STATE_QUIZ_ANSWER,
    STATE_PDF_WAIT,
    STATE_EXAM_NAME,
    STATE_EXAM_DATE,
    STATE_PLANNER_TOPIC,
    STATE_PLANNER_DAYS,
    STATE_BROADCAST,
    STATE_BAN_USER,
    STATE_UNBAN_USER,
    STATE_OCR_QUESTION,
    STATE_ESSAY_TOPIC,
    STATE_LETTER_TOPIC,
    STATE_CODE_REQUEST,
    STATE_GRAMMAR_FIX,
    STATE_REWRITE_TEXT,
    STATE_SUMMARIZE_TEXT,
    STATE_STORY_TOPIC,
    STATE_FLASHCARD_TOPIC,
) = range(30)

# Emoji constants
EMOJI = {
    "home": "🏠",
    "ai": "🤖",
    "study": "📚",
    "notes": "📝",
    "pdf": "📄",
    "math": "🧮",
    "quiz": "🧠",
    "translate": "🌐",
    "profile": "👤",
    "settings": "⚙",
    "back": "⬅",
    "close": "❌",
    "check": "✅",
    "star": "⭐",
    "fire": "🔥",
    "trophy": "🏆",
    "book": "📖",
    "pencil": "✏️",
    "bulb": "💡",
    "rocket": "🚀",
    "crown": "👑",
    "gem": "💎",
    "chart": "📊",
    "clock": "🕐",
    "bell": "🔔",
    "lock": "🔒",
    "info": "ℹ️",
    "warn": "⚠️",
    "err": "🚫",
    "loading": "⏳",
    "done": "✨",
    "pin": "📌",
    "trash": "🗑️",
    "search": "🔍",
    "edit": "✏️",
    "save": "💾",
    "link": "🔗",
    "medal": "🎖️",
    "calendar": "📅",
    "target": "🎯",
    "code": "💻",
    "lang": "🌍",
    "img": "🖼️",
    "fav": "❤️",
    "streak": "🔥",
    "new": "🆕",
    "user": "👤",
    "admin": "🛡️",
    "ban": "🔨",
    "broadcast": "📢",
    "stats": "📈",
    "restart": "🔄",
    "maintenance": "🔧",
    "log": "📋",
}

LOADING_MESSAGES = [
    "⏳ Processing your request...",
    "🤔 Thinking carefully...",
    "🔍 Analyzing information...",
    "💡 Generating response...",
    "📚 Consulting knowledge base...",
    "🚀 Almost there...",
    "✨ Crafting the perfect answer...",
]

LANGUAGES = {
    "English": "en", "Bengali": "bn", "Hindi": "hi", "Arabic": "ar",
    "Spanish": "es", "French": "fr", "German": "de", "Chinese": "zh",
    "Japanese": "ja", "Korean": "ko", "Russian": "ru", "Portuguese": "pt",
    "Italian": "it", "Turkish": "tr", "Dutch": "nl", "Polish": "pl",
    "Vietnamese": "vi", "Thai": "th", "Indonesian": "id", "Malay": "ms",
    "Persian": "fa", "Urdu": "ur", "Tamil": "ta", "Telugu": "te",
    "Swahili": "sw", "Ukrainian": "uk", "Greek": "el", "Hebrew": "he",
    "Romanian": "ro", "Hungarian": "hu", "Czech": "cs", "Swedish": "sv",
    "Norwegian": "no", "Danish": "da", "Finnish": "fi", "Slovak": "sk",
    "Croatian": "hr", "Bulgarian": "bg", "Serbian": "sr", "Catalan": "ca",
    "Malagasy": "mg", "Azerbaijani": "az", "Kazakh": "kk", "Uzbek": "uz",
}

# ─────────────────────────────────────────────────────────────────────────────
# FIREBASE INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────

def init_firebase() -> None:
    """Initialize Firebase Admin SDK."""
    if firebase_admin._apps:
        return
    cred_dict = {
        "type": "service_account",
        "project_id": FIREBASE_PROJECT_ID,
        "private_key_id": "key",
        "private_key": FIREBASE_PRIVATE_KEY,
        "client_email": FIREBASE_CLIENT_EMAIL,
        "client_id": "",
        "auth_uri": "[accounts.google.com](https://accounts.google.com/o/oauth2/auth)",
        "token_uri": "[oauth2.googleapis.com](https://oauth2.googleapis.com/token)",
        "auth_provider_x509_cert_url": "[googleapis.com](https://www.googleapis.com/oauth2/v1/certs)",
        "client_x509_cert_url": "",
    }
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DATABASE_URL})
    logger.info("✅ Firebase initialized successfully")


def fb_ref(path: str):
    """Get a Firebase database reference."""
    return firebase_db.reference(path)


def fb_get(path: str) -> Any:
    """Get data from Firebase."""
    try:
        return fb_ref(path).get()
    except Exception as e:
        logger.error(f"Firebase GET error at {path}: {e}")
        return None


def fb_set(path: str, data: Any) -> bool:
    """Set data in Firebase."""
    try:
        fb_ref(path).set(data)
        return True
    except Exception as e:
        logger.error(f"Firebase SET error at {path}: {e}")
        return False


def fb_update(path: str, data: dict) -> bool:
    """Update data in Firebase."""
    try:
        fb_ref(path).update(data)
        return True
    except Exception as e:
        logger.error(f"Firebase UPDATE error at {path}: {e}")
        return False


def fb_push(path: str, data: Any) -> Optional[str]:
    """Push data to Firebase list."""
    try:
        ref = fb_ref(path).push(data)
        return ref.key
    except Exception as e:
        logger.error(f"Firebase PUSH error at {path}: {e}")
        return None


def fb_delete(path: str) -> bool:
    """Delete data from Firebase."""
    try:
        fb_ref(path).delete()
        return True
    except Exception as e:
        logger.error(f"Firebase DELETE error at {path}: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE GEMINI CLIENT
# ─────────────────────────────────────────────────────────────────────────────

gemini_client: Optional[genai.Client] = None


def get_gemini_client() -> genai.Client:
    global gemini_client
    if gemini_client is None:
        gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
    return gemini_client


async def call_gemini(
    prompt: str,
    system_instruction: str = "",
    image_data: Optional[bytes] = None,
    image_mime: str = "image/jpeg",
    history: Optional[list] = None,
    temperature: float = 0.7,
) -> str:
    """Call Google Gemini API asynchronously."""
    try:
        client = get_gemini_client()
        contents = []

        if history:
            for msg in history[-CONVERSATION_HISTORY_LIMIT:]:
                role = msg.get("role", "user")
                text = msg.get("text", "")
                contents.append(
                    genai_types.Content(
                        role=role,
                        parts=[genai_types.Part(text=text)],
                    )
                )

        parts = []
        if image_data:
            parts.append(
                genai_types.Part(
                    inline_data=genai_types.Blob(mime_type=image_mime, data=image_data)
                )
            )
        parts.append(genai_types.Part(text=prompt))
        contents.append(genai_types.Content(role="user", parts=parts))

        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=8192,
        )
        if system_instruction:
            config.system_instruction = system_instruction

        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=AI_MODEL,
                contents=contents,
                config=config,
            ),
        )
        return response.text or "I couldn't generate a response. Please try again."
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return f"⚠️ AI Error: {str(e)[:200]}"


# ─────────────────────────────────────────────────────────────────────────────
# RATE LIMITER
# ─────────────────────────────────────────────────────────────────────────────

_rate_limit_store: dict[int, list[float]] = defaultdict(list)


def is_rate_limited(user_id: int) -> bool:
    """Check if user has exceeded rate limit."""
    now = time.time()
    calls = _rate_limit_store[user_id]
    calls[:] = [t for t in calls if now - t < RATE_LIMIT_PERIOD]
    if len(calls) >= RATE_LIMIT_CALLS:
        return True
    calls.append(now)
    return False


# ─────────────────────────────────────────────────────────────────────────────
# USER DATABASE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_user(user_id: int) -> dict:
    """Get user data from Firebase."""
    data = fb_get(f"users/{user_id}")
    return data or {}


def save_user(user_id: int, data: dict) -> bool:
    return fb_update(f"users/{user_id}", data)


def register_user(user_id: int, username: str, full_name: str, referrer_id: Optional[int] = None) -> dict:
    """Register a new user or update existing one."""
    existing = get_user(user_id)
    now = datetime.now(timezone.utc).isoformat()

    if not existing:
        user_data = {
            "user_id": user_id,
            "username": username or "",
            "full_name": full_name,
            "joined_at": now,
            "last_seen": now,
            "is_banned": False,
            "is_premium": False,
            "language": "en",
            "notifications": True,
            "streak": 0,
            "last_streak_date": "",
            "total_messages": 0,
            "ai_calls": 0,
            "quizzes_taken": 0,
            "notes_created": 0,
            "pdfs_processed": 0,
            "referrer_id": referrer_id,
            "referral_count": 0,
            "achievements": [],
            "quiz_score": 0,
        }
        fb_set(f"users/{user_id}", user_data)
        fb_update("stats/global", {"total_users": firebase_db.reference("stats/global/total_users").get() or 0 + 1})
        if referrer_id:
            fb_update(f"users/{referrer_id}", {
                "referral_count": (get_user(referrer_id).get("referral_count", 0) + 1)
            })
        return user_data
    else:
        update = {"last_seen": now, "full_name": full_name, "username": username or ""}
        fb_update(f"users/{user_id}", update)
        existing.update(update)
        return existing


def update_streak(user_id: int) -> int:
    """Update daily streak and return current streak."""
    user = get_user(user_id)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    last_date = user.get("last_streak_date", "")
    streak = user.get("streak", 0)

    if last_date == today:
        return streak
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    if last_date == yesterday:
        streak += 1
    else:
        streak = 1

    fb_update(f"users/{user_id}", {"streak": streak, "last_streak_date": today})
    return streak


def increment_stat(user_id: int, stat: str, amount: int = 1) -> None:
    """Increment a user statistic."""
    try:
        current = get_user(user_id).get(stat, 0)
        fb_update(f"users/{user_id}", {stat: current + amount})
    except Exception as e:
        logger.error(f"Error incrementing stat {stat}: {e}")


def add_history(user_id: int, action: str, data: str) -> None:
    """Add entry to user history."""
    try:
        entry = {
            "action": action,
            "data": data[:500],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        fb_push(f"history/{user_id}", entry)
        increment_stat(user_id, "total_messages")
    except Exception as e:
        logger.error(f"History error: {e}")


def get_history(user_id: int, limit: int = 10) -> list:
    """Get user history."""
    try:
        data = fb_get(f"history/{user_id}") or {}
        items = list(data.values()) if isinstance(data, dict) else []
        items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return items[:limit]
    except Exception:
        return []


def save_note(user_id: int, title: str, content: str) -> Optional[str]:
    """Save a note for user."""
    try:
        note = {
            "title": title,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_favorite": False,
        }
        key = fb_push(f"notes/{user_id}", note)
        increment_stat(user_id, "notes_created")
        return key
    except Exception as e:
        logger.error(f"Note save error: {e}")
        return None


def get_notes(user_id: int) -> dict:
    """Get all notes for user."""
    return fb_get(f"notes/{user_id}") or {}


def delete_note(user_id: int, note_id: str) -> bool:
    return fb_delete(f"notes/{user_id}/{note_id}")


def save_bookmark(user_id: int, title: str, content: str) -> None:
    """Save a bookmark."""
    try:
        entry = {
            "title": title,
            "content": content[:1000],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        fb_push(f"bookmarks/{user_id}", entry)
    except Exception as e:
        logger.error(f"Bookmark error: {e}")


def get_bookmarks(user_id: int) -> list:
    """Get user bookmarks."""
    try:
        data = fb_get(f"bookmarks/{user_id}") or {}
        return list(data.items()) if isinstance(data, dict) else []
    except Exception:
        return []


def save_quiz_score(user_id: int, topic: str, score: int, total: int) -> None:
    """Save quiz score."""
    try:
        entry = {
            "topic": topic,
            "score": score,
            "total": total,
            "percentage": round((score / total) * 100, 1) if total > 0 else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        fb_push(f"quiz_scores/{user_id}", entry)
        current_score = get_user(user_id).get("quiz_score", 0)
        fb_update(f"users/{user_id}", {"quiz_score": current_score + score})
        increment_stat(user_id, "quizzes_taken")
    except Exception as e:
        logger.error(f"Quiz score error: {e}")


def get_conversation_history(user_id: int) -> list:
    """Get AI conversation history."""
    return fb_get(f"conversations/{user_id}") or []


def save_conversation_history(user_id: int, history: list) -> None:
    """Save AI conversation history."""
    trimmed = history[-CONVERSATION_HISTORY_LIMIT:]
    fb_set(f"conversations/{user_id}", trimmed)


def clear_conversation(user_id: int) -> None:
    fb_delete(f"conversations/{user_id}")


def save_exam(user_id: int, name: str, date_str: str) -> None:
    """Save exam countdown."""
    try:
        entry = {"name": name, "date": date_str, "created_at": datetime.now(timezone.utc).isoformat()}
        fb_push(f"exams/{user_id}", entry)
    except Exception as e:
        logger.error(f"Exam save error: {e}")


def get_exams(user_id: int) -> list:
    try:
        data = fb_get(f"exams/{user_id}") or {}
        return list(data.items()) if isinstance(data, dict) else []
    except Exception:
        return []


def get_leaderboard(limit: int = 10) -> list:
    """Get top quiz scorers."""
    try:
        users = fb_get("users") or {}
        scores = []
        for uid, data in users.items():
            if isinstance(data, dict) and not data.get("is_banned", False):
                scores.append({
                    "user_id": uid,
                    "full_name": data.get("full_name", "Unknown"),
                    "quiz_score": data.get("quiz_score", 0),
                    "streak": data.get("streak", 0),
                })
        scores.sort(key=lambda x: x["quiz_score"], reverse=True)
        return scores[:limit]
    except Exception:
        return []


def is_banned(user_id: int) -> bool:
    return bool(get_user(user_id).get("is_banned", False))


def is_maintenance() -> bool:
    return bool(fb_get("settings/maintenance") or False)


# ─────────────────────────────────────────────────────────────────────────────
# KEYBOARD BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def main_keyboard() -> ReplyKeyboardMarkup:
    """Build the main reply keyboard with all important features."""
    buttons = [
        [KeyboardButton("🏠 Home"), KeyboardButton("🤖 AI Chat")],
        [KeyboardButton("📚 Study"), KeyboardButton("📄 PDF")],
        [KeyboardButton("📝 Notes"), KeyboardButton("🧮 Math Solver")],
        [KeyboardButton("🧠 Quiz"), KeyboardButton("📷 OCR")],
        [KeyboardButton("🎓 Homework Help"), KeyboardButton("📖 Explain Topic")],
        [KeyboardButton("📝 Text Summary"), KeyboardButton("🌐 Translate")],
        [KeyboardButton("✍ Essay Writer"), KeyboardButton("💻 Code Assistant")],
        [KeyboardButton("👤 Profile"), KeyboardButton("⚙ Settings")],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, persistent=True)


def nav_inline(back_cb: str = "home", show_home: bool = True) -> list[list[InlineKeyboardButton]]:
    """Standard navigation buttons."""
    row = [InlineKeyboardButton("⬅ Back", callback_data=back_cb)]
    if show_home:
        row.append(InlineKeyboardButton("🏠 Home", callback_data="home"))
    row.append(InlineKeyboardButton("❌ Close", callback_data="close"))
    return [row]


def study_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📖 Explain Chapter", callback_data="study_explain"),
         InlineKeyboardButton("📋 Summary", callback_data="study_summary")],
        [InlineKeyboardButton("❓ Generate MCQ", callback_data="study_mcq"),
         InlineKeyboardButton("📝 Short Notes", callback_data="study_short_notes")],
        [InlineKeyboardButton("🃏 Flashcards", callback_data="study_flashcards"),
         InlineKeyboardButton("📅 Study Planner", callback_data="study_planner")],
        [InlineKeyboardButton("🔔 Study Reminder", callback_data="study_reminder"),
         InlineKeyboardButton("📌 Bookmarks", callback_data="study_bookmarks")],
        [InlineKeyboardButton("⏰ Exam Countdown", callback_data="study_exam_countdown")],
        *nav_inline("home"),
    ]
    return InlineKeyboardMarkup(buttons)


def quiz_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("🚀 Start Quiz", callback_data="quiz_start"),
         InlineKeyboardButton("📅 Daily Quiz", callback_data="quiz_daily")],
        [InlineKeyboardButton("📆 Weekly Quiz", callback_data="quiz_weekly"),
         InlineKeyboardButton("🏆 Leaderboard", callback_data="quiz_leaderboard")],
        [InlineKeyboardButton("📊 My Results", callback_data="quiz_results")],
        *nav_inline("home"),
    ]
    return InlineKeyboardMarkup(buttons)


def pdf_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📋 Summarize PDF", callback_data="pdf_summarize"),
         InlineKeyboardButton("❓ Generate MCQ", callback_data="pdf_mcq")],
        [InlineKeyboardButton("📝 Generate Notes", callback_data="pdf_notes"),
         InlineKeyboardButton("💬 Ask Questions", callback_data="pdf_ask")],
        [InlineKeyboardButton("📄 Extract Text", callback_data="pdf_extract")],
        *nav_inline("home"),
    ]
    return InlineKeyboardMarkup(buttons)


def math_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("🔢 Step-by-Step", callback_data="math_step"),
         InlineKeyboardButton("📐 Formula", callback_data="math_formula")],
        [InlineKeyboardButton("📈 Graph Analysis", callback_data="math_graph"),
         InlineKeyboardButton("🧮 Calculator", callback_data="math_calc")],
        *nav_inline("home"),
    ]
    return InlineKeyboardMarkup(buttons)


def translate_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("🔍 Detect Language", callback_data="translate_detect"),
         InlineKeyboardButton("🌍 Translate Text", callback_data="translate_text")],
        *nav_inline("home"),
    ]
    return InlineKeyboardMarkup(buttons)


def notes_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("➕ Create Note", callback_data="note_create"),
         InlineKeyboardButton("📋 My Notes", callback_data="note_list")],
        [InlineKeyboardButton("🔍 Search Notes", callback_data="note_search"),
         InlineKeyboardButton("❤️ Favorites", callback_data="note_favorites")],
        [InlineKeyboardButton("🕐 History", callback_data="note_history")],
        *nav_inline("home"),
    ]
    return InlineKeyboardMarkup(buttons)


def ai_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📚 Homework Help", callback_data="ai_homework"),
         InlineKeyboardButton("💡 Explain Anything", callback_data="ai_explain")],
        [InlineKeyboardButton("🧮 Math Solver", callback_data="ai_math"),
         InlineKeyboardButton("✏️ Grammar Fix", callback_data="ai_grammar")],
        [InlineKeyboardButton("📝 Essay Writer", callback_data="ai_essay"),
         InlineKeyboardButton("📨 Letter Writer", callback_data="ai_letter")],
        [InlineKeyboardButton("📋 Paragraph Writer", callback_data="ai_paragraph"),
         InlineKeyboardButton("📖 Story Writer", callback_data="ai_story")],
        [InlineKeyboardButton("🔁 Summarize", callback_data="ai_summarize"),
         InlineKeyboardButton("✍️ Rewrite Text", callback_data="ai_rewrite")],
        [InlineKeyboardButton("💻 Code Generator", callback_data="ai_code"),
         InlineKeyboardButton("🔍 Code Explainer", callback_data="ai_explain_code")],
        [InlineKeyboardButton("🖼️ Image to Text (OCR)", callback_data="ai_ocr"),
         InlineKeyboardButton("💬 Free Chat", callback_data="ai_chat")],
        *nav_inline("home"),
    ]
    return InlineKeyboardMarkup(buttons)


def profile_keyboard(user_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📊 Statistics", callback_data="profile_stats"),
         InlineKeyboardButton("🕐 History", callback_data="profile_history")],
        [InlineKeyboardButton("🔥 Streak", callback_data="profile_streak"),
         InlineKeyboardButton("🏆 Achievements", callback_data="profile_achievements")],
        [InlineKeyboardButton("🔗 Referral Link", callback_data="profile_referral"),
         InlineKeyboardButton("💎 Premium", callback_data="profile_premium")],
        *nav_inline("home"),
    ]
    return InlineKeyboardMarkup(buttons)


def settings_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("🌍 Language", callback_data="settings_language"),
         InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications")],
        [InlineKeyboardButton("🔒 Privacy", callback_data="settings_privacy"),
         InlineKeyboardButton("🗑️ Reset Data", callback_data="settings_reset")],
        *nav_inline("home"),
    ]
    return InlineKeyboardMarkup(buttons)


def admin_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
         InlineKeyboardButton("🔨 Ban User", callback_data="admin_ban")],
        [InlineKeyboardButton("✅ Unban User", callback_data="admin_unban"),
         InlineKeyboardButton("👥 User Count", callback_data="admin_usercount")],
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
         InlineKeyboardButton("🔧 Maintenance", callback_data="admin_maintenance")],
        [InlineKeyboardButton("📋 Logs", callback_data="admin_logs"),
         InlineKeyboardButton("🔄 Restart", callback_data="admin_restart")],
        *nav_inline("home"),
    ]
    return InlineKeyboardMarkup(buttons)


def language_keyboard() -> InlineKeyboardMarkup:
    common_langs = list(LANGUAGES.keys())[:20]
    buttons = []
    for i in range(0, len(common_langs), 3):
        row = [InlineKeyboardButton(lang, callback_data=f"setlang_{LANGUAGES[lang]}")
               for lang in common_langs[i:i+3]]
        buttons.append(row)
    buttons.extend(nav_inline("settings"))
    return InlineKeyboardMarkup(buttons)


# ─────────────────────────────────────────────────────────────────────────────
# TEXT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def escape_md(text: str) -> str:
    """Escape text for MarkdownV2."""
    chars = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in chars else c for c in str(text))


def split_long_message(text: str, limit: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Split message into chunks."""
    if len(text) <= limit:
        return [text]
    chunks = []
    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


async def send_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Send typing action."""
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except Exception:
        pass


async def send_long_message(
    message: Message,
    text: str,
    parse_mode: str = ParseMode.MARKDOWN,
    reply_markup=None,
) -> None:
    """Send potentially long message in chunks."""
    chunks = split_long_message(text)
    for i, chunk in enumerate(chunks):
        try:
            if i == len(chunks) - 1:
                await message.reply_text(chunk, parse_mode=parse_mode, reply_markup=reply_markup)
            else:
                await message.reply_text(chunk, parse_mode=parse_mode)
        except TelegramError as e:
            logger.warning(f"Send error (trying plain text): {e}")
            try:
                clean = re.sub(r"[*_`\[\]()~>#+=|{}.!\\]", "", chunk)
                if i == len(chunks) - 1:
                    await message.reply_text(clean, reply_markup=reply_markup)
                else:
                    await message.reply_text(clean)
            except Exception as e2:
                logger.error(f"Failed to send chunk: {e2}")


async def loading_message(message: Message) -> Message:
    """Send a random loading message."""
    return await message.reply_text(random.choice(LOADING_MESSAGES))


async def check_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user has joined the required channel."""
    if not CHANNEL_USERNAME:
        return True
    try:
        user_id = update.effective_user.id
        member = await context.bot.get_chat_member(
            f"@{CHANNEL_USERNAME.lstrip('@')}", user_id
        )
        return member.status not in ("left", "kicked")
    except Exception:
        return True


# ─────────────────────────────────────────────────────────────────────────────
# DECORATORS
# ─────────────────────────────────────────────────────────────────────────────

def require_not_banned(func):
    """Decorator to block banned users."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user and is_banned(user.id):
            await update.effective_message.reply_text(
                "🚫 You have been banned from using this bot."
            )
            return ConversationHandler.END
        return await func(update, context, *args, **kwargs)
    return wrapper


def require_not_maintenance(func):
    """Decorator to block non-owners during maintenance."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user and user.id != OWNER_ID and is_maintenance():
            await update.effective_message.reply_text(
                "🔧 Bot is under maintenance. Please try again later."
            )
            return ConversationHandler.END
        return await func(update, context, *args, **kwargs)
    return wrapper


def rate_limited(func):
    """Rate limiting decorator."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user and is_rate_limited(user.id):
            await update.effective_message.reply_text(
                "⚡ Slow down! You're sending too many requests. Please wait a moment."
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def owner_only(func):
    """Restrict handler to bot owner."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user or user.id != OWNER_ID:
            await update.effective_message.reply_text("🚫 This command is owner-only.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# FORCE JOIN CHECK
# ─────────────────────────────────────────────────────────────────────────────

async def force_join_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Returns True if user can proceed; False if they need to join channel."""
    if not CHANNEL_USERNAME:
        return True
    joined = await check_force_join(update, context)
    if not joined:
        channel = CHANNEL_USERNAME.lstrip("@")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"[t.me](https://t.me/{channel})")],
            [InlineKeyboardButton("✅ I Joined", callback_data="check_join")],
        ])
        await update.effective_message.reply_text(
            f"📢 *Join Required*\n\nTo use this bot, please join our channel first:\n\n"
            f"👉 @{channel}\n\nThen press ✅ I Joined.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# HOME / START
# ─────────────────────────────────────────────────────────────────────────────

@require_not_banned
@require_not_maintenance
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    args = context.args

    referrer_id = None
    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0][4:])
            if referrer_id == user.id:
                referrer_id = None
        except ValueError:
            pass

    user_data = register_user(user.id, user.username, user.full_name, referrer_id)
    streak = update_streak(user.id)

    await force_join_gate(update, context)

    welcome_text = (
        f"✨ *Welcome to AI Study Bot!* ✨\n\n"
        f"Hello, *{user.full_name}*! 👋\n\n"
        f"🎓 Your personal AI-powered study companion is here to help you:\n\n"
        f"• 🤖 Chat with advanced AI\n"
        f"• 📚 Get detailed study explanations\n"
        f"• 🧠 Take interactive quizzes\n"
        f"• 📝 Manage your study notes\n"
        f"• 📄 Process and analyze PDFs\n"
        f"• 🧮 Solve complex math problems\n"
        f"• 🌐 Translate 100+ languages\n"
        f"• 🖼️ Extract text from images (OCR)\n\n"
        f"🔥 Current streak: *{streak} day{'s' if streak != 1 else ''}*\n\n"
        f"Use the menu below to get started!"
    )

    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard(),
    )

    add_history(user.id, "start", "User started bot")


@require_not_banned
@require_not_maintenance
async def home_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 🏠 Home button."""
    user = update.effective_user
    streak = update_streak(user.id)

    text = (
        f"🏠 *Main Menu*\n\n"
        f"Welcome back, *{user.first_name}*! 👋\n"
        f"🔥 Streak: *{streak} day{'s' if streak != 1 else ''}*\n\n"
        f"Choose a feature from the keyboard below:"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_keyboard())
    context.user_data.clear()
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
# HELP COMMAND
# ─────────────────────────────────────────────────────────────────────────────

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    text = (
        "📖 *AI Study Bot — Help Guide*\n\n"
        "*Main Features:*\n"
        "🤖 `/chat` — Start AI conversation\n"
        "📚 `/study` — Study tools menu\n"
        "🧠 `/quiz` — Take a quiz\n"
        "📝 `/notes` — Manage your notes\n"
        "📄 `/pdf` — PDF tools\n"
        "🧮 `/math` — Math solver\n"
        "🌐 `/translate` — Translation\n"
        "👤 `/profile` — Your profile\n"
        "⚙ `/settings` — Bot settings\n\n"
        "*Utility Commands:*\n"
        "`/clear` — Clear AI chat history\n"
        "`/streak` — Check your streak\n"
        "`/leaderboard` — View top scorers\n"
        "`/stats` — Your statistics\n\n"
        "*Send an image* to extract text (OCR)\n"
        "*Send a PDF* to process it\n\n"
        "💡 *Tip:* Use the keyboard buttons for quick navigation!"
    )
    await (update.message or update.effective_message).reply_text(
        text, parse_mode=ParseMode.MARKDOWN
    )


# ─────────────────────────────────────────────────────────────────────────────
# AI CHAT HANDLER
# ─────────────────────────────────────────────────────────────────────────────

@require_not_banned
@require_not_maintenance
async def ai_chat_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for AI Chat."""
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Clear History", callback_data="ai_clear_history"),
         InlineKeyboardButton("❌ Exit Chat", callback_data="home")],
    ])
    await update.effective_message.reply_text(
        "🤖 *AI Chat Mode*\n\n"
        "I'm your intelligent study assistant! Ask me anything:\n\n"
        "• Homework questions\n"
        "• Concept explanations\n"
        "• Problem solving\n"
        "• Writing help\n"
        "• And much more!\n\n"
        "💬 Just type your message below:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb,
    )
    return STATE_AI_CHAT


@require_not_banned
@rate_limited
async def ai_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle AI chat messages."""
    user = update.effective_user
    user_text = update.message.text.strip()

    _menu_buttons = {
        "🏠 Home", "📚 Study", "📄 PDF", "📝 Notes", "🧮 Math Solver",
        "🧠 Quiz", "📷 OCR", "🎓 Homework Help", "📖 Explain Topic",
        "📝 Text Summary", "🌐 Translate", "✍ Essay Writer",
        "💻 Code Assistant", "👤 Profile", "⚙ Settings",
    }
    if user_text in _menu_buttons or user_text in ("/start", "/home"):
        return await reply_keyboard_router(update, context)

    await send_typing(context, update.effective_chat.id)
    loading_msg = await loading_message(update.message)

    history = get_conversation_history(user.id)

    system_prompt = (
        "You are an intelligent AI study assistant. Help students learn effectively. "
        "Be encouraging, clear, and educational. Use structured explanations with examples. "
        "For math, show step-by-step solutions. For code, add comments. "
        "Use emojis appropriately to make responses engaging."
    )

    response = await call_gemini(
        prompt=user_text,
        system_instruction=system_prompt,
        history=history,
        temperature=0.7,
    )

    history.append({"role": "user", "text": user_text})
    history.append({"role": "model", "text": response})
    save_conversation_history(user.id, history)
    increment_stat(user.id, "ai_calls")
    add_history(user.id, "ai_chat", user_text[:100])

    try:
        await loading_msg.delete()
    except Exception:
        pass

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📌 Save as Note", callback_data=f"save_note_ai"),
         InlineKeyboardButton("🗑️ Clear Chat", callback_data="ai_clear_history")],
        [InlineKeyboardButton("🏠 Home", callback_data="home"),
         InlineKeyboardButton("❌ Close", callback_data="close")],
    ])

    context.user_data["last_ai_response"] = response
    await send_long_message(update.message, response, reply_markup=kb)
    return STATE_AI_CHAT


# ─────────────────────────────────────────────────────────────────────────────
# STUDY HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@require_not_banned
@require_not_maintenance
async def study_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show study menu."""
    msg = update.effective_message
    await msg.reply_text(
        "📚 *Study Tools*\n\nChoose what you'd like to do:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=study_keyboard(),
    )


@require_not_banned
@require_not_maintenance
async def study_explain_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start explain chapter flow."""
    await update.effective_message.reply_text(
        "📖 *Explain Chapter*\n\nSend me a topic or chapter title and I'll explain it in detail!\n\n"
        "*Examples:*\n• Photosynthesis\n• World War II causes\n• Pythagorean theorem\n• Python OOP",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
    )
    return STATE_STUDY_CHAPTER


async def study_explain_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle chapter explanation."""
    topic = update.message.text.strip()
    loading_msg = await loading_message(update.message)
    await send_typing(context, update.effective_chat.id)

    prompt = (
        f"Explain the following topic in a comprehensive, student-friendly way:\n\n"
        f"Topic: {topic}\n\n"
        f"Structure your response with:\n"
        f"1. 📌 Overview/Definition\n"
        f"2. 🔑 Key Concepts\n"
        f"3. 📖 Detailed Explanation\n"
        f"4. 💡 Examples\n"
        f"5. 🎯 Key Takeaways\n"
        f"6. ❓ Common Questions\n\n"
        f"Make it educational and engaging."
    )

    response = await call_gemini(prompt, temperature=0.5)
    increment_stat(update.effective_user.id, "ai_calls")
    add_history(update.effective_user.id, "study_explain", topic)

    try:
        await loading_msg.delete()
    except Exception:
        pass

    context.user_data["last_ai_response"] = response
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📌 Bookmark", callback_data="bookmark_last"),
         InlineKeyboardButton("📝 Save as Note", callback_data="save_note_ai")],
        *nav_inline("menu_study"),
    ])
    await send_long_message(update.message, response, reply_markup=kb)
    return ConversationHandler.END


async def study_summary_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "📋 *Topic Summary*\n\nSend me a topic and I'll create a concise summary!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
    )
    return STATE_STUDY_SUMMARY


async def study_summary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    topic = update.message.text.strip()
    loading_msg = await loading_message(update.message)
    await send_typing(context, update.effective_chat.id)

    prompt = (
        f"Create a concise, well-structured summary of: {topic}\n\n"
        f"Include:\n"
        f"• 📌 Main points (bullet form)\n"
        f"• 🔑 Key facts and dates (if applicable)\n"
        f"• 🎯 Core concepts\n"
        f"• 📝 Quick revision notes\n\n"
        f"Keep it concise but comprehensive."
    )

    response = await call_gemini(prompt, temperature=0.4)
    increment_stat(update.effective_user.id, "ai_calls")
    add_history(update.effective_user.id, "study_summary", topic)

    try:
        await loading_msg.delete()
    except Exception:
        pass

    context.user_data["last_ai_response"] = response
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📌 Bookmark", callback_data="bookmark_last"),
         InlineKeyboardButton("📝 Save Note", callback_data="save_note_ai")],
        *nav_inline("menu_study"),
    ])
    await send_long_message(update.message, response, reply_markup=kb)
    return ConversationHandler.END


async def study_mcq_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "❓ *Generate MCQ*\n\nSend a topic and I'll generate multiple-choice questions!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
    )
    return STATE_STUDY_MCQ


async def study_mcq_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    topic = update.message.text.strip()
    loading_msg = await loading_message(update.message)
    await send_typing(context, update.effective_chat.id)

    prompt = (
        f"Generate 5 high-quality MCQ questions about: {topic}\n\n"
        f"Format each question exactly as:\n"
        f"Q[n]. [Question text]\n"
        f"A) [Option]\nB) [Option]\nC) [Option]\nD) [Option]\n"
        f"✅ Answer: [letter]) [answer]\n"
        f"💡 Explanation: [brief explanation]\n\n"
        f"Make questions progressively harder."
    )

    response = await call_gemini(prompt, temperature=0.6)
    increment_stat(update.effective_user.id, "ai_calls")
    add_history(update.effective_user.id, "study_mcq", topic)

    try:
        await loading_msg.delete()
    except Exception:
        pass

    context.user_data["last_ai_response"] = response
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📌 Bookmark", callback_data="bookmark_last"),
         InlineKeyboardButton("🧠 Start Quiz", callback_data="quiz_start")],
        *nav_inline("menu_study"),
    ])
    await send_long_message(update.message, response, reply_markup=kb)
    return ConversationHandler.END


async def study_flashcards_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "🃏 *Flashcards*\n\nSend a topic and I'll create study flashcards!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
    )
    return STATE_FLASHCARD_TOPIC


async def study_flashcards_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    topic = update.message.text.strip()
    loading_msg = await loading_message(update.message)
    await send_typing(context, update.effective_chat.id)

    prompt = (
        f"Create 8 study flashcards for: {topic}\n\n"
        f"Format each card as:\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🃏 Card [n]\n"
        f"📌 FRONT: [Question/Term]\n"
        f"💡 BACK: [Answer/Definition]\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"Cover the most important concepts."
    )

    response = await call_gemini(prompt, temperature=0.5)
    increment_stat(update.effective_user.id, "ai_calls")
    add_history(update.effective_user.id, "flashcards", topic)

    try:
        await loading_msg.delete()
    except Exception:
        pass

    context.user_data["last_ai_response"] = response
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Save as Note", callback_data="save_note_ai"),
         InlineKeyboardButton("📌 Bookmark", callback_data="bookmark_last")],
        *nav_inline("menu_study"),
    ])
    await send_long_message(update.message, response, reply_markup=kb)
    return ConversationHandler.END


async def study_planner_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "📅 *Study Planner*\n\nWhat subject/topic do you want to study?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
    )
    context.user_data["planner_step"] = "topic"
    return STATE_PLANNER_TOPIC


async def study_planner_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["planner_topic"] = update.message.text.strip()
    await update.message.reply_text(
        "📅 How many days do you have to study? (e.g., 7, 14, 30)",
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
    )
    return STATE_PLANNER_DAYS


async def study_planner_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        days = int(update.message.text.strip())
        if days < 1 or days > 365:
            await update.message.reply_text("Please enter a number between 1 and 365.")
            return STATE_PLANNER_DAYS
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return STATE_PLANNER_DAYS

    topic = context.user_data.get("planner_topic", "General Study")
    loading_msg = await loading_message(update.message)
    await send_typing(context, update.effective_chat.id)

    prompt = (
        f"Create a detailed {days}-day study plan for: {topic}\n\n"
        f"Structure the plan with:\n"
        f"• Daily goals and tasks\n"
        f"• Time allocation suggestions\n"
        f"• Weekly milestones\n"
        f"• Review days built in\n"
        f"• Practice test schedule\n\n"
        f"Make it realistic and motivating. Format clearly by day/week."
    )

    response = await call_gemini(prompt, temperature=0.5)
    increment_stat(update.effective_user.id, "ai_calls")
    add_history(update.effective_user.id, "study_planner", f"{topic} ({days} days)")

    try:
        await loading_msg.delete()
    except Exception:
        pass

    context.user_data["last_ai_response"] = response
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Save as Note", callback_data="save_note_ai")],
        *nav_inline("menu_study"),
    ])
    await send_long_message(update.message, response, reply_markup=kb)
    return ConversationHandler.END


async def study_short_notes_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "📝 *Short Notes Generator*\n\nSend a topic for quick revision notes!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
    )
    return STATE_STUDY_SUMMARY


# ─────────────────────────────────────────────────────────────────────────────
# EXAM COUNTDOWN
# ─────────────────────────────────────────────────────────────────────────────

async def exam_countdown_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start adding exam countdown."""
    user_id = update.effective_user.id
    exams = get_exams(user_id)

    text = "⏰ *Exam Countdown*\n\n"
    if exams:
        text += "📋 *Your upcoming exams:*\n"
        now = datetime.now(timezone.utc)
        for _, exam in exams[:5]:
            try:
                exam_date = datetime.fromisoformat(exam.get("date", ""))
                delta = exam_date - now
                days_left = delta.days
                status = f"{days_left} days" if days_left > 0 else "⚠️ Past"
            except Exception:
                status = "Invalid date"
            text += f"• 📚 {exam.get('name', 'Unknown')}: {status} left\n"
        text += "\n"

    text += "➕ Add a new exam?\n\nSend the exam name:"
    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
    )
    return STATE_EXAM_NAME


async def exam_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["exam_name"] = update.message.text.strip()
    await update.message.reply_text(
        "📅 Enter the exam date (format: YYYY-MM-DD, e.g., 2025-06-15):",
        reply_markup=InlineKeyboardMarkup(nav_inline("study_exam_countdown")),
    )
    return STATE_EXAM_DATE


async def exam_date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    date_text = update.message.text.strip()
    try:
        exam_date = datetime.strptime(date_text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_left = (exam_date - now).days

        name = context.user_data.get("exam_name", "Exam")
        save_exam(update.effective_user.id, name, exam_date.isoformat())
        add_history(update.effective_user.id, "exam_added", name)

        emoji_status = "🔴" if days_left < 7 else ("🟡" if days_left < 30 else "🟢")
        await update.message.reply_text(
            f"✅ *Exam Added!*\n\n"
            f"📚 Name: {name}\n"
            f"📅 Date: {date_text}\n"
            f"{emoji_status} Days left: *{days_left}*\n\n"
            f"{'⚠️ Start studying NOW!' if days_left < 7 else '📖 Keep studying consistently!'}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid date format. Please use YYYY-MM-DD (e.g., 2025-06-15)."
        )
        return STATE_EXAM_DATE
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
# QUIZ HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@require_not_banned
@require_not_maintenance
async def quiz_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "🧠 *Quiz Center*\n\nTest your knowledge with AI-powered quizzes!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=quiz_keyboard(),
    )


async def quiz_start_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start a quiz by asking for topic."""
    await update.effective_message.reply_text(
        "🧠 *Start Quiz*\n\nWhat topic would you like to be quizzed on?\n\n"
        "*Examples:*\n• History\n• Biology\n• Python programming\n• General Knowledge",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_quiz")),
    )
    context.user_data["quiz_type"] = "custom"
    return STATE_QUIZ_TOPIC


async def quiz_daily_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start daily quiz on random topic."""
    topics = [
        "General Knowledge", "Science", "History", "Geography",
        "Literature", "Mathematics", "Technology", "Art & Culture"
    ]
    topic = random.choice(topics)
    context.user_data["quiz_topic"] = topic
    context.user_data["quiz_type"] = "daily"
    await update.effective_message.reply_text(
        f"📅 *Daily Quiz*\n\nToday's topic: *{topic}*\n\nGenerating questions...",
        parse_mode=ParseMode.MARKDOWN,
    )
    return await generate_quiz(update, context, topic)


async def quiz_weekly_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    topics = ["Science", "History", "Geography", "Technology", "Literature"]
    topic = topics[datetime.now().isocalendar()[1] % len(topics)]
    context.user_data["quiz_topic"] = topic
    context.user_data["quiz_type"] = "weekly"
    await update.effective_message.reply_text(
        f"📆 *Weekly Challenge*\n\nThis week's topic: *{topic}*\n\nGenerating questions...",
        parse_mode=ParseMode.MARKDOWN,
    )
    return await generate_quiz(update, context, topic)


async def quiz_topic_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    topic = update.message.text.strip()
    context.user_data["quiz_topic"] = topic
    return await generate_quiz(update, context, topic)


async def generate_quiz(
    update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str
) -> int:
    """Generate quiz questions and present first one."""
    loading_msg = await (update.message or update.effective_message).reply_text(
        "🤔 Generating quiz questions..."
    )
    await send_typing(context, update.effective_chat.id)

    prompt = (
        f"Generate exactly 5 multiple choice quiz questions about: {topic}\n\n"
        f"Return ONLY valid JSON in this exact format:\n"
        f'{{"questions": [{{'
        f'"question": "...", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], '
        f'"answer": "A", "explanation": "..."'
        f"}}]}}\n\n"
        f"The 'answer' field must be only the letter A, B, C, or D."
    )

    response = await call_gemini(prompt, temperature=0.6)

    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            quiz_data = json.loads(json_match.group())
            questions = quiz_data.get("questions", [])
        else:
            raise ValueError("No JSON found")

        if not questions:
            raise ValueError("Empty questions")

        context.user_data["quiz_questions"] = questions
        context.user_data["quiz_current"] = 0
        context.user_data["quiz_score"] = 0
        context.user_data["quiz_answers"] = []

        try:
            await loading_msg.delete()
        except Exception:
            pass

        return await show_quiz_question(update, context)

    except Exception as e:
        logger.error(f"Quiz generation error: {e}\nResponse: {response[:500]}")
        try:
            await loading_msg.delete()
        except Exception:
            pass
        await (update.message or update.effective_message).reply_text(
            "⚠️ Failed to generate quiz. Please try a different topic.",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_quiz")),
        )
        return ConversationHandler.END


async def show_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show current quiz question."""
    questions = context.user_data.get("quiz_questions", [])
    current = context.user_data.get("quiz_current", 0)

    if current >= len(questions):
        return await finish_quiz(update, context)

    q = questions[current]
    total = len(questions)
    progress_bar = "█" * (current + 1) + "░" * (total - current - 1)

    text = (
        f"🧠 *Question {current + 1}/{total}*\n"
        f"[{progress_bar}]\n\n"
        f"📌 {q['question']}\n\n"
    )
    for opt in q.get("options", []):
        text += f"{opt}\n"

    options = q.get("options", [])
    option_buttons = []
    for i, opt in enumerate(options):
        letter = opt[0] if opt else chr(65 + i)
        option_buttons.append([
            InlineKeyboardButton(f"{opt[:40]}", callback_data=f"quiz_ans_{letter}")
        ])
    option_buttons.append([InlineKeyboardButton("❌ End Quiz", callback_data="home")])

    await (update.message or update.effective_message).reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(option_buttons),
    )
    return STATE_QUIZ_ANSWER


async def quiz_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle quiz answer selection via callback."""
    query = update.callback_query
    await query.answer()

    answer = query.data.replace("quiz_ans_", "")
    questions = context.user_data.get("quiz_questions", [])
    current = context.user_data.get("quiz_current", 0)

    if current >= len(questions):
        return await finish_quiz(update, context)

    q = questions[current]
    correct = q.get("answer", "A").upper()
    is_correct = answer.upper() == correct

    if is_correct:
        context.user_data["quiz_score"] = context.user_data.get("quiz_score", 0) + 1
        result_text = f"✅ *Correct!* Well done!\n\n"
    else:
        result_text = f"❌ *Wrong!* The answer was *{correct}*\n\n"

    result_text += f"💡 *Explanation:* {q.get('explanation', 'N/A')}"

    context.user_data["quiz_current"] = current + 1
    context.user_data.setdefault("quiz_answers", []).append({
        "question": q["question"],
        "your_answer": answer,
        "correct": correct,
        "is_correct": is_correct,
    })

    next_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "➡️ Next Question" if current + 1 < len(questions) else "🏁 See Results",
            callback_data="quiz_next"
        )
    ]])

    await query.edit_message_text(
        result_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=next_kb,
    )
    return STATE_QUIZ_ANSWER


async def quiz_next_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Move to next quiz question."""
    query = update.callback_query
    await query.answer()
    return await show_quiz_question(update, context)


async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show quiz results."""
    score = context.user_data.get("quiz_score", 0)
    questions = context.user_data.get("quiz_questions", [])
    total = len(questions)
    topic = context.user_data.get("quiz_topic", "Unknown")
    user_id = update.effective_user.id

    percentage = round((score / total) * 100, 1) if total > 0 else 0
    save_quiz_score(user_id, topic, score, total)
    add_history(user_id, "quiz_completed", f"{topic}: {score}/{total}")

    if percentage >= 80:
        grade_emoji = "🏆"
        grade_text = "Excellent!"
    elif percentage >= 60:
        grade_emoji = "⭐"
        grade_text = "Good job!"
    elif percentage >= 40:
        grade_emoji = "📚"
        grade_text = "Keep studying!"
    else:
        grade_emoji = "💪"
        grade_text = "Don't give up!"

    text = (
        f"{grade_emoji} *Quiz Complete!*\n\n"
        f"📚 Topic: {topic}\n"
        f"📊 Score: *{score}/{total}* ({percentage}%)\n"
        f"💬 {grade_text}\n\n"
    )

    answers = context.user_data.get("quiz_answers", [])
    if answers:
        text += "📋 *Review:*\n"
        for i, ans in enumerate(answers[:5], 1):
            mark = "✅" if ans["is_correct"] else "❌"
            text += f"{mark} Q{i}: Your: {ans['your_answer']} | Correct: {ans['correct']}\n"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 New Quiz", callback_data="quiz_start"),
         InlineKeyboardButton("🏆 Leaderboard", callback_data="quiz_leaderboard")],
        *nav_inline("menu_quiz"),
    ])

    await (update.effective_message).reply_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
    )
    context.user_data.pop("quiz_questions", None)
    context.user_data.pop("quiz_current", None)
    context.user_data.pop("quiz_score", None)
    context.user_data.pop("quiz_answers", None)
    return ConversationHandler.END


async def quiz_leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show quiz leaderboard."""
    leaders = get_leaderboard(10)

    text = "🏆 *Quiz Leaderboard*\n\n"
    medals = ["🥇", "🥈", "🥉"] + ["🎖️"] * 7

    if leaders:
        for i, leader in enumerate(leaders):
            text += f"{medals[i]} *{leader['full_name']}*: {leader['quiz_score']} pts\n"
    else:
        text += "No scores yet. Be the first to take a quiz!\n"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠 Take Quiz", callback_data="quiz_start")],
        *nav_inline("menu_quiz"),
    ])
    await update.effective_message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
    )


async def quiz_results_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's quiz results."""
    user_id = update.effective_user.id
    scores_data = fb_get(f"quiz_scores/{user_id}") or {}
    scores = list(scores_data.values()) if isinstance(scores_data, dict) else []
    scores.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    text = "📊 *Your Quiz Results*\n\n"
    if scores:
        total_quizzes = len(scores)
        avg = sum(s.get("percentage", 0) for s in scores) / total_quizzes
        text += f"Total quizzes: *{total_quizzes}*\nAverage score: *{avg:.1f}%*\n\n"
        text += "🕐 *Recent results:*\n"
        for s in scores[:5]:
            pct = s.get("percentage", 0)
            emoji = "✅" if pct >= 60 else "❌"
            text += f"{emoji} {s.get('topic', 'Unknown')}: {s.get('score', 0)}/{s.get('total', 0)} ({pct}%)\n"
    else:
        text += "No quiz results yet. Take a quiz to see your scores!"

    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_quiz")),
    )


# ─────────────────────────────────────────────────────────────────────────────
# NOTES HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@require_not_banned
@require_not_maintenance
async def notes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "📝 *Notes Manager*\n\nOrganize your study notes:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=notes_keyboard(),
    )


async def note_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "📝 *Create Note*\n\nSend your note title first:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_notes")),
    )
    context.user_data["note_step"] = "title"
    return STATE_NOTE_CREATE


async def note_create_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    step = context.user_data.get("note_step", "title")
    user_id = update.effective_user.id

    if step == "title":
        context.user_data["note_title"] = update.message.text.strip()
        context.user_data["note_step"] = "content"
        await update.message.reply_text(
            f"📝 Title: *{context.user_data['note_title']}*\n\n"
            f"Now send the note content:",
            parse_mode=ParseMode.MARKDOWN,
        )
        return STATE_NOTE_CREATE
    else:
        title = context.user_data.get("note_title", "Untitled")
        content = update.message.text.strip()
        note_id = save_note(user_id, title, content)
        add_history(user_id, "note_created", title)

        await update.message.reply_text(
            f"✅ *Note Saved!*\n\n📌 Title: {title}\n📝 Content preview: {content[:100]}...",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_notes")),
        )
        context.user_data.pop("note_step", None)
        context.user_data.pop("note_title", None)
        return ConversationHandler.END


async def note_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    notes = get_notes(user_id)

    if not notes:
        await update.effective_message.reply_text(
            "📭 You have no notes yet. Create one first!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Create Note", callback_data="note_create")],
                *nav_inline("menu_notes"),
            ]),
        )
        return

    text = f"📝 *Your Notes* ({len(notes)} total)\n\n"
    buttons = []
    for note_id, note in list(notes.items())[:10]:
        title = note.get("title", "Untitled")
        created = note.get("created_at", "")[:10]
        fav = "❤️ " if note.get("is_favorite") else ""
        buttons.append([
            InlineKeyboardButton(
                f"{fav}📝 {title[:30]} ({created})",
                callback_data=f"view_note_{note_id}"
            )
        ])

    buttons.extend(nav_inline("menu_notes"))
    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def note_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "🔍 *Search Notes*\n\nEnter a keyword to search your notes:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_notes")),
    )
    return STATE_NOTE_SEARCH


async def note_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyword = update.message.text.strip().lower()
    user_id = update.effective_user.id
    notes = get_notes(user_id)

    results = {
        k: v for k, v in notes.items()
        if keyword in v.get("title", "").lower() or keyword in v.get("content", "").lower()
    }

    if not results:
        await update.message.reply_text(
            f"🔍 No notes found for: *{keyword}*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_notes")),
        )
        return ConversationHandler.END

    text = f"🔍 *Found {len(results)} note(s) for '{keyword}':*\n\n"
    buttons = []
    for note_id, note in results.items():
        title = note.get("title", "Untitled")
        buttons.append([
            InlineKeyboardButton(f"📝 {title[:35]}", callback_data=f"view_note_{note_id}")
        ])

    buttons.extend(nav_inline("menu_notes"))
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return ConversationHandler.END


async def note_favorites_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    notes = get_notes(user_id)
    favs = {k: v for k, v in notes.items() if v.get("is_favorite")}

    if not favs:
        await update.effective_message.reply_text(
            "❤️ No favorite notes yet. View a note and mark it as favorite!",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_notes")),
        )
        return

    buttons = []
    for note_id, note in favs.items():
        buttons.append([
            InlineKeyboardButton(f"❤️ {note.get('title', 'Untitled')[:35]}",
                                 callback_data=f"view_note_{note_id}")
        ])
    buttons.extend(nav_inline("menu_notes"))
    await update.effective_message.reply_text(
        f"❤️ *Favorite Notes* ({len(favs)} total):",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ─────────────────────────────────────────────────────────────────────────────
# PDF HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@require_not_banned
@require_not_maintenance
async def pdf_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "📄 *PDF Tools*\n\nSend me a PDF file to get started!\n\n"
        "I can analyze, summarize, extract text, generate questions, and more.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=pdf_keyboard(),
    )


@require_not_banned
@require_not_maintenance
async def pdf_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle received PDF document."""
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".pdf"):
        await update.message.reply_text("Please send a valid PDF file.")
        return ConversationHandler.END

    await update.message.reply_text(
        "📄 *PDF Received!*\n\n"
        f"📁 File: {doc.file_name}\n"
        f"📦 Size: {doc.file_size // 1024} KB\n\n"
        "What would you like to do with this PDF?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=pdf_keyboard(),
    )

    context.user_data["pdf_file_id"] = doc.file_id
    context.user_data["pdf_name"] = doc.file_name
    return STATE_PDF_WAIT


async def pdf_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle PDF action selection."""
    query = update.callback_query
    if query:
        await query.answer()
        action = query.data
    else:
        return STATE_PDF_WAIT

    file_id = context.user_data.get("pdf_file_id")
    if not file_id:
        await query.edit_message_text(
            "⚠️ No PDF file found. Please send a PDF file first.",
            reply_markup=InlineKeyboardMarkup(nav_inline("home")),
        )
        return ConversationHandler.END

    action_map = {
        "pdf_summarize": "Create a comprehensive summary",
        "pdf_mcq": "Generate 5 multiple choice questions",
        "pdf_notes": "Create structured study notes",
        "pdf_extract": "Extract and organize all text",
        "pdf_ask": "Answer: What are the main topics covered?",
    }

    if action not in action_map:
        return STATE_PDF_WAIT

    await query.edit_message_text("⏳ Processing your PDF... This may take a moment.")

    try:
        file = await context.bot.get_file(file_id)
        file_bytes = await file.download_as_bytearray()

        prompt = (
            f"I have a PDF document. {action_map[action]}.\n\n"
            f"Note: The PDF binary data is provided. Extract meaningful content and respond accordingly.\n"
            f"If you cannot read the binary, provide a helpful response explaining PDF analysis capabilities."
        )

        response = await call_gemini(
            prompt=prompt,
            image_data=bytes(file_bytes[:50000]),
            image_mime="application/pdf",
        )

        increment_stat(update.effective_user.id, "pdfs_processed")
        add_history(update.effective_user.id, "pdf_" + action.split("_")[1],
                    context.user_data.get("pdf_name", "PDF"))
        context.user_data["last_ai_response"] = response

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Save as Note", callback_data="save_note_ai")],
            *nav_inline("menu_pdf"),
        ])

        await send_long_message(update.effective_message, response, reply_markup=kb)

    except Exception as e:
        logger.error(f"PDF processing error: {e}")
        await update.effective_message.reply_text(
            "⚠️ Failed to process PDF. Please try a smaller file or different format.",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_pdf")),
        )

    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
# MATH HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@require_not_banned
@require_not_maintenance
async def math_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "🧮 *Math Tools*\n\nPower up your math skills with AI!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=math_keyboard(),
    )


async def math_solve_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "🔢 *Math Solver*\n\nSend me any math problem and I'll solve it step by step!\n\n"
        "*Examples:*\n"
        "• Solve: 2x² + 5x - 3 = 0\n"
        "• Integrate: ∫ x² dx\n"
        "• Find the derivative of sin(x²)\n"
        "• Simplify: (3x + 2)(x - 4)",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_math")),
    )
    context.user_data["math_type"] = "solve"
    return STATE_MATH_SOLVE


async def math_formula_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "📐 *Formula Reference*\n\nAsk for any math formula or concept!\n\n"
        "*Examples:*\n"
        "• Quadratic formula\n"
        "• Pythagorean theorem\n"
        "• Integration by parts\n"
        "• Law of cosines",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_math")),
    )
    context.user_data["math_type"] = "formula"
    return STATE_MATH_SOLVE


async def math_graph_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "📈 *Graph Analysis*\n\nDescribe a function and I'll analyze its graph!\n\n"
        "*Examples:*\n"
        "• y = x² - 4x + 4\n"
        "• y = sin(x)\n"
        "• y = 1/x",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_math")),
    )
    context.user_data["math_type"] = "graph"
    return STATE_MATH_SOLVE


async def math_calc_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "🧮 *Calculator*\n\nSend me a calculation to evaluate!\n\n"
        "*Examples:*\n"
        "• 15% of 2500\n"
        "• Compound interest: P=1000, r=5%, n=2 years\n"
        "• Convert 75°F to Celsius",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_math")),
    )
    context.user_data["math_type"] = "calc"
    return STATE_MATH_SOLVE


async def math_solve_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    problem = update.message.text.strip()
    math_type = context.user_data.get("math_type", "solve")
    user_id = update.effective_user.id

    loading_msg = await loading_message(update.message)
    await send_typing(context, update.effective_chat.id)

    prompts = {
        "solve": (
            f"Solve this math problem with detailed step-by-step working:\n\n{problem}\n\n"
            f"Format with:\n"
            f"📌 Problem Restatement\n"
            f"🔢 Step-by-Step Solution\n"
            f"✅ Final Answer\n"
            f"💡 Key Concepts Used\n"
            f"🔍 Verification (if applicable)"
        ),
        "formula": (
            f"Provide the formula/concept for: {problem}\n\n"
            f"Include:\n"
            f"📐 Formula with proper notation\n"
            f"📖 Variables explained\n"
            f"💡 When to use it\n"
            f"📌 Example application\n"
            f"🔗 Related formulas"
        ),
        "graph": (
            f"Analyze the graph of: {problem}\n\n"
            f"Include:\n"
            f"📈 Function type and shape\n"
            f"📌 Key points (intercepts, vertex, asymptotes)\n"
            f"📊 Domain and range\n"
            f"🔼 Increasing/decreasing intervals\n"
            f"💡 Graph description"
        ),
        "calc": (
            f"Calculate and solve: {problem}\n\n"
            f"Show all working steps clearly with the final numerical answer."
        ),
    }

    prompt = prompts.get(math_type, prompts["solve"])
    response = await call_gemini(prompt, temperature=0.3)
    increment_stat(user_id, "ai_calls")
    add_history(user_id, "math_" + math_type, problem[:80])

    try:
        await loading_msg.delete()
    except Exception:
        pass

    context.user_data["last_ai_response"] = response
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Save as Note", callback_data="save_note_ai"),
         InlineKeyboardButton("📌 Bookmark", callback_data="bookmark_last")],
        *nav_inline("menu_math"),
    ])
    await send_long_message(update.message, response, reply_markup=kb)
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
# TRANSLATE HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@require_not_banned
@require_not_maintenance
async def translate_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "🌐 *Translation Hub*\n\nTranslate text to 100+ languages!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=translate_keyboard(),
    )


async def translate_detect_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "🔍 *Detect Language*\n\nSend the text you want to detect:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_translate")),
    )
    context.user_data["translate_action"] = "detect"
    return STATE_TRANSLATE_TEXT


async def translate_text_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "🌍 *Translate Text*\n\nSend the text you want to translate:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_translate")),
    )
    context.user_data["translate_action"] = "translate"
    return STATE_TRANSLATE_TEXT


async def translate_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    action = context.user_data.get("translate_action", "detect")
    text_to_process = update.message.text.strip()

    if action == "detect":
        loading_msg = await loading_message(update.message)
        await send_typing(context, update.effective_chat.id)

        prompt = (
            f"Detect the language of this text and provide detailed info:\n\n'{text_to_process}'\n\n"
            f"Format:\n"
            f"🌍 Detected Language: [name]\n"
            f"🔤 Language Code: [code]\n"
            f"📊 Confidence: [high/medium/low]\n"
            f"🌐 Region/Variant: [if applicable]\n"
            f"💡 Fun fact: [one interesting fact about this language]"
        )
        response = await call_gemini(prompt, temperature=0.2)
        try:
            await loading_msg.delete()
        except Exception:
            pass
        await send_long_message(update.message, response,
                                reply_markup=InlineKeyboardMarkup(nav_inline("menu_translate")))
        return ConversationHandler.END

    elif action == "translate":
        context.user_data["translate_source_text"] = text_to_process
        await update.message.reply_text(
            "🌍 Select target language:",
            reply_markup=language_keyboard(),
        )
        return STATE_TRANSLATE_LANG
    return ConversationHandler.END


async def translate_language_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    lang_code = query.data.replace("setlang_", "")
    lang_name = next((k for k, v in LANGUAGES.items() if v == lang_code), lang_code)
    source_text = context.user_data.get("translate_source_text", "")

    if not source_text:
        await query.edit_message_text("⚠️ No text to translate.")
        return ConversationHandler.END

    await query.edit_message_text(f"⏳ Translating to {lang_name}...")

    prompt = (
        f"Translate the following text to {lang_name} ({lang_code}):\n\n"
        f"'{source_text}'\n\n"
        f"Format:\n"
        f"🌍 *Translation ({lang_name}):*\n[translated text]\n\n"
        f"📝 *Original:*\n{source_text}\n\n"
        f"💡 *Notes:* [any important translation notes]"
    )

    response = await call_gemini(prompt, temperature=0.2)
    add_history(update.effective_user.id, "translate", f"→{lang_name}")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Translate Again", callback_data="translate_text")],
        *nav_inline("menu_translate"),
    ])
    await query.edit_message_text(
        response,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb,
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
# AI FEATURES (ESSAY, LETTER, CODE, GRAMMAR, etc.)
# ─────────────────────────────────────────────────────────────────────────────

async def ai_essay_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "📝 *Essay Writer*\n\nSend the essay topic or title:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
    )
    return STATE_ESSAY_TOPIC


async def ai_essay_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    topic = update.message.text.strip()
    loading_msg = await loading_message(update.message)
    await send_typing(context, update.effective_chat.id)

    prompt = (
        f"Write a well-structured academic essay on: {topic}\n\n"
        f"Include:\n"
        f"1. 📌 Introduction with thesis statement\n"
        f"2. 📖 Body paragraphs (3-4) with evidence\n"
        f"3. 🔄 Counterargument (if applicable)\n"
        f"4. ✅ Conclusion with summary\n\n"
        f"Use formal language, smooth transitions, and citations where relevant."
    )

    response = await call_gemini(prompt, temperature=0.6)
    increment_stat(update.effective_user.id, "ai_calls")

    try:
        await loading_msg.delete()
    except Exception:
        pass

    context.user_data["last_ai_response"] = response
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Save as Note", callback_data="save_note_ai")],
        *nav_inline("menu_ai"),
    ])
    await send_long_message(update.message, response, reply_markup=kb)
    return ConversationHandler.END


async def ai_letter_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "📨 *Letter / Application Writer*\n\n"
        "Describe what letter you need:\n\n"
        "*Examples:*\n"
        "• Job application for Software Engineer\n"
        "• Leave application to school principal\n"
        "• Complaint letter to manager\n"
        "• University admission request",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
    )
    return STATE_LETTER_TOPIC


async def ai_letter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    request = update.message.text.strip()
    loading_msg = await loading_message(update.message)
    await send_typing(context, update.effective_chat.id)

    prompt = (
        f"Write a professional, formal letter/application for:\n\n{request}\n\n"
        f"Format properly with:\n"
        f"• Date and address headers\n"
        f"• Proper salutation\n"
        f"• Clear body paragraphs\n"
        f"• Professional closing\n"
        f"• Signature line\n\n"
        f"Use [Name], [Position], [Date] as placeholders where needed."
    )

    response = await call_gemini(prompt, temperature=0.5)
    increment_stat(update.effective_user.id, "ai_calls")

    try:
        await loading_msg.delete()
    except Exception:
        pass

    context.user_data["last_ai_response"] = response
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Save as Note", callback_data="save_note_ai")],
        *nav_inline("menu_ai"),
    ])
    await send_long_message(update.message, response, reply_markup=kb)
    return ConversationHandler.END


async def ai_grammar_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "✏️ *Grammar Fix*\n\nSend the text you want me to fix:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
    )
    return STATE_GRAMMAR_FIX


async def ai_grammar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    loading_msg = await loading_message(update.message)
    await send_typing(context, update.effective_chat.id)

    prompt = (
        f"Fix grammar, spelling, and style in this text:\n\n{text}\n\n"
        f"Format:\n"
        f"✅ *Corrected Text:*\n[fixed text]\n\n"
        f"📋 *Changes Made:*\n[list specific corrections]\n\n"
        f"💡 *Style Suggestions:* [optional improvements]"
    )

    response = await call_gemini(prompt, temperature=0.3)
    increment_stat(update.effective_user.id, "ai_calls")

    try:
        await loading_msg.delete()
    except Exception:
        pass

    await send_long_message(
        update.message, response,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai"))
    )
    return ConversationHandler.END


async def ai_code_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "💻 *Code Generator*\n\nDescribe what code you need:\n\n"
        "*Examples:*\n"
        "• Python function to sort a list by multiple keys\n"
        "• JavaScript async fetch with error handling\n"
        "• SQL query to find duplicate records\n"
        "• React component for a login form",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
    )
    context.user_data["code_action"] = "generate"
    return STATE_CODE_REQUEST


async def ai_explain_code_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "🔍 *Code Explainer*\n\nSend the code you want explained:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
    )
    context.user_data["code_action"] = "explain"
    return STATE_CODE_REQUEST


async def ai_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    request = update.message.text.strip()
    action = context.user_data.get("code_action", "generate")
    loading_msg = await loading_message(update.message)
    await send_typing(context, update.effective_chat.id)

    if action == "generate":
        prompt = (
            f"Generate clean, well-commented code for:\n\n{request}\n\n"
            f"Include:\n"
            f"• Complete working code\n"
            f"• Clear inline comments\n"
            f"• Usage example\n"
            f"• Error handling\n"
            f"• Brief explanation of approach"
        )
    else:
        prompt = (
            f"Explain this code in detail:\n\n```\n{request}\n```\n\n"
            f"Cover:\n"
            f"• What it does (overview)\n"
            f"• Line-by-line breakdown\n"
            f"• Key algorithms/patterns used\n"
            f"• Potential issues or improvements\n"
            f"• Time/space complexity (if applicable)"
        )

    response = await call_gemini(prompt, temperature=0.4)
    increment_stat(update.effective_user.id, "ai_calls")

    try:
        await loading_msg.delete()
    except Exception:
        pass

    context.user_data["last_ai_response"] = response
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Save as Note", callback_data="save_note_ai")],
        *nav_inline("menu_ai"),
    ])
    await send_long_message(update.message, response, reply_markup=kb)
    return ConversationHandler.END


async def ai_rewrite_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "✍️ *Rewrite Text*\n\nSend the text you want rewritten:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
    )
    return STATE_REWRITE_TEXT


async def ai_rewrite_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    loading_msg = await loading_message(update.message)
    await send_typing(context, update.effective_chat.id)

    prompt = (
        f"Rewrite this text to improve clarity, flow, and engagement:\n\n{text}\n\n"
        f"Provide:\n"
        f"✍️ *Rewritten Version:*\n[improved text]\n\n"
        f"📊 *Improvements Made:* [brief list]"
    )

    response = await call_gemini(prompt, temperature=0.6)
    increment_stat(update.effective_user.id, "ai_calls")

    try:
        await loading_msg.delete()
    except Exception:
        pass

    await send_long_message(
        update.message, response,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai"))
    )
    return ConversationHandler.END


async def ai_summarize_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "🔁 *Summarize Text*\n\nSend the text you want summarized:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
    )
    return STATE_SUMMARIZE_TEXT


async def ai_summarize_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    loading_msg = await loading_message(update.message)
    await send_typing(context, update.effective_chat.id)

    prompt = (
        f"Create a concise summary of this text:\n\n{text}\n\n"
        f"Format:\n"
        f"📋 *Summary:* [2-3 sentence overview]\n\n"
        f"🔑 *Key Points:*\n[bullet points]\n\n"
        f"📊 *Word count reduced:* [original] → [summary]"
    )

    response = await call_gemini(prompt, temperature=0.4)
    increment_stat(update.effective_user.id, "ai_calls")

    try:
        await loading_msg.delete()
    except Exception:
        pass

    await send_long_message(
        update.message, response,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai"))
    )
    return ConversationHandler.END


async def ai_story_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "📖 *Story Writer*\n\nDescribe the story you want:\n\n"
        "*Examples:*\n"
        "• A student who discovers a magic library\n"
        "• Sci-fi story about AI and humanity\n"
        "• Short mystery set in a school",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
    )
    return STATE_STORY_TOPIC


async def ai_story_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prompt_text = update.message.text.strip()
    loading_msg = await loading_message(update.message)
    await send_typing(context, update.effective_chat.id)

    prompt = (
        f"Write a creative, engaging short story about:\n\n{prompt_text}\n\n"
        f"Include:\n"
        f"• Compelling opening hook\n"
        f"• Well-developed characters\n"
        f"• Rising action and conflict\n"
        f"• Satisfying resolution\n"
        f"• Vivid descriptions\n\n"
        f"Length: 400-600 words."
    )

    response = await call_gemini(prompt, temperature=0.8)
    increment_stat(update.effective_user.id, "ai_calls")

    try:
        await loading_msg.delete()
    except Exception:
        pass

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Save as Note", callback_data="save_note_ai")],
        *nav_inline("menu_ai"),
    ])
    await send_long_message(update.message, response, reply_markup=kb)
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
# OCR — IMAGE HANDLING
# ─────────────────────────────────────────────────────────────────────────────

@require_not_banned
@require_not_maintenance
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages — OCR and image analysis."""
    user = update.effective_user
    photo = update.message.photo[-1]  # Largest available

    await update.message.reply_text(
        "🖼️ *Image received!* Analyzing...\n\n"
        "Choose what to do:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 Extract Text (OCR)", callback_data="ocr_extract"),
             InlineKeyboardButton("❓ Ask Question", callback_data="ocr_question")],
            [InlineKeyboardButton("📋 Summarize Image", callback_data="ocr_summarize"),
             InlineKeyboardButton("🔍 Analyze Image", callback_data="ocr_analyze")],
            *nav_inline("home"),
        ]),
    )
    context.user_data["ocr_photo_id"] = photo.file_id


async def ocr_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle OCR action selection."""
    query = update.callback_query
    await query.answer()
    action = query.data

    photo_id = context.user_data.get("ocr_photo_id")
    if not photo_id:
        await query.edit_message_text("⚠️ No image found. Please send an image first.")
        return ConversationHandler.END

    if action == "ocr_question":
        await query.edit_message_text(
            "❓ What question do you have about this image?",
            reply_markup=InlineKeyboardMarkup(nav_inline("home")),
        )
        context.user_data["ocr_action"] = "question"
        return STATE_OCR_QUESTION
    else:
        prompts = {
            "ocr_extract": (
                "Extract ALL text from this image. Format it clearly, preserving structure. "
                "If it's handwritten, do your best to interpret it accurately. "
                "Label sections if multiple are present."
            ),
            "ocr_summarize": (
                "Summarize the content of this image. "
                "If it contains text, summarize the text. "
                "If it's a diagram or chart, describe and summarize what it shows."
            ),
            "ocr_analyze": (
                "Provide a detailed analysis of this image:\n"
                "1. What type of image is this?\n"
                "2. Main content/subject\n"
                "3. Any text present\n"
                "4. Key information conveyed\n"
                "5. Educational relevance (if any)"
            ),
        }

        prompt = prompts.get(action, "Describe this image.")
        await query.edit_message_text("⏳ Processing image...")

        try:
            file = await context.bot.get_file(photo_id)
            file_bytes = await file.download_as_bytearray()
            response = await call_gemini(
                prompt=prompt,
                image_data=bytes(file_bytes),
                image_mime="image/jpeg",
            )
            increment_stat(update.effective_user.id, "ai_calls")
            add_history(update.effective_user.id, "ocr", action)

            context.user_data["last_ai_response"] = response
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Save as Note", callback_data="save_note_ai")],
                *nav_inline("home"),
            ])
            await send_long_message(update.effective_message, response, reply_markup=kb)
        except Exception as e:
            logger.error(f"OCR error: {e}")
            await update.effective_message.reply_text(
                "⚠️ Failed to analyze image. Please try again.",
                reply_markup=InlineKeyboardMarkup(nav_inline("home")),
            )
        return ConversationHandler.END


async def ocr_question_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle question about image."""
    question = update.message.text.strip()
    photo_id = context.user_data.get("ocr_photo_id")

    if not photo_id:
        await update.message.reply_text("⚠️ Image not found.")
        return ConversationHandler.END

    loading_msg = await loading_message(update.message)
    await send_typing(context, update.effective_chat.id)

    try:
        file = await context.bot.get_file(photo_id)
        file_bytes = await file.download_as_bytearray()
        response = await call_gemini(
            prompt=question,
            image_data=bytes(file_bytes),
            image_mime="image/jpeg",
        )
        increment_stat(update.effective_user.id, "ai_calls")

        try:
            await loading_msg.delete()
        except Exception:
            pass

        await send_long_message(
            update.message, response,
            reply_markup=InlineKeyboardMarkup(nav_inline("home"))
        )
    except Exception as e:
        logger.error(f"OCR question error: {e}")
        try:
            await loading_msg.delete()
        except Exception:
            pass
        await update.message.reply_text("⚠️ Failed to process. Please try again.")

    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
# PROFILE HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@require_not_banned
async def profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_data = get_user(user.id)
    streak = update_streak(user.id)

    joined = user_data.get("joined_at", "")[:10]
    premium = "💎 Premium" if user_data.get("is_premium") else "Free"
    total_msg = user_data.get("total_messages", 0)
    ai_calls = user_data.get("ai_calls", 0)
    quizzes = user_data.get("quizzes_taken", 0)
    notes = user_data.get("notes_created", 0)
    referrals = user_data.get("referral_count", 0)

    text = (
        f"👤 *Your Profile*\n\n"
        f"{'─' * 25}\n"
        f"🏷️ Name: *{user.full_name}*\n"
        f"🆔 ID: `{user.id}`\n"
        f"📅 Joined: {joined}\n"
        f"💎 Plan: {premium}\n"
        f"{'─' * 25}\n"
        f"📊 *Statistics:*\n"
        f"💬 Messages: {total_msg}\n"
        f"🤖 AI Calls: {ai_calls}\n"
        f"🧠 Quizzes: {quizzes}\n"
        f"📝 Notes: {notes}\n"
        f"{'─' * 25}\n"
        f"🔥 Streak: *{streak} day{'s' if streak != 1 else ''}*\n"
        f"🔗 Referrals: {referrals}\n"
    )

    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=profile_keyboard(user.id),
    )


async def profile_achievements_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_data = get_user(user_id)

    total_msg = user_data.get("total_messages", 0)
    quizzes = user_data.get("quizzes_taken", 0)
    notes = user_data.get("notes_created", 0)
    streak = user_data.get("streak", 0)

    achievements = []
    if total_msg >= 1:
        achievements.append("🎯 First Steps — Sent first message")
    if total_msg >= 100:
        achievements.append("💬 Chatterbox — 100+ messages")
    if total_msg >= 500:
        achievements.append("🗣️ Power User — 500+ messages")
    if quizzes >= 1:
        achievements.append("🧠 Quiz Taker — First quiz completed")
    if quizzes >= 10:
        achievements.append("🏆 Quiz Master — 10+ quizzes")
    if notes >= 1:
        achievements.append("📝 Note Taker — First note created")
    if notes >= 20:
        achievements.append("📚 Archivist — 20+ notes")
    if streak >= 3:
        achievements.append("🔥 On Fire — 3-day streak")
    if streak >= 7:
        achievements.append("⚡ Weekly Warrior — 7-day streak")
    if streak >= 30:
        achievements.append("🌟 Dedicated Scholar — 30-day streak")

    if not achievements:
        achievements = ["🚀 Start using the bot to earn achievements!"]

    text = f"🏆 *Your Achievements* ({len(achievements)} earned)\n\n"
    text += "\n".join(f"• {a}" for a in achievements)

    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_profile")),
    )


async def profile_referral_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    referrals = user_data.get("referral_count", 0)
    bot_username = context.bot.username

    ref_link = f"[t.me](https://t.me/{bot_username}?start=ref_{user_id})"
    text = (
        f"🔗 *Your Referral Link*\n\n"
        f"Share this link with friends:\n"
        f"`{ref_link}`\n\n"
        f"👥 Total referrals: *{referrals}*\n\n"
        f"💡 *Benefits:*\n"
        f"• Track your referrals\n"
        f"• Help friends discover AI study tools\n"
        f"• Earn recognition on leaderboard"
    )

    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Share Link", url=f"[t.me](https://t.me/share/url?url={ref_link})")],
            *nav_inline("menu_profile"),
        ]),
    )


async def profile_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    history = get_history(user_id, 10)

    text = "🕐 *Recent Activity*\n\n"
    if history:
        for item in history:
            action = item.get("action", "unknown")
            data = item.get("data", "")[:50]
            timestamp = item.get("timestamp", "")[:10]
            text += f"• `{action}`: {data} ({timestamp})\n"
    else:
        text += "No activity yet. Start using the bot!"

    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("menu_profile")),
    )


async def profile_premium_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "💎 *Premium Plan*\n\n"
        "Unlock the full power of AI Study Bot!\n\n"
        "✅ *Premium Features:*\n"
        "• 🚀 Unlimited AI calls\n"
        "• 📄 Advanced PDF processing\n"
        "• 🧠 Unlimited quizzes\n"
        "• 📝 Unlimited notes storage\n"
        "• ⚡ Priority response speed\n"
        "• 🎯 Personalized study plans\n"
        "• 📊 Advanced analytics\n\n"
        "💰 *Pricing:* Contact admin for pricing.\n\n"
        "📩 Contact the admin to upgrade!"
    )
    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 Contact Admin", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}" if CHANNEL_USERNAME else "https://t.me/")],
            *nav_inline("menu_profile"),
        ]),
    )


# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@require_not_banned
async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    lang = user_data.get("language", "en")
    notif = "ON 🔔" if user_data.get("notifications", True) else "OFF 🔕"

    text = (
        f"⚙️ *Settings*\n\n"
        f"🌍 Language: *{lang}*\n"
        f"🔔 Notifications: *{notif}*\n\n"
        f"Configure your preferences below:"
    )

    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=settings_keyboard(),
    )


async def settings_notifications_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    user_data = get_user(user_id)
    current = user_data.get("notifications", True)
    new_val = not current

    fb_update(f"users/{user_id}", {"notifications": new_val})
    status = "enabled 🔔" if new_val else "disabled 🔕"

    await query.edit_message_text(
        f"✅ Notifications *{status}* successfully.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("settings")),
    )


async def settings_reset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ Yes, Reset All Data", callback_data="confirm_reset")],
        [InlineKeyboardButton("❌ Cancel", callback_data="settings")],
    ])
    await query.edit_message_text(
        "⚠️ *Reset Data*\n\nAre you sure you want to reset all your data?\n\n"
        "This will delete:\n• All notes\n• History\n• Quiz scores\n• Bookmarks\n• Conversation history\n\n"
        "This action *cannot be undone!*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb,
    )


async def confirm_reset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    # Delete user data (preserve core user profile)
    fb_delete(f"notes/{user_id}")
    fb_delete(f"history/{user_id}")
    fb_delete(f"quiz_scores/{user_id}")
    fb_delete(f"bookmarks/{user_id}")
    fb_delete(f"conversations/{user_id}")
    fb_delete(f"exams/{user_id}")

    # Reset stats
    fb_update(f"users/{user_id}", {
        "total_messages": 0,
        "ai_calls": 0,
        "quizzes_taken": 0,
        "notes_created": 0,
        "pdfs_processed": 0,
        "quiz_score": 0,
    })

    await query.edit_message_text(
        "✅ *All data has been reset successfully.*\n\nStart fresh!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("home")),
    )


async def settings_privacy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🔒 *Privacy Settings*\n\n"
        "Your data is stored securely in our Firebase database.\n\n"
        "📋 *What we store:*\n"
        "• Basic profile (name, username, ID)\n"
        "• Usage statistics\n"
        "• Your notes and bookmarks\n"
        "• AI conversation history\n"
        "• Quiz scores\n\n"
        "🗑️ *Delete your data:* Use the Reset Data option.\n\n"
        "🔐 All data is private and not shared with third parties.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("settings")),
    )


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@owner_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"🛡️ *Admin Panel*\n\nWelcome, Owner! {EMOJI['crown']}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_keyboard(),
    )


@owner_only
async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "📢 *Broadcast Message*\n\nSend the message to broadcast to all users:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="admin")
        ]]),
    )
    return STATE_BROADCAST


async def admin_broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != OWNER_ID:
        return ConversationHandler.END

    broadcast_text = update.message.text.strip()
    users_data = fb_get("users") or {}

    sent = 0
    failed = 0
    total = len(users_data)

    status_msg = await update.message.reply_text(f"📢 Broadcasting to {total} users...")

    for uid, user_data in users_data.items():
        if user_data.get("is_banned"):
            continue
        if not user_data.get("notifications", True):
            continue
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=f"📢 *Announcement*\n\n{broadcast_text}",
                parse_mode=ParseMode.MARKDOWN,
            )
            sent += 1
        except Forbidden:
            failed += 1
        except Exception as e:
            logger.error(f"Broadcast error for {uid}: {e}")
            failed += 1
        await asyncio.sleep(0.05)  # Rate limit

    await status_msg.edit_text(
        f"✅ *Broadcast Complete*\n\n"
        f"✉️ Sent: {sent}\n❌ Failed: {failed}\n📊 Total: {total}",
        parse_mode=ParseMode.MARKDOWN,
    )
    return ConversationHandler.END


@owner_only
async def admin_ban_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "🔨 *Ban User*\n\nSend the User ID to ban:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin")]]),
    )
    return STATE_BAN_USER


async def admin_ban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != OWNER_ID:
        return ConversationHandler.END
    try:
        ban_id = int(update.message.text.strip())
        fb_update(f"users/{ban_id}", {"is_banned": True})
        await update.message.reply_text(
            f"✅ User `{ban_id}` has been banned.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(nav_inline("admin")),
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID.")
    return ConversationHandler.END


@owner_only
async def admin_unban_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "✅ *Unban User*\n\nSend the User ID to unban:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin")]]),
    )
    return STATE_UNBAN_USER


async def admin_unban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != OWNER_ID:
        return ConversationHandler.END
    try:
        unban_id = int(update.message.text.strip())
        fb_update(f"users/{unban_id}", {"is_banned": False})
        await update.message.reply_text(
            f"✅ User `{unban_id}` has been unbanned.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(nav_inline("admin")),
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID.")
    return ConversationHandler.END


async def admin_usercount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    users = fb_get("users") or {}
    total = len(users)
    banned = sum(1 for u in users.values() if isinstance(u, dict) and u.get("is_banned"))
    premium = sum(1 for u in users.values() if isinstance(u, dict) and u.get("is_premium"))

    await update.effective_message.reply_text(
        f"👥 *User Statistics*\n\n"
        f"Total Users: *{total}*\n"
        f"Banned: *{banned}*\n"
        f"Premium: *{premium}*\n"
        f"Active: *{total - banned}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("admin")),
    )


async def admin_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    users = fb_get("users") or {}
    total_users = len(users)
    total_ai_calls = sum(
        u.get("ai_calls", 0) for u in users.values() if isinstance(u, dict)
    )
    total_quizzes = sum(
        u.get("quizzes_taken", 0) for u in users.values() if isinstance(u, dict)
    )
    total_notes = sum(
        u.get("notes_created", 0) for u in users.values() if isinstance(u, dict)
    )

    await update.effective_message.reply_text(
        f"📊 *Bot Statistics*\n\n"
        f"👥 Total Users: *{total_users}*\n"
        f"🤖 Total AI Calls: *{total_ai_calls}*\n"
        f"🧠 Total Quizzes: *{total_quizzes}*\n"
        f"📝 Total Notes: *{total_notes}*\n"
        f"🤖 AI Model: *{AI_MODEL}*\n"
        f"📦 Bot Version: *{BOT_VERSION}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("admin")),
    )


async def admin_maintenance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if update.effective_user.id != OWNER_ID:
        return

    current = is_maintenance()
    fb_set("settings/maintenance", not current)
    status = "ENABLED 🔧" if not current else "DISABLED ✅"

    await query.edit_message_text(
        f"🔧 Maintenance mode *{status}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("admin")),
    )


async def admin_logs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        return

    logs_data = fb_get("error_logs") or {}
    if isinstance(logs_data, dict):
        logs = list(logs_data.values())[-5:]
    else:
        logs = []

    text = "📋 *Recent Error Logs*\n\n"
    if logs:
        for log in reversed(logs):
            text += f"⚠️ `{log.get('error', 'Unknown')[:80]}`\n"
            text += f"📅 {log.get('timestamp', '')[:19]}\n\n"
    else:
        text += "No recent errors. Bot is running smoothly! ✅"

    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(nav_inline("admin")),
    )


async def admin_restart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if update.effective_user.id != OWNER_ID:
        return

    await query.edit_message_text("🔄 Restarting bot...")
    logger.info("Admin initiated restart")
    await asyncio.sleep(1)
    os.execv(sys.executable, [sys.executable] + sys.argv)


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY COMMANDS
# ─────────────────────────────────────────────────────────────────────────────

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear AI conversation history."""
    clear_conversation(update.effective_user.id)
    await update.message.reply_text(
        "🗑️ *Chat history cleared!*\n\nStarting fresh conversation.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def streak_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    streak = update_streak(user_id)
    user_data = get_user(user_id)
    last_date = user_data.get("last_streak_date", "N/A")

    if streak >= 30:
        emoji = "🌟"
    elif streak >= 7:
        emoji = "⚡"
    elif streak >= 3:
        emoji = "🔥"
    else:
        emoji = "📅"

    await update.message.reply_text(
        f"{emoji} *Your Study Streak*\n\n"
        f"🔥 Current streak: *{streak} day{'s' if streak != 1 else ''}*\n"
        f"📅 Last active: {last_date}\n\n"
        f"{'Keep it going! You are on fire! 🔥' if streak >= 3 else 'Study daily to build your streak!'}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await quiz_leaderboard_handler(update, context)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await profile_menu(update, context)


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK QUERY ROUTER
# ─────────────────────────────────────────────────────────────────────────────

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Central callback query router."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user

    if is_banned(user.id) and data != "home":
        await query.edit_message_text("🚫 You are banned.")
        return ConversationHandler.END

    # ── Navigation ──
    if data == "home":
        text = (
            f"🏠 *Main Menu*\n\nWelcome back, *{user.first_name}*!\n\n"
            f"Use the keyboard below to choose a feature:"
        )
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass
        await query.message.reply_text(
            "👇 Select a feature from the menu:",
            reply_markup=main_keyboard(),
        )
        context.user_data.clear()
        return ConversationHandler.END

    elif data == "close":
        try:
            await query.message.delete()
        except Exception:
            await query.edit_message_text("✅ Closed.")
        return ConversationHandler.END

    elif data == "help":
        text = (
            "📖 *Help Guide*\n\n"
            "• 🤖 AI Chat — Ask anything\n"
            "• 📚 Study — Explanations, MCQ, flashcards\n"
            "• 🧠 Quiz — Test your knowledge\n"
            "• 📝 Notes — Manage study notes\n"
            "• 📄 PDF — Analyze documents\n"
            "• 🧮 Math — Solve problems\n"
            "• 🌐 Translate — 100+ languages\n"
            "• 👤 Profile — Stats & achievements\n\n"
            "Send an image for OCR extraction!"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                      reply_markup=InlineKeyboardMarkup(nav_inline("home")))
        return ConversationHandler.END

    # ── Menu navigations ──
    elif data == "menu_study":
        await query.edit_message_text(
            "📚 *Study Tools*\n\nChoose what you'd like to do:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=study_keyboard(),
        )
        return ConversationHandler.END

    elif data == "menu_quiz":
        await query.edit_message_text(
            "🧠 *Quiz Center*\n\nTest your knowledge!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=quiz_keyboard(),
        )
        return ConversationHandler.END

    elif data == "menu_notes":
        await query.edit_message_text(
            "📝 *Notes Manager*\n\nOrganize your study notes:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=notes_keyboard(),
        )
        return ConversationHandler.END

    elif data == "menu_pdf":
        await query.edit_message_text(
            "📄 *PDF Tools*\n\nSend me a PDF file to get started!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=pdf_keyboard(),
        )
        return ConversationHandler.END

    elif data == "menu_math":
        await query.edit_message_text(
            "🧮 *Math Tools*\n\nPower up your math skills!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=math_keyboard(),
        )
        return ConversationHandler.END

    elif data == "menu_translate":
        await query.edit_message_text(
            "🌐 *Translation Hub*\n\nTranslate text to 100+ languages!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=translate_keyboard(),
        )
        return ConversationHandler.END

    elif data == "menu_profile":
        await profile_menu(update, context)
        return ConversationHandler.END

    elif data == "menu_ai":
        await query.edit_message_text(
            "🤖 *AI Features*\n\nChoose an AI tool:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ai_keyboard(),
        )
        return ConversationHandler.END

    # ── Study callbacks ──
    elif data == "study_explain":
        await query.edit_message_text(
            "📖 Send the topic/chapter you want explained:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
        )
        context.user_data["conv_state"] = "study_explain"
        return STATE_STUDY_CHAPTER

    elif data == "study_summary":
        await query.edit_message_text(
            "📋 Send the topic for a summary:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
        )
        context.user_data["conv_state"] = "study_summary"
        return STATE_STUDY_SUMMARY

    elif data == "study_mcq":
        await query.edit_message_text(
            "❓ Send the topic for MCQ generation:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
        )
        context.user_data["conv_state"] = "study_mcq"
        return STATE_STUDY_MCQ

    elif data == "study_short_notes":
        await query.edit_message_text(
            "📝 Send the topic for short notes:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
        )
        context.user_data["conv_state"] = "study_summary"
        return STATE_STUDY_SUMMARY

    elif data == "study_flashcards":
        await query.edit_message_text(
            "🃏 Send the topic for flashcards:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
        )
        return STATE_FLASHCARD_TOPIC

    elif data == "study_planner":
        await query.edit_message_text(
            "📅 What subject do you want to plan?",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
        )
        context.user_data["planner_step"] = "topic"
        return STATE_PLANNER_TOPIC

    elif data == "study_reminder":
        await query.edit_message_text(
            "🔔 *Study Reminder*\n\n"
            "Set daily reminders using the bot's notification system.\n\n"
            "💡 *Tip:* Study at the same time each day to build a habit!\n\n"
            "To set reminders, use your phone's built-in reminder app and schedule bot check-ins.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
        )
        return ConversationHandler.END

    elif data == "study_bookmarks":
        bookmarks = get_bookmarks(user.id)
        if not bookmarks:
            await query.edit_message_text(
                "📌 No bookmarks yet. Save AI responses using the Bookmark button!",
                reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
            )
        else:
            text = f"📌 *Your Bookmarks* ({len(bookmarks)})\n\n"
            for _, bm in bookmarks[:5]:
                title = bm.get("title", "Untitled")
                ts = bm.get("timestamp", "")[:10]
                text += f"• {title[:40]} ({ts})\n"
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
            )
        return ConversationHandler.END

    elif data == "study_exam_countdown":
        await query.edit_message_text(
            "⏰ Send the exam name to add a countdown:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_study")),
        )
        return STATE_EXAM_NAME

    # ── Quiz callbacks ──
    elif data == "quiz_start":
        await query.edit_message_text(
            "🧠 What topic would you like to be quizzed on?",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_quiz")),
        )
        context.user_data["quiz_type"] = "custom"
        return STATE_QUIZ_TOPIC

    elif data == "quiz_daily":
        return await quiz_daily_flow(update, context)

    elif data == "quiz_weekly":
        return await quiz_weekly_flow(update, context)

    elif data == "quiz_leaderboard":
        await quiz_leaderboard_handler(update, context)
        return ConversationHandler.END

    elif data == "quiz_results":
        await quiz_results_handler(update, context)
        return ConversationHandler.END

    elif data == "quiz_next":
        return await quiz_next_callback(update, context)

    elif data.startswith("quiz_ans_"):
        return await quiz_answer_callback(update, context)

    # ── AI callbacks ──
    elif data == "ai_chat":
        await query.edit_message_text(
            "🤖 *AI Chat Mode*\n\nType your message below! I'm ready to help.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ Clear History", callback_data="ai_clear_history")],
                *nav_inline("home"),
            ]),
        )
        return STATE_AI_CHAT

    elif data == "ai_clear_history":
        clear_conversation(user.id)
        try:
            await query.edit_message_text(
                "✅ Chat history cleared! Start a fresh conversation.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💬 Start Chatting", callback_data="ai_chat")
                ]]),
            )
        except Exception:
            pass
        return ConversationHandler.END

    elif data in ("ai_homework", "ai_explain"):
        await query.edit_message_text(
            "💡 Ask me anything — homework, concepts, problems!\n\nType your question:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
        )
        return STATE_AI_CHAT

    elif data == "ai_math":
        await query.edit_message_text(
            "🧮 Send me a math problem to solve step by step:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
        )
        context.user_data["math_type"] = "solve"
        return STATE_MATH_SOLVE

    elif data == "ai_grammar":
        await query.edit_message_text(
            "✏️ Send the text you want grammar-checked:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
        )
        return STATE_GRAMMAR_FIX

    elif data == "ai_essay":
        await query.edit_message_text(
            "📝 Send the essay topic:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
        )
        return STATE_ESSAY_TOPIC

    elif data in ("ai_letter", "ai_paragraph"):
        await query.edit_message_text(
            "📨 Describe the letter/application you need:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
        )
        return STATE_LETTER_TOPIC

    elif data == "ai_story":
        await query.edit_message_text(
            "📖 Describe the story you want written:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
        )
        return STATE_STORY_TOPIC

    elif data == "ai_summarize":
        await query.edit_message_text(
            "🔁 Send the text you want summarized:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
        )
        return STATE_SUMMARIZE_TEXT

    elif data == "ai_rewrite":
        await query.edit_message_text(
            "✍️ Send the text you want rewritten:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
        )
        return STATE_REWRITE_TEXT

    elif data == "ai_code":
        await query.edit_message_text(
            "💻 Describe the code you need generated:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
        )
        context.user_data["code_action"] = "generate"
        return STATE_CODE_REQUEST

    elif data == "ai_explain_code":
        await query.edit_message_text(
            "🔍 Send the code you want explained:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_ai")),
        )
        context.user_data["code_action"] = "explain"
        return STATE_CODE_REQUEST

    elif data == "ai_ocr":
        await query.edit_message_text(
            "🖼️ *OCR — Image to Text*\n\nSend me an image and I'll extract the text!\n\n"
            "Works with:\n• Printed text\n• Screenshots\n• Handwritten notes (best effort)",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(nav_inline("home")),
        )
        return ConversationHandler.END

    # ── OCR callbacks ──
    elif data in ("ocr_extract", "ocr_summarize", "ocr_analyze"):
        return await ocr_action_callback(update, context)

    elif data == "ocr_question":
        return await ocr_action_callback(update, context)

    # ── Notes callbacks ──
    elif data == "note_create":
        await query.edit_message_text(
            "📝 Send the note title:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_notes")),
        )
        context.user_data["note_step"] = "title"
        return STATE_NOTE_CREATE

    elif data == "note_list":
        await note_list_handler(update, context)
        return ConversationHandler.END

    elif data == "note_search":
        await query.edit_message_text(
            "🔍 Send a keyword to search your notes:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_notes")),
        )
        return STATE_NOTE_SEARCH

    elif data == "note_favorites":
        await note_favorites_handler(update, context)
        return ConversationHandler.END

    elif data == "note_history":
        await profile_history_handler(update, context)
        return ConversationHandler.END

    elif data.startswith("view_note_"):
        note_id = data.replace("view_note_", "")
        notes = get_notes(user.id)
        note = notes.get(note_id)
        if note:
            fav = note.get("is_favorite", False)
            fav_btn = "💔 Unfavorite" if fav else "❤️ Favorite"
            await query.edit_message_text(
                f"📝 *{note.get('title', 'Untitled')}*\n\n{note.get('content', '')}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(fav_btn, callback_data=f"fav_note_{note_id}"),
                     InlineKeyboardButton("🗑️ Delete", callback_data=f"del_note_{note_id}")],
                    *nav_inline("note_list"),
                ]),
            )
        return ConversationHandler.END

    elif data.startswith("fav_note_"):
        note_id = data.replace("fav_note_", "")
        notes = get_notes(user.id)
        note = notes.get(note_id)
        if note:
            new_fav = not note.get("is_favorite", False)
            fb_update(f"notes/{user.id}/{note_id}", {"is_favorite": new_fav})
            status = "added to ❤️ favorites" if new_fav else "removed from favorites"
            await query.answer(f"Note {status}!")
        return ConversationHandler.END

    elif data.startswith("del_note_"):
        note_id = data.replace("del_note_", "")
        delete_note(user.id, note_id)
        await query.edit_message_text(
            "✅ Note deleted.",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_notes")),
        )
        return ConversationHandler.END

    # ── PDF callbacks ──
    elif data in ("pdf_summarize", "pdf_mcq", "pdf_notes", "pdf_extract", "pdf_ask"):
        return await pdf_action_handler(update, context)

    # ── Math callbacks ──
    elif data == "math_step":
        await query.edit_message_text(
            "🔢 Send me a math problem to solve step by step:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_math")),
        )
        context.user_data["math_type"] = "solve"
        return STATE_MATH_SOLVE

    elif data == "math_formula":
        await query.edit_message_text(
            "📐 Send the formula or concept you want:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_math")),
        )
        context.user_data["math_type"] = "formula"
        return STATE_MATH_SOLVE

    elif data == "math_graph":
        await query.edit_message_text(
            "📈 Send a function to analyze its graph:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_math")),
        )
        context.user_data["math_type"] = "graph"
        return STATE_MATH_SOLVE

    elif data == "math_calc":
        await query.edit_message_text(
            "🧮 Send a calculation to evaluate:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_math")),
        )
        context.user_data["math_type"] = "calc"
        return STATE_MATH_SOLVE

    # ── Translate callbacks ──
    elif data == "translate_detect":
        await query.edit_message_text(
            "🔍 Send the text to detect its language:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_translate")),
        )
        context.user_data["translate_action"] = "detect"
        return STATE_TRANSLATE_TEXT

    elif data == "translate_text":
        await query.edit_message_text(
            "🌍 Send the text you want to translate:",
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_translate")),
        )
        context.user_data["translate_action"] = "translate"
        return STATE_TRANSLATE_TEXT

    elif data.startswith("setlang_"):
        if context.user_data.get("translate_action") == "translate":
            return await translate_language_callback(update, context)
        else:
            lang_code = data.replace("setlang_", "")
            fb_update(f"users/{user.id}", {"language": lang_code})
            lang_name = next((k for k, v in LANGUAGES.items() if v == lang_code), lang_code)
            await query.edit_message_text(
                f"✅ Language set to *{lang_name}*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(nav_inline("settings")),
            )
            return ConversationHandler.END

    # ── Profile callbacks ──
    elif data == "profile_stats":
        await profile_menu(update, context)
        return ConversationHandler.END

    elif data == "profile_history":
        await profile_history_handler(update, context)
        return ConversationHandler.END

    elif data == "profile_streak":
        streak = update_streak(user.id)
        await query.edit_message_text(
            f"🔥 *Your Streak: {streak} days*\n\nKeep studying daily!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(nav_inline("menu_profile")),
        )
        return ConversationHandler.END

    elif data == "profile_achievements":
        await profile_achievements_handler(update, context)
        return ConversationHandler.END

    elif data == "profile_referral":
        await profile_referral_handler(update, context)
        return ConversationHandler.END

    elif data == "profile_premium":
        await profile_premium_handler(update, context)
        return ConversationHandler.END

    # ── Settings callbacks ──
    elif data == "settings":
        user_data = get_user(user.id)
        lang = user_data.get("language", "en")
        notif = "ON 🔔" if user_data.get("notifications", True) else "OFF 🔕"
        await query.edit_message_text(
            f"⚙️ *Settings*\n\n🌍 Language: *{lang}*\n🔔 Notifications: *{notif}*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=settings_keyboard(),
        )
        return ConversationHandler.END

    elif data == "settings_language":
        await query.edit_message_text(
            "🌍 *Select Language:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=language_keyboard(),
        )
        return ConversationHandler.END

    elif data == "settings_notifications":
        await settings_notifications_callback(update, context)
        return ConversationHandler.END

    elif data == "settings_privacy":
        await settings_privacy_callback(update, context)
        return ConversationHandler.END

    elif data == "settings_reset":
        await settings_reset_callback(update, context)
        return ConversationHandler.END

    elif data == "confirm_reset":
        await confirm_reset_callback(update, context)
        return ConversationHandler.END

    # ── Admin callbacks ──
    elif data == "admin":
        if user.id == OWNER_ID:
            await query.edit_message_text(
                f"🛡️ *Admin Panel*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_keyboard(),
            )
        return ConversationHandler.END

    elif data == "admin_broadcast":
        if user.id != OWNER_ID:
            return ConversationHandler.END
        await query.edit_message_text(
            "📢 Send the broadcast message:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin")]]),
        )
        return STATE_BROADCAST

    elif data == "admin_ban":
        if user.id != OWNER_ID:
            return ConversationHandler.END
        await query.edit_message_text(
            "🔨 Send the User ID to ban:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin")]]),
        )
        return STATE_BAN_USER

    elif data == "admin_unban":
        if user.id != OWNER_ID:
            return ConversationHandler.END
        await query.edit_message_text(
            "✅ Send the User ID to unban:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin")]]),
        )
        return STATE_UNBAN_USER

    elif data == "admin_usercount":
        await admin_usercount_handler(update, context)
        return ConversationHandler.END

    elif data == "admin_stats":
        await admin_stats_handler(update, context)
        return ConversationHandler.END

    elif data == "admin_maintenance":
        await admin_maintenance_callback(update, context)
        return ConversationHandler.END

    elif data == "admin_logs":
        await admin_logs_handler(update, context)
        return ConversationHandler.END

    elif data == "admin_restart":
        await admin_restart_callback(update, context)
        return ConversationHandler.END

    # ── Save helpers ──
    elif data == "save_note_ai":
        last_response = context.user_data.get("last_ai_response", "")
        if last_response:
            title = f"AI Note {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            save_note(user.id, title, last_response[:2000])
            await query.answer("✅ Saved as note!")
        else:
            await query.answer("⚠️ Nothing to save.")
        return ConversationHandler.END

    elif data == "bookmark_last":
        last_response = context.user_data.get("last_ai_response", "")
        if last_response:
            title = f"Bookmark {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            save_bookmark(user.id, title, last_response[:1000])
            await query.answer("📌 Bookmarked!")
        else:
            await query.answer("⚠️ Nothing to bookmark.")
        return ConversationHandler.END

    # ── Force join check ──
    elif data == "check_join":
        joined = await check_force_join(update, context)
        if joined:
            await query.edit_message_text(
                "✅ *Welcome!* You can now use the bot.\n\nUse /start to begin!",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await query.answer("⚠️ Please join the channel first!", show_alert=True)
        return ConversationHandler.END

    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
# REPLY KEYBOARD ROUTER
# ─────────────────────────────────────────────────────────────────────────────

@require_not_banned
@require_not_maintenance
async def reply_keyboard_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Route reply keyboard button presses."""
    text = update.message.text

    if text == "🏠 Home":
        return await home_handler(update, context)
    elif text == "🤖 AI Chat":
        return await ai_chat_entry(update, context)
    elif text == "📚 Study":
        await study_menu(update, context)
        return ConversationHandler.END
    elif text == "📝 Notes":
        await notes_menu(update, context)
        return ConversationHandler.END
    elif text == "📄 PDF":
        await pdf_menu(update, context)
        return ConversationHandler.END
    elif text == "🧮 Math Solver":
        await math_menu(update, context)
        return ConversationHandler.END
    elif text == "🧠 Quiz":
        await quiz_menu(update, context)
        return ConversationHandler.END
    elif text == "🌐 Translate":
        await translate_menu(update, context)
        return ConversationHandler.END
    elif text == "👤 Profile":
        await profile_menu(update, context)
        return ConversationHandler.END
    elif text == "⚙ Settings":
        await settings_menu(update, context)
        return ConversationHandler.END
    elif text == "📷 OCR":
        # Directly prompt user to send an image for OCR
        context.user_data["conv_state"] = "ocr"
        await update.message.reply_text(
            "📷 *OCR — Image to Text*\n\nSend me an image and I'll extract all the text from it!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(nav_inline("home")),
        )
        return STATE_OCR_QUESTION
    elif text == "🎓 Homework Help":
        context.user_data["conv_state"] = "ai_homework"
        await update.message.reply_text(
            "🎓 *Homework Help*\n\nDescribe your homework problem or question and I'll help you solve it step by step!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(nav_inline("home")),
        )
        return STATE_AI_CHAT
    elif text == "📖 Explain Topic":
        context.user_data["conv_state"] = "ai_explain"
        await update.message.reply_text(
            "📖 *Explain Topic*\n\nWhat topic or concept would you like me to explain?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(nav_inline("home")),
        )
        return STATE_STUDY_CHAPTER
    elif text == "📝 Text Summary":
        context.user_data["conv_state"] = "ai_summarize"
        await update.message.reply_text(
            "📝 *Text Summary*\n\nPaste the text you want me to summarize:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(nav_inline("home")),
        )
        return STATE_SUMMARIZE_TEXT
    elif text == "✍ Essay Writer":
        context.user_data["conv_state"] = "ai_essay"
        await update.message.reply_text(
            "✍ *Essay Writer*\n\nWhat topic should I write an essay about? You can also specify length, style, or any requirements.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(nav_inline("home")),
        )
        return STATE_ESSAY_TOPIC
    elif text == "💻 Code Assistant":
        context.user_data["conv_state"] = "ai_code"
        await update.message.reply_text(
            "💻 *Code Assistant*\n\nDescribe what you need — I can write, explain, debug, or review code in any language!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(nav_inline("home")),
        )
        return STATE_CODE_REQUEST

    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
# ERROR HANDLER
# ─────────────────────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    error = context.error
    logger.error(f"Exception: {error}", exc_info=True)

    try:
        error_entry = {
            "error": str(error)[:500],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "traceback": traceback.format_exc()[:1000],
        }
        fb_push("error_logs", error_entry)
    except Exception:
        pass

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ An error occurred. Please try again or use /start to restart.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Home", callback_data="home")
                ]]),
            )
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# UNKNOWN MESSAGE FALLBACK
# ─────────────────────────────────────────────────────────────────────────────

async def unknown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown messages with AI fallback."""
    user = update.effective_user
    if is_banned(user.id):
        return
    if is_maintenance() and user.id != OWNER_ID:
        return

    text = update.message.text or ""
    if not text or text.startswith("/"):
        return

    # Check force join
    if not await force_join_gate(update, context):
        return

    # If not in conversation, treat as AI chat
    if is_rate_limited(user.id):
        await update.message.reply_text(
            "⚡ Please slow down! Wait a moment before sending more messages."
        )
        return

    await send_typing(context, update.effective_chat.id)
    loading_msg = await loading_message(update.message)

    history = get_conversation_history(user.id)
    system_prompt = (
        "You are a helpful AI study assistant for students. "
        "Help with studies, explain concepts, solve problems. "
        "Be encouraging and educational."
    )

    response = await call_gemini(
        prompt=text,
        system_instruction=system_prompt,
        history=history,
    )

    history.append({"role": "user", "text": text})
    history.append({"role": "model", "text": response})
    save_conversation_history(user.id, history)
    increment_stat(user.id, "ai_calls")
    add_history(user.id, "ai_fallback", text[:80])
    update_streak(user.id)

    try:
        await loading_msg.delete()
    except Exception:
        pass

    context.user_data["last_ai_response"] = response
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Save as Note", callback_data="save_note_ai"),
         InlineKeyboardButton("🗑️ Clear Chat", callback_data="ai_clear_history")],
        [InlineKeyboardButton("🏠 Home", callback_data="home")],
    ])
    await send_long_message(update.message, response, reply_markup=kb)


# ─────────────────────────────────────────────────────────────────────────────
# BOT COMMANDS SETUP
# ─────────────────────────────────────────────────────────────────────────────

async def post_init(application: Application) -> None:
    """Post-initialization setup."""
    commands = [
        BotCommand("start", "🚀 Start the bot"),
        BotCommand("help", "📖 Help guide"),
        BotCommand("chat", "🤖 AI chat"),
        BotCommand("study", "📚 Study tools"),
        BotCommand("quiz", "🧠 Take a quiz"),
        BotCommand("notes", "📝 Manage notes"),
        BotCommand("math", "🧮 Math solver"),
        BotCommand("translate", "🌐 Translate text"),
        BotCommand("profile", "👤 View profile"),
        BotCommand("settings", "⚙️ Bot settings"),
        BotCommand("streak", "🔥 Check streak"),
        BotCommand("leaderboard", "🏆 Leaderboard"),
        BotCommand("clear", "🗑️ Clear chat history"),
        BotCommand("admin", "🛡️ Admin panel (owner)"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ Bot commands registered")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APPLICATION BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_app() -> Application:
    """Build and configure the Telegram application."""
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .concurrent_updates(True)
        .build()
    )

    # ── Main conversation handler ──
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            CommandHandler("chat", ai_chat_entry),
            CommandHandler("study", study_menu),
            CommandHandler("quiz", quiz_menu),
            CommandHandler("notes", notes_menu),
            CommandHandler("math", math_menu),
            CommandHandler("translate", translate_menu),
            CommandHandler("profile", profile_menu),
            CommandHandler("settings", settings_menu),
            # Reply keyboard
            MessageHandler(
                filters.Regex(
                    r"^(🏠 Home|🤖 AI Chat|📚 Study|📄 PDF|📝 Notes|🧮 Math Solver|🧠 Quiz|📷 OCR|🎓 Homework Help|📖 Explain Topic|📝 Text Summary|🌐 Translate|✍ Essay Writer|💻 Code Assistant|👤 Profile|⚙ Settings)$"
                ),
                reply_keyboard_router,
            ),
            # Callback router as entry
            CallbackQueryHandler(callback_router),
            # Photo handler
            MessageHandler(filters.PHOTO, photo_handler),
            # PDF handler
            MessageHandler(filters.Document.PDF, pdf_receive),
        ],
        states={
            STATE_AI_CHAT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat_message),
                CallbackQueryHandler(callback_router),
            ],
            STATE_STUDY_CHAPTER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, study_explain_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_STUDY_SUMMARY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, study_summary_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_STUDY_MCQ: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, study_mcq_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_NOTE_CREATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, note_create_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_NOTE_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, note_search_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_MATH_SOLVE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, math_solve_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_TRANSLATE_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, translate_text_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_TRANSLATE_LANG: [
                CallbackQueryHandler(callback_router),
            ],
            STATE_QUIZ_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, quiz_topic_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_QUIZ_ANSWER: [
                CallbackQueryHandler(callback_router),
            ],
            STATE_PDF_WAIT: [
                CallbackQueryHandler(callback_router),
                MessageHandler(filters.Document.PDF, pdf_receive),
            ],
            STATE_EXAM_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, exam_name_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_EXAM_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, exam_date_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_PLANNER_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, study_planner_topic),
                CallbackQueryHandler(callback_router),
            ],
            STATE_PLANNER_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, study_planner_days),
                CallbackQueryHandler(callback_router),
            ],
            STATE_BROADCAST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_BAN_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_ban_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_UNBAN_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_unban_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_OCR_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ocr_question_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_ESSAY_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ai_essay_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_LETTER_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ai_letter_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_CODE_REQUEST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ai_code_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_GRAMMAR_FIX: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ai_grammar_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_REWRITE_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ai_rewrite_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_SUMMARIZE_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ai_summarize_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_STORY_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ai_story_handler),
                CallbackQueryHandler(callback_router),
            ],
            STATE_FLASHCARD_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, study_flashcards_handler),
                CallbackQueryHandler(callback_router),
            ],
        },
        fallbacks=[
            CommandHandler("start", start_command),
            CommandHandler("help", help_command),
            MessageHandler(
                filters.Regex(r"^🏠 Home$"),
                home_handler,
            ),
            CallbackQueryHandler(callback_router, pattern="^home$"),
        ],
        allow_reentry=True,
        name="main_conv",
    )

    # ── Standalone command handlers ──
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("streak", streak_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CommandHandler("stats", stats_command))

    # ── Fallback for any uncaught text ──
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        unknown_handler,
    ))

    # ── Error handler ──
    app.add_error_handler(error_handler)

    return app


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Main entry point."""
    logger.info(f"🚀 Starting AI Study Bot v{BOT_VERSION}")

    # Initialize Firebase
    init_firebase()
    logger.info("✅ Firebase connected")

    # Verify Gemini
    get_gemini_client()
    logger.info("✅ Gemini AI client ready")

    # Build and run
    app = build_app()
    logger.info("✅ Bot application built")
    logger.info("🤖 Bot is now running (polling)...")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False,
    )


if __name__ == "__main__":
    main()
