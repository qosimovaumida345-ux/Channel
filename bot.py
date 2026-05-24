import asyncio
import json
import logging
import os
import sqlite3
import time
import aiohttp
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import base64
from io import BytesIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN  = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")   # masalan: @mening_kanalim
ADMIN_ID   = int(os.getenv("ADMIN_ID", "0"))
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "your_openrouter_api_key")

# ──────────────────────────────────────────────
# UC NARXLAR RO'YXATI
# ──────────────────────────────────────────────
UC_PRICES_TEXT = (
    "⚡️ sdzABU UC XIZMATI\n"
    "⚡️ UC tushish vaqti 1-7 minut\n\n"
    "\" ⚠️ <i>Diqqat suhbatni davom ettirish orqali\n"
    "UC servis shartlariga rozilik bildirgan bo'lasiz</i> \"\n\n"
    "💳 orqali\n\n"
    "<tg-emoji emoji-id=\"5411181829627685641\">🪙</tg-emoji> 60 - 13.000 UZS\n"
    "<tg-emoji emoji-id=\"5411181829627685641\">🪙</tg-emoji> 120 - 26.000 UZS\n"
    "<tg-emoji emoji-id=\"5411181829627685641\">🪙</tg-emoji> 180 - 39.000 UZS\n"
    "<tg-emoji emoji-id=\"5411181829627685641\">🪙</tg-emoji> 325 - 58.000 UZS\n"
    "<tg-emoji emoji-id=\"5411181829627685641\">🪙</tg-emoji> 385 - 70.000 UZS 💳\n"
    "<tg-emoji emoji-id=\"5411181829627685641\">🪙</tg-emoji> 660 - 112.000 UZS\n"
    "<tg-emoji emoji-id=\"5411181829627685641\">🪙</tg-emoji> 720 - 125.000 UZS 💳\n"
    "<tg-emoji emoji-id=\"5411181829627685641\">🪙</tg-emoji> 985 - 170.000 UZS\n"
    "<tg-emoji emoji-id=\"5411181829627685641\">🪙</tg-emoji> 1320 - 224.000 UZS\n"
    "<tg-emoji emoji-id=\"5411181829627685641\">🪙</tg-emoji> 1800 - 290.000 UZS\n"
    "<tg-emoji emoji-id=\"5411181829627685641\">🪙</tg-emoji> 2125 - 350.000 UZS\n"
    "<tg-emoji emoji-id=\"5411181829627685641\">🪙</tg-emoji> 3850 - 570.000 UZS\n"
    "<tg-emoji emoji-id=\"5411181829627685641\">🪙</tg-emoji> 8100 - 1.120.000 UZS\n\n"
    "Orginal UC admin lichkasi 👇"
)

PAYMENT_TEXT = (
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "💳 <b>TO'LOV KARTA MA'LUMOTLARI</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Quyidagi karta raqamiga to'lovni amalga oshiring va chekni (skrinshot) adminga yuboring:\n\n"
    "💳 KARTA RAQAMI:\n"
    "👉 <code>5614 6846 0556 8557</code> 👈\n\n"
    "⚠️ <i>Diqqat: To'lov to'liq o'tganiga ishonch hosil qilgandan so'ng, tasdiqlovni admin @WebDev999 ga yuboring. Barcha xaridlarimiz 100% kafolatlangan!</i>\n"
    "━━━━━━━━━━━━━━━━━━━━━"
)

# ──────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect("bot.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id          INTEGER PRIMARY KEY,
                name        TEXT,
                description TEXT,
                credentials TEXT,
                price       REAL,
                tier        TEXT,
                status      TEXT DEFAULT 'available',
                rank        TEXT DEFAULT '',
                level       INTEGER DEFAULT 0,
                skin_count  INTEGER DEFAULT 0,
                season      INTEGER DEFAULT 0,
                uc_balance  INTEGER DEFAULT 0,
                server      TEXT DEFAULT '',
                rp_level    INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS given (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                user_id    INTEGER,
                given_at   TEXT
            );
            CREATE TABLE IF NOT EXISTS milestones (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                target      INTEGER UNIQUE,
                triggered   INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS claimed_users (
                user_id INTEGER PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS users (
                user_id       INTEGER PRIMARY KEY,
                referrer_id   INTEGER,
                invites_count INTEGER DEFAULT 0
            );
        """)
        try:
            conn.execute("ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0")
            conn.execute("ALTER TABLE users ADD COLUMN streak INTEGER DEFAULT 0")
            conn.execute("ALTER TABLE users ADD COLUMN last_daily TEXT")
            conn.execute("ALTER TABLE users ADD COLUMN lucky_spin_at TEXT")
        except sqlite3.OperationalError:
            pass # Already exists

def get_user(user_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

def create_user(user_id: int, referrer_id: int = None):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO users (user_id, referrer_id) VALUES (?, ?)", (user_id, referrer_id))

def add_invite(user_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET invites_count = invites_count + 1, points = points + 50 WHERE user_id=?", (user_id,))

def check_daily(user_id: int):
    user = get_user(user_id)
    if not user: return False, 0
    now = datetime.now()
    if not user["last_daily"]:
        return True, 1
    last_d = datetime.fromisoformat(user["last_daily"])
    if now.date() > last_d.date():
        if now.date() == last_d.date() + timedelta(days=1):
            return True, user["streak"] + 1
        return True, 1
    return False, user["streak"]

def claim_daily(user_id: int, new_streak: int, points: int):
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE users SET last_daily=?, streak=?, points=points+? WHERE user_id=?", (now, new_streak, points, user_id))

def load_accounts_from_json(path="pubg-accounts.json"):
    """JSON fayldan accountlarni DB ga bir marta yuklaydi."""
    with get_conn() as conn:
        already = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        if already > 0:
            return

    with open(path) as f:
        raw = json.load(f)["pubg_accounts"]

    rows = []
    for item in raw:
        # Yangi object format
        if isinstance(item, dict):
            rows.append((
                item.get("name", ""),
                item.get("description", ""),
                item.get("credentials", ""),
                item.get("price", 0),
                item.get("tier", "Random"),
                item.get("status", "available"),
                item.get("rank", ""),
                item.get("level", 0),
                item.get("skin_count", 0),
                item.get("season", 0),
                item.get("uc_balance", 0),
                item.get("server", ""),
                item.get("rp_level", 0),
            ))
        # Eski array format (backward compat)
        elif isinstance(item, list) and len(item) >= 7:
            rows.append((
                item[1], item[2], item[3], item[4], item[5], item[6],
                "", 0, 0, 0, 0, "", 0
            ))

    with get_conn() as conn:
        conn.executemany(
            """INSERT INTO accounts
               (name,description,credentials,price,tier,status,
                rank,level,skin_count,season,uc_balance,server,rp_level)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )
    logger.info(f"{len(rows)} ta account DB ga yuklandi.")

def next_available_account():
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE status='available' ORDER BY id LIMIT 1"
        ).fetchone()
    return row

def mark_given(account_id: int, user_id: int):
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE accounts SET status='given' WHERE id=?", (account_id,))
        conn.execute(
            "INSERT INTO given (account_id,user_id,given_at) VALUES (?,?,?)",
            (account_id, user_id, now),
        )

def has_claimed(user_id: int) -> bool:
    with get_conn() as conn:
        r = conn.execute(
            "SELECT 1 FROM claimed_users WHERE user_id=?", (user_id,)
        ).fetchone()
    return r is not None

def set_banned(user_id: int):
    with get_conn() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY)")
        conn.execute("INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)", (user_id,))

def remove_banned(user_id: int):
    with get_conn() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY)")
        conn.execute("DELETE FROM banned_users WHERE user_id=?", (user_id,))

def is_banned(user_id: int) -> bool:
    with get_conn() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY)")
        row = conn.execute("SELECT 1 FROM banned_users WHERE user_id=?", (user_id,)).fetchone()
        return row is not None

def set_claimed(user_id: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO claimed_users (user_id) VALUES (?)", (user_id,)
        )

def stats():
    with get_conn() as conn:
        total     = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        available = conn.execute("SELECT COUNT(*) FROM accounts WHERE status='available'").fetchone()[0]
        given_cnt = conn.execute("SELECT COUNT(*) FROM given").fetchone()[0]
    return total, available, given_cnt

def add_milestone(target: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO milestones (target) VALUES (?)", (target,)
        )

def get_pending_milestones(current_subs: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM milestones WHERE triggered=0 AND target<=? ORDER BY target",
            (current_subs,),
        ).fetchall()
    return rows

def mark_milestone_done(milestone_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE milestones SET triggered=1 WHERE id=?", (milestone_id,)
        )

# ──────────────────────────────────────────────
# RANK EMOJI HELPER
# ──────────────────────────────────────────────
def rank_emoji(rank: str) -> str:
    r = rank.lower() if rank else ""
    if "conqueror" in r:     return "👑"
    if "ace dominator" in r: return "🔱"
    if "ace master" in r:    return "⚜️"
    if "ace" in r:           return "🏆"
    if "crown" in r:         return "👸"
    if "diamond" in r:       return "💎"
    if "platinum" in r:      return "🥇"
    if "gold" in r:          return "🥈"
    if "silver" in r:        return "🥉"
    if "bronze" in r:        return "🪙"
    return "🎖️"

def tier_emoji(tier: str) -> str:
    t = tier.lower() if tier else ""
    if "ultimate" in t:   return "🌟"
    if "mythic" in t:     return "🔮"
    if "collector" in t:  return "💫"
    if "legendary" in t:  return "⭐"
    if "elite" in t:      return "🏅"
    if "premium" in t:    return "💠"
    return "📦"

# ──────────────────────────────────────────────
# ACCOUNT TEXT FORMATTER
# ──────────────────────────────────────────────
def account_text(acc) -> str:
    """Account haqida to'liq ma'lumot — emoji bilan."""
    rank_val  = acc["rank"]  if acc["rank"]  else "N/A"
    server    = acc["server"] if acc["server"] else "N/A"
    creds     = acc["credentials"]
    parts     = creds.split(":", 1) if creds else ["", ""]
    email     = parts[0] if len(parts) > 0 else ""
    password  = parts[1] if len(parts) > 1 else ""

    return (
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎮 <b>{acc['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 {acc['description']}\n\n"
        f"{tier_emoji(acc['tier'])} Tier: <b>{acc['tier']}</b>\n"
        f"💰 Narxi: <b>{acc['price']:,.0f} so'm</b>\n"
        f"{rank_emoji(rank_val)} Rank: <b>{rank_val}</b>\n"
        f"📊 Level: <b>{acc['level']}</b>\n"
        f"🎨 Skinlar soni: <b>{acc['skin_count']}</b>\n"
        f"🗓 Season: <b>S{acc['season']}</b>\n"
        f"🪙 UC Balance: <b>{acc['uc_balance']:,}</b>\n"
        f"🌍 Server: <b>{server}</b>\n"
        f"🎫 RP Level: <b>{acc['rp_level']}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔑 <b>Login ma'lumotlari:</b>\n"
        f"📧 Email: <code>{email}</code>\n"
        f"🔒 Parol: <code>{password}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ <i>Ushbu ma'lumotni hech kim bilan ulashmang!</i>"
    )

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
async def is_subscribed(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

# ──────────────────────────────────────────────
# ROUTER
# ──────────────────────────────────────────────
router = Router()

@router.message(Command("start"))
async def cmd_start(msg: Message, bot: Bot):
    user_id = msg.from_user.id
    if is_banned(user_id):
        return
        
    parts = msg.text.split()
    referrer_id = None
    if len(parts) > 1 and parts[1].isdigit():
        ref = int(parts[1])
        if ref != user_id:
            referrer_id = ref
            
    create_user(user_id, referrer_id)

    total, available, _ = stats()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}"),
        ],
        [
            InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub"),
        ],
        [
            InlineKeyboardButton(text="📋 MENU", callback_data="main_menu"),
        ],
    ])
    await msg.answer(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎮 <b>PUBG Account Giveaway Bot</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎁 Bepul PUBG account olish uchun:\n\n"
        f"1️⃣ Kanalga obuna bo'l\n"
        f"2️⃣ «✅ Tekshirish» tugmasini bos\n"
        f"3️⃣ Accountni ol va o'yna!\n\n"
        f"📋 Barcha funksiyalar uchun «MENU» tugmasini bosing!\n\n"
        f"📦 Jami accountlar: <b>{total:,}</b>\n"
        f"✅ Hali mavjud: <b>{available:,}</b>\n\n"
        f"📢 Kanal: {CHANNEL_ID}\n"
        f"📺 YouTube: youtube.com/@sdzABU\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=kb,
        parse_mode="HTML",
    )

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Akkaunt Sotish (Trade)", callback_data="trade_start"),
        ],
        [
            InlineKeyboardButton(text="🎁 Kunlik Bonus", callback_data="menu_daily"),
            InlineKeyboardButton(text="🎰 Omad G'ildiragi", callback_data="menu_spin"),
        ],
        [
            InlineKeyboardButton(text="🛍 Ballar Do'koni", callback_data="menu_shop"),
            InlineKeyboardButton(text="🏆 Top Reyting", callback_data="menu_leaderboard"),
        ],
        [
            InlineKeyboardButton(text="👤 Profilim", callback_data="my_profile"),
            InlineKeyboardButton(text="🔗 Do'stlarni Taklif", callback_data="my_referrals"),
        ],
        [
            InlineKeyboardButton(text="🪙 UC Narxlari", callback_data="uc_prices"),
            InlineKeyboardButton(text="📊 Statistika", callback_data="public_stats"),
        ],
        [
            InlineKeyboardButton(text="🤖 AI Maslahatchi", callback_data="menu_ai"),
            InlineKeyboardButton(text="📜 Buyruqlar", callback_data="menu_commands"),
        ],
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="go_back_start"),
        ],
    ])
    await call.message.edit_text(
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 <b>ASOSIY MENU</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Quyidagi tugmalardan birini tanlang:\n\n"
        "🛒 <b>Akkaunt Sotish</b> — O'z akkingizni pulga/ballga soting\n"
        "🎁 <b>Kunlik Bonus</b> — Har kuni ball yig'ing\n"
        "🎰 <b>Omad G'ildiragi</b> — Akkaunt yoki ball yutib oling\n"
        "🛍 <b>Do'kon</b> — Ballaringizni sarflang\n"
        "🏆 <b>Top Reyting</b> — Eng ko'p ball yig'ganlar\n"
        "👤 <b>Profil</b> — Balansingiz va streak\n"
        "🔗 <b>Taklif</b> — Do'stlarni taklif qiling\n"
        "🪙 <b>UC</b> — UC narxlari va xarid\n"
        "🤖 <b>AI</b> — PUBG bo'yicha maslahat\n"
        "━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data == "go_back_start")
async def cb_go_back(call: CallbackQuery, bot: Bot):
    total, available, _ = stats()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}"),
        ],
        [
            InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub"),
        ],
        [
            InlineKeyboardButton(text="📋 MENU", callback_data="main_menu"),
        ],
    ])
    await call.message.edit_text(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎮 <b>PUBG Account Giveaway Bot</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎁 Bepul PUBG account olish uchun:\n\n"
        f"1️⃣ Kanalga obuna bo'l\n"
        f"2️⃣ «✅ Tekshirish» tugmasini bos\n"
        f"3️⃣ Accountni ol va o'yna!\n\n"
        f"📋 Barcha funksiyalar uchun «MENU» tugmasini bosing!\n\n"
        f"📦 Jami accountlar: <b>{total:,}</b>\n"
        f"✅ Hali mavjud: <b>{available:,}</b>\n\n"
        f"📢 Kanal: {CHANNEL_ID}\n"
        f"📺 YouTube: youtube.com/@sdzABU\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data == "menu_daily")
async def cb_menu_daily(call: CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)
    if not user: create_user(user_id); user = get_user(user_id)
    can_claim, new_streak = check_daily(user_id)
    if not can_claim:
        await call.message.answer("❌ Siz bugungi bonusni oldingiz!\n⏳ Ertaga yana urinib ko'ring.")
        await call.answer()
        return
    points_won = 10 + (new_streak * 2)
    claim_daily(user_id, new_streak, points_won)
    await call.message.answer(
        f"🎉 <b>Kunlik bonus olindi!</b>\n\n"
        f"💰 Mukofot: <b>+{points_won} ball</b>\n"
        f"🔥 Ketma-ketlik: <b>{new_streak} kun</b>\n\n"
        f"<i>Ertaga ham kiring va ko'proq ball oling!</i>",
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data == "menu_spin")
async def cb_menu_spin(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    user = get_user(user_id)
    if not user: create_user(user_id); user = get_user(user_id)
    now = datetime.now()
    if user and user["lucky_spin_at"]:
        last_s = datetime.fromisoformat(user["lucky_spin_at"])
        if now < last_s + timedelta(hours=12):
            diff = (last_s + timedelta(hours=12)) - now
            h, rem = divmod(diff.seconds, 3600)
            m, _ = divmod(rem, 60)
            await call.message.answer(f"⏳ Siz aylantirgansiz! Keyingi urinish: <b>{h} soat {m} min</b> dan so'ng.", parse_mode="HTML")
            await call.answer()
            return
    with get_conn() as conn:
        conn.execute("UPDATE users SET lucky_spin_at=? WHERE user_id=?", (now.isoformat(), user_id))
    wait_msg = await call.message.answer("🎰 <i>G'ildirak aylanmoqda...</i>", parse_mode="HTML")
    await asyncio.sleep(1)
    chance = random.random()
    if chance < 0.05:
        acc = next_available_account()
        if acc:
            mark_given(acc["id"], user_id)
            await wait_msg.edit_text(f"🎉 <b>JACKPOT! AKKAUNT YUTDINGIZ!</b>\n\n{account_text(acc)}", parse_mode="HTML")
        else:
            with get_conn() as conn: conn.execute("UPDATE users SET points=points+500 WHERE user_id=?", (user_id,))
            await wait_msg.edit_text("🎰 Akkauntlar qolmagan, kompensatsiya: <b>+500 ball!</b>", parse_mode="HTML")
    elif chance < 0.40:
        pts = random.choice([10, 20, 50, 100])
        with get_conn() as conn: conn.execute("UPDATE users SET points=points+? WHERE user_id=?", (pts, user_id))
        await wait_msg.edit_text(f"🎁 Tabriklaymiz, siz <b>{pts} ball</b> yutib oldingiz!", parse_mode="HTML")
    else:
        await wait_msg.edit_text("😔 Afsuski yutmadingiz. 12 soatdan keyin yana urining!", parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "menu_shop")
async def cb_menu_shop(call: CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)
    if not user: create_user(user_id); user = get_user(user_id)
    pts = user['points'] if user and 'points' in user.keys() else 0
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Random Akkaunt (1500 ball)", callback_data="buy_account_1500")],
        [InlineKeyboardButton(text="💎 UC Skidka -20% (5000 ball)", callback_data="buy_uc_5000")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="main_menu")],
    ])
    await call.message.answer(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 <b>BALLAR DO'KONI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Sizning balingiz: <b>{pts} ball</b>\n\n"
        f"Pastdagi tovarlardan xarid qilishingiz mumkin:",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data == "menu_leaderboard")
async def cb_menu_leaderboard(call: CallbackQuery):
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id, points FROM users WHERE points > 0 ORDER BY points DESC LIMIT 10").fetchall()
    if not rows:
        await call.message.answer("📊 Reyting hozircha bo'sh.")
        await call.answer()
        return
    text = "━━━━━━━━━━━━━━━━━━━━━\n🏆 <b>TOP 10 BALL YIG'GANLAR</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, row in enumerate(rows):
        text += f"{medals[i]} <code>{row['user_id']}</code> — <b>{row['points']} ball</b>\n"
    text += "\n<i>O'z o'rningizni ko'tarish uchun Kunlik Bonus va Spin qiling!</i>\n━━━━━━━━━━━━━━━━━━━━━"
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "menu_ai")
async def cb_menu_ai(call: CallbackQuery):
    await call.message.answer(
        "🤖 <b>sdzABU AI Maslahatchi</b>\n\n"
        "Menga PUBG haqida savol bering! Masalan:\n\n"
        "<code>/ai M416 uchun qaysi nishon yaxshi?</code>\n"
        "<code>/ai Crown ga qanday chiqish mumkin?</code>\n"
        "<code>/ai Sensitivity sozlamalari</code>\n\n"
        "<i>Shunchaki /ai va savolni yozing!</i>",
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data == "menu_commands")
async def cb_menu_commands(call: CallbackQuery):
    await call.message.answer(
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📜 <b>BOT BUYRUQLARI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎮 <b>Asosiy:</b>\n"
        "/start — Botni ishga tushirish\n"
        "/daily — Kunlik bonus ball olish\n"
        "/spin — Omad g'ildiragi (12 soatda 1x)\n"
        "/shop — Ballar do'koni\n"
        "/leaderboard — Top reyting\n\n"
        "🛒 <b>Savdo:</b>\n"
        "🛒 Akkaunt Sotish — Menu → Trade tugmasi\n\n"
        "🤖 <b>AI:</b>\n"
        "/ai savol — AI dan maslahat olish\n\n"
        "📊 <b>Ma'lumot:</b>\n"
        "👤 Profilim — Ballar va streak ko'rish\n"
        "📊 Statistika — Bot statistikasi\n"
        "💰 UC Narxlar — UC narxlar ro'yxati\n"
        "👥 Takliflarim — Referral ma'lumotlar\n\n"
        "<i>Barchasi Menu tugmasidan ham foydalanish mumkin!</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data == "check_sub")
async def cb_check_sub(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id

    if has_claimed(user_id):
        await call.answer("Siz allaqachon account oldingiz! ✅", show_alert=True)
        return

    subscribed = await is_subscribed(bot, user_id)
    if not subscribed:
        await call.answer(
            "❌ Siz hali kanalga obuna bo'lmadingiz!\nObuna bo'lib qayta urining.",
            show_alert=True,
        )
        return

    acc = next_available_account()
    if acc is None:
        await call.answer("😔 Hozircha accountlar tugadi. Keyinroq urinib ko'ring.", show_alert=True)
        return

    mark_given(acc["id"], user_id)
    set_claimed(user_id)

    # REFEARRAL TEKSHIRUVI
    user = get_user(user_id)
    if user and user["referrer_id"]:
        try:
            r_id = user["referrer_id"]
            add_invite(r_id)
            r_data = get_user(r_id)
            inv = r_data["invites_count"] if r_data else 0
            if inv > 0 and inv % 15 == 0:
                extra_acc = next_available_account()
                if extra_acc:
                    mark_given(extra_acc["id"], r_id)
                    await bot.send_message(
                        r_id,
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🎉 <b>TABRIKLAYMIZ!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"Sizning ssilkangiz orqali <b>{inv}</b> kishi bizga qo'shildi!\n"
                        f"🏆 Mukofot sifatida sizga maxsus akkaunt berildi:\n\n"
                        f"{account_text(extra_acc)}\n\n"
                        f"🔗 Ko'proq do'stlaringizni taklif qiling — har 15 ta uchun yana akkaunt!",
                        parse_mode="HTML"
                    )
            else:
                qoldi = 15 - (inv % 15)
                progress = '🟩' * (inv % 15) + '⬜' * qoldi
                try:
                    await bot.send_message(
                        r_id,
                        f"✅ Sizning ssilkangiz orqali yana 1 kishi qo'shildi!\n"
                        f"👥 Jami takliflar: <b>{inv}</b>/15\n"
                        f"{progress}\n"
                        f"🎁 Keyingi mukofotga <b>{qoldi}</b> ta qoldi!",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Referral error: {e}")

    await call.message.answer(
        f"🎉 <b>Tabriklaymiz!</b> Sizga account berildi:\n\n{account_text(acc)}",
        parse_mode="HTML",
    )
    await call.answer("✅ Account yuborildi! DM ni tekshiring.", show_alert=True)

@router.callback_query(F.data == "my_referrals")
async def cb_referrals(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    user = get_user(user_id)
    if not user:
        create_user(user_id)
        user = get_user(user_id)
        
    invites = user["invites_count"]
    link = f"https://t.me/{(await bot.get_me()).username}?start={user_id}"
    
    await call.message.answer(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>SHAXSIY TAKLIF SSILKANGIZ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👉 <code>{link}</code>\n\n"
        f"Ushbu ssilkani do'stlaringizga yuboring! Qachonki ular:\n"
        f"1. Botga kirsa\n"
        f"2. Kanalga obuna bo'lsa\n"
        f"3. <b>Birinchi tasodifiy akkauntini olsa</b>\n\n"
        f"Shundagina sizga 1 ta taklif yoziladi.\n"
        f"🎁 <b>Har 15 ta shunday odam uchun sizga AVTOMATIK ravishda LICHKANGIZGA maxsus yopiq premium akkaunt yuboriladi!</b>\n\n"
        f"👥 Hozircha taklif qilgan do'stlaringiz: <b>{invites} ta</b>\n"
        f"📊 Keyingi akkaunt uchun qoldi: <b>{15 - (invites % 15)} ta</b>",
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data == "uc_prices")
async def cb_uc_prices(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 UC SOTIB OLISH", url="https://t.me/WebDev999")],
        [InlineKeyboardButton(text="🔰 AKK SOTIB OLISH", url="https://t.me/sdzAbuPM_AkkSavdo")],
        [InlineKeyboardButton(text="📜 TO'LOV VA QOIDALAR", url="https://t.me/sdzAbuPM_UC")],
    ])
    uc_img = FSInputFile("uc-banner.png")
    await call.message.answer_photo(
        photo=uc_img,
        caption=UC_PRICES_TEXT,
        reply_markup=kb,
        parse_mode="HTML",
    )
    await call.answer()

@router.callback_query(F.data == "public_stats")
async def cb_public_stats(call: CallbackQuery):
    total, available, given_cnt = stats()
    await call.message.answer(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Bot Statistikasi</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Jami accountlar: <b>{total:,}</b>\n"
        f"✅ Mavjud: <b>{available:,}</b>\n"
        f"🎁 Berilgan: <b>{given_cnt:,}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
    )
    await call.answer()

@router.callback_query(F.data == "my_profile")
async def cb_profile(call: CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)
    if not user:
        create_user(user_id)
        user = get_user(user_id)
        
    pts = user['points'] if user and 'points' in user.keys() else 0
    streak = user['streak'] if user and 'streak' in user.keys() else 0
    invites = user['invites_count'] if user and 'invites_count' in user.keys() else 0
    
    await call.message.answer(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>SIZNING PROFILINGIZ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"💰 Ballar: <b>{pts}</b>\n"
        f"🔥 Kunlik ketma-ketlik: <b>{streak} kun</b>\n"
        f"👥 Takliflar: <b>{invites} ta</b>\n\n"
        f"<i>Ball yig'ish uchun /daily yoki /spin qiling!</i>",
        parse_mode="HTML"
    )
    await call.answer()

@router.message(Command("daily"))
async def cmd_daily(msg: Message, **_):
    user_id = msg.from_user.id
    user = get_user(user_id)
    if not user: create_user(user_id)
    can_claim, new_streak = check_daily(user_id)
    
    if not can_claim:
        await msg.answer("❌ Siz bugungi bonusni oldingiz!\n⏳ Ertaga yana urinib ko'ring.")
        return
        
    points_won = 10 + (new_streak * 2)
    claim_daily(user_id, new_streak, points_won)
    
    await msg.answer(
        f"🎉 <b>Kunlik bonus olingandi!</b>\n\n"
        f"💰 Mukofot: <b>+{points_won} ball</b>\n"
        f"🔥 Ketma-ketlik: <b>{new_streak} kun</b>\n\n"
        f"<i>Ertaga ham kiring va ko'proq ball oling!</i>",
        parse_mode="HTML"
    )

import random
@router.message(Command("spin"))
async def cmd_spin(msg: Message, **_):
    user_id = msg.from_user.id
    user = get_user(user_id)
    if not user: create_user(user_id); user = get_user(user_id)
    now = datetime.now()
    
    if user and user["lucky_spin_at"]:
        last_s = datetime.fromisoformat(user["lucky_spin_at"])
        if now < last_s + timedelta(hours=12):
            diff = (last_s + timedelta(hours=12)) - now
            h, rem = divmod(diff.seconds, 3600)
            m, _ = divmod(rem, 60)
            await msg.answer(f"⏳ Siz aylantirgansiz! Keyingi urinish: <b>{h} soat {m} min</b> dan so'ng.", parse_mode="HTML")
            return
            
    with get_conn() as conn:
        conn.execute("UPDATE users SET lucky_spin_at=? WHERE user_id=?", (now.isoformat(), user_id))
        
    wait_msg = await msg.answer("🎰 <i>G'ildirak aylanmoqda...</i>", parse_mode="HTML")
    await asyncio.sleep(1)
    
    chance = random.random()
    if chance < 0.05:
        acc = next_available_account()
        if acc:
            mark_given(acc["id"], user_id)
            await wait_msg.edit_text(f"🎉 <b>JACKPOT! AKKAUNT YUTDINGIZ!</b>\n\n{account_text(acc)}", parse_mode="HTML")
        else:
            with get_conn() as conn: conn.execute("UPDATE users SET points=points+500 WHERE user_id=?", (user_id,))
            await wait_msg.edit_text("🎰 Akkauntlar qolmagan, kompensatsiya: <b>+500 ball!</b>", parse_mode="HTML")
    elif chance < 0.40:
        pts = random.choice([10, 20, 50, 100])
        with get_conn() as conn: conn.execute("UPDATE users SET points=points+? WHERE user_id=?", (pts, user_id))
        await wait_msg.edit_text(f"🎁 Tabriklaymiz, siz <b>{pts} ball</b> yutib oldingiz!", parse_mode="HTML")
    else:
        await wait_msg.edit_text("😔 Afsuski yutmadingiz. 12 soatdan keyin yana urining!", parse_mode="HTML")

@router.message(Command("leaderboard"))
async def cmd_leaderboard(msg: Message, **_):
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id, points FROM users WHERE points > 0 ORDER BY points DESC LIMIT 10").fetchall()
        
    if not rows:
        await msg.answer("📊 Reyting hozircha bo'sh.")
        return
        
    text = "━━━━━━━━━━━━━━━━━━━━━\n🏆 <b>TOP 10 BALL YIG'GANLAR</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, row in enumerate(rows):
        text += f"{medals[i]} <code>{row['user_id']}</code> — <b>{row['points']} ball</b>\n"
    text += "\n<i>O'z o'rningizni ko'tarish uchun /daily va /spin qiling!</i>\n━━━━━━━━━━━━━━━━━━━━━"
    await msg.answer(text, parse_mode="HTML")

@router.message(Command("shop"))
async def cmd_shop(msg: Message, **_):
    user_id = msg.from_user.id
    user = get_user(user_id)
    if not user: create_user(user_id); user = get_user(user_id)
    
    pts = user['points'] if user and 'points' in user.keys() else 0
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Random Akkaunt (1500 ball)", callback_data="buy_account_1500")],
        [InlineKeyboardButton(text="💎 UC Skidka -20% (5000 ball)", callback_data="buy_uc_5000")],
    ])
    await msg.answer(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 <b>BALLAR DO'KONI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Sizning balingiz: <b>{pts} ball</b>\n\n"
        f"Pastdagi tovarlardan xarid qilishingiz mumkin:",
        reply_markup=kb,
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("buy_"))
async def cb_buy(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    user = get_user(user_id)
    pts = user['points'] if user and 'points' in user.keys() else 0
    
    item = call.data
    price = 0
    if item == "buy_account_1500": price = 1500
    elif item == "buy_uc_5000": price = 5000
    
    if pts < price:
        await call.answer("❌ Balingiz yetarli emas! /daily yoki qiling.", show_alert=True)
        return
        
    if item == "buy_account_1500":
        acc = next_available_account()
        if not acc:
            await call.answer("Oluvchi akkauntlar qolmagan, keyinroq urining.", show_alert=True)
            return
        mark_given(acc["id"], user_id)
        with get_conn() as conn: conn.execute("UPDATE users SET points=points-? WHERE user_id=?", (price, user_id))
        await call.message.answer(f"🎉 <b>Xarid muvaffaqiyatli!</b> Siz Akkaunt oldingiz:\n\n{account_text(acc)}", parse_mode="HTML")
        await call.answer("Xarid qilindi!", show_alert=True)
        
    elif item == "buy_uc_5000":
        with get_conn() as conn: conn.execute("UPDATE users SET points=points-? WHERE user_id=?", (price, user_id))
        await call.message.answer("🎉 <b>Xarid muvaffaqiyatli!</b>\n\nSizga -20% UC chegirma berildi. Kun oxirigacha Adminga murojaat qiling va IDingizni ko'rsating: @WebDev999", parse_mode="HTML")
        await call.answer("Xarid qilindi!", show_alert=True)


# ──────────────────────────────────────────────
# TRADE / SELL ACCOUNT (FSM + AI Vision)
# ──────────────────────────────────────────────
class TradeState(StatesGroup):
    waiting_for_credentials = State()
    waiting_for_price = State()
    waiting_for_proof = State()

@router.callback_query(F.data == "trade_start")
async def cb_trade_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer(
        "🛒 <b>AKKAUNT SOTISH YOKI TRADE</b>\n\n"
        "Shu yerda siz o'z PUBG akkauntingizni tizimga sotishingiz, pulga yoki pointsga almashtirishingiz mumkin.\n\n"
        "Qadam 1/3: Iltimos, akkaunt <b>Login va Parolini</b> (email:pass formatida) yuboring.",
        parse_mode="HTML"
    )
    await state.set_state(TradeState.waiting_for_credentials)
    await call.answer()

@router.message(TradeState.waiting_for_credentials)
async def trade_step1(msg: Message, state: FSMContext):
    await state.update_data(credentials=msg.text)
    await msg.answer(
        "Qadam 2/3: Akkauntingiz qancha turadi? Nima xohlaysiz?\n"
        "(Masalan: <b>100,000 UZS</b> (naqd pul) yoki <b>1500 ball</b> (bot balansiga))",
        parse_mode="HTML"
    )
    await state.set_state(TradeState.waiting_for_price)

@router.message(TradeState.waiting_for_price)
async def trade_step2(msg: Message, state: FSMContext):
    await state.update_data(price=msg.text)
    await msg.answer(
        "Qadam 3/3: Akkauntingiz haqiqiyligini tasdiqlovchi <b>SKRINSHOT (Rasm)</b> yoki <b>Video</b> yuboring. \n"
        "<i>(O'yin profilining asosiylari, Level, RP ko'rinib tursin)</i>\n\n"
        "⚠️ Rasm AI tomonidan (Vision tekshiruvi orqali) avtomat tekshiriladi.",
        parse_mode="HTML"
    )
    await state.set_state(TradeState.waiting_for_proof)

async def verify_image_with_ai(base64_img: str) -> dict:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    model = "google/gemini-2.5-flash-8b-exp:free"
    
    data = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text", 
                        "text": "Sen hakam AI. Rasmni ko'rib, u PUBG Mobile o'yinining profili/lobbisi ekanligini tasdiqla. Level, BP, UC kabi detallarga e'tibor ber. Xulosa va ishonch foizini qisqa o'zbek tilida yoz. Agar rostdan PUBG bo'lsa 'VERIFIED: YES' bilan boshla, aks holda 'VERIFIED: NO'."
                    },
                    {
                        "type": "image_url", 
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                    }
                ]
            }
        ]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    return {"result": res["choices"][0]["message"]["content"]}
                elif resp.status == 404:
                    data["model"] = "meta-llama/llama-3.2-90b-vision-instruct:free"
                    async with session.post(url, headers=headers, json=data) as r2:
                        if r2.status == 200:
                            res = await r2.json()
                            return {"result": res["choices"][0]["message"]["content"]}
    except Exception as e:
        logger.error(f"Vision error: {e}")
    
    return {"result": "VERIFIED: PENDING / MANUAL CHECK (AI ulanishda xato yoki model mavjud emas, ammo Admin o'zi tekshiradi.)"}

@router.message(TradeState.waiting_for_proof, F.photo)
async def trade_step3_photo(msg: Message, state: FSMContext, bot: Bot):
    wait_msg = await msg.answer("⏳ <i>Rasmingiz AI Vision orqali tahlil qilinmoqda, kuting...</i>", parse_mode="HTML")
    
    photo = msg.photo[-1]
    file = await bot.get_file(photo.file_id)
    photo_bytes = BytesIO()
    await bot.download_file(file.file_path, photo_bytes)
    b64 = base64.b64encode(photo_bytes.getvalue()).decode()
    
    ai_check = await verify_image_with_ai(b64)
    result_text = ai_check["result"]
    data = await state.get_data()
    uid = msg.from_user.id
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Qabul Qilish", callback_data=f"trade_accept_{uid}")],
        [InlineKeyboardButton(text="❌ Rad Etish / Fake", callback_data=f"trade_reject_{uid}")]
    ])
    
    report = (
        f"━━━━━━━━━━━━━━\n"
        f"🛒 <b>TRADE SO'ROVI (AI VERIFIED)</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 User: <code>{uid}</code>\n"
        f"🔐 Ma'lumot: <code>{data.get('credentials')}</code>\n"
        f"💰 Narx (Sotuv): <b>{data.get('price')}</b>\n\n"
        f"🤖 <b>AI XULOSASI:</b>\n{result_text}"
    )
    
    try:
        await bot.send_photo(ADMIN_ID, photo.file_id, caption=report[:1000], reply_markup=kb, parse_mode="HTML")
        await wait_msg.edit_text("✅ <b>O'tkazildi!</b>\nSkrinshot AI tomonidan tekshirildi va Adminga yuborildi. Qabul qilinsa DM/Ball olasiz.", parse_mode="HTML")
    except Exception as e:
        await wait_msg.edit_text("❌ Xatolik yuz berdi (Ehtimol admin botni bloklagan yoki sozlanmagan).")
        
    await state.clear()

@router.message(TradeState.waiting_for_proof, F.video | F.document)
async def trade_step3_video(msg: Message, state: FSMContext, bot: Bot):
    wait_msg = await msg.answer("⏳ <i>Video yuklanmoqda... (Videolar rasmdek tez o'qilmaydi, adminga yetkazilyapti)</i>", parse_mode="HTML")
    data = await state.get_data()
    uid = msg.from_user.id
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Qabul Qilish", callback_data=f"trade_accept_{uid}")],
        [InlineKeyboardButton(text="❌ Rad Etish / Fake", callback_data=f"trade_reject_{uid}")]
    ])
    
    report = (
        f"━━━━━━━━━━━━━━\n"
        f"🛒 <b>TRADE SO'ROVI (VIDEO/FILE)</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 User: <code>{uid}</code>\n"
        f"🔐 Ma'lumot: <code>{data.get('credentials')}</code>\n"
        f"💰 Narx (Talab): <b>{data.get('price')}</b>\n\n"
        f"🤖 <b>AI XULOSASI:</b> (Video uzatildi). Manual Control qiling!"
    )
    
    if msg.video:
        await bot.send_video(ADMIN_ID, msg.video.file_id, caption=report[:1000], reply_markup=kb, parse_mode="HTML")
    else:
        await bot.send_document(ADMIN_ID, msg.document.file_id, caption=report[:1000], reply_markup=kb, parse_mode="HTML")
        
    await wait_msg.edit_text("✅ <b>Yuborildi!</b>\nIsbot (Video) adminga yetkazildi. Natija tez orada xabar qilinadi.", parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data.startswith("trade_accept_"))
async def cb_trade_accept(call: CallbackQuery, bot: Bot):
    uid = int(call.data.split("_")[2])
    with get_conn() as conn:
        conn.execute("UPDATE users SET points=points+500 WHERE user_id=?", (uid,))
    
    await bot.send_message(
        uid, 
        "🎉 <b>TABRIKLAYMIZ!</b>\n\nSizni Akkauntingiz Admin / AI tomonidan tasdiqlandi va QABUL QILINDI.\n\n"
        "Sizga kompensatsiya sifatida <b>+500 BALL</b> berildi (yoki pul yozgan bo'lsangiz admin siz bilan to'lov uchun bog'lanadi)!", 
        parse_mode="HTML"
    )
    await call.message.edit_reply_markup(reply_markup=None)
    await call.answer("Tasdiqlandi va foydalanuvchiga xabar boradi!", show_alert=True)

@router.callback_query(F.data.startswith("trade_reject_"))
async def cb_trade_reject(call: CallbackQuery, bot: Bot):
    uid = int(call.data.split("_")[2])
    await bot.send_message(
        uid, 
        "❌ <b>RAD ETILDI</b>\n\nSizning Trade so'rovingiz (Akkaunt, narxi yoki tashlagan isbotingiz) AI va Admin tekshiruvidan O'TMADI (Fake yoki mos emas).", 
        parse_mode="HTML"
    )
    await call.message.edit_reply_markup(reply_markup=None)
    await call.answer("Rad etildi!", show_alert=True)

# ──────────────────────────────────────────────
# ADMIN COMMANDS
# ──────────────────────────────────────────────
def admin_only(func):
    async def wrapper(msg: Message, **kwargs):
        if msg.from_user.id != ADMIN_ID:
            await msg.answer("⛔ Ruxsat yo'q.")
            return
        await func(msg, **kwargs)
    return wrapper

@router.message(Command("stats"))
@admin_only
async def cmd_stats(msg: Message, **_):
    total, available, given_cnt = stats()
    await msg.answer(
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Admin Statistika</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Jami accountlar: <b>{total:,}</b>\n"
        f"✅ Mavjud: <b>{available:,}</b>\n"
        f"🎁 Berilgan: <b>{given_cnt:,}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
    )

@router.message(Command("addmilestone"))
@admin_only
async def cmd_add_milestone(msg: Message, **_):
    parts = msg.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await msg.answer("❗ Ishlatish: /addmilestone 1000")
        return
    target = int(parts[1])
    add_milestone(target)
    await msg.answer(f"✅ Milestone qo'shildi: <b>{target:,}</b> obunachi", parse_mode="HTML")

@router.message(Command("sendpromo"))
@admin_only
async def cmd_send_promo(msg: Message, bot: Bot, **_):
    """Kanalga qo'lda promo post yuboradi."""
    await send_promo(bot)
    await msg.answer("✅ Promo post kanalga yuborildi!")

@router.message(Command("senduc"))
@admin_only
async def cmd_send_uc(msg: Message, bot: Bot, **_):
    """Kanalga UC narxlarini qo'lda yuboradi."""
    await send_uc_post(bot)
    await msg.answer("✅ UC narxlar kanalga yuborildi!")

@router.message(Command("sendpayment"))
@admin_only
async def cmd_send_payment(msg: Message, bot: Bot, **_):
    """Guruhga to'lov ma'lumotlarini 1 marotaba tashlaydi."""
    await bot.send_message(
        "@sdzAbuPM_UC",
        PAYMENT_TEXT,
        parse_mode="HTML"
    )
    await msg.answer("✅ To'lov ma'lumotlari @sdzAbuPM_UC guruhiga yuborildi!")

@router.message(Command("setpromo"))
@admin_only
async def cmd_set_promo(msg: Message, **_):
    """Auto promo intervalini soat bilan belgilaydi: /setpromo 6"""
    parts = msg.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await msg.answer("❗ Ishlatish: /setpromo 6  (har 6 soatda bir marta)")
        return
    hours = int(parts[1])
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO settings VALUES ('promo_interval', ?)", (str(hours),))
    await msg.answer(f"✅ Promo har <b>{hours}</b> soatda avtomatik yuboriladi.", parse_mode="HTML")

@router.message(Command("give"))
@admin_only
async def cmd_give_manual(msg: Message, **_):
    """Admin joriy chatga M ta account beradi: /give 5"""
    parts = msg.text.split()
    count = 1
    if len(parts) > 1 and parts[1].isdigit():
        count = int(parts[1])
        
    if count > 50: # prevent spam
        count = 50
        
    given_accs = []
    for _ in range(count):
        acc = next_available_account()
        if not acc:
            break
        mark_given(acc["id"], msg.chat.id)
        given_accs.append(acc)
        
    if not given_accs:
        await msg.answer("😔 Bo'sh accountlar qolmadi.")
        return
        
    for acc in given_accs:
        try:
            await msg.answer(f"🎁 <b>GIVEAWAY ACCOUNT</b>! 👇\n\n{account_text(acc)}", parse_mode="HTML")
            await asyncio.sleep(0.3)
        except Exception:
            pass
            
    await msg.reply(f"✅ Shu chatga jami {len(given_accs)} ta akkaunt tashlandi!")

@router.message(Command("topreferrals"))
@admin_only
async def cmd_top_referrals(msg: Message, **_):
    """Eng ko'p do'st taklif qilgan top 10 foydalanuvchilarni ko'rsatadi."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT user_id, invites_count FROM users WHERE invites_count > 0 ORDER BY invites_count DESC LIMIT 10"
        ).fetchall()
    if not rows:
        await msg.answer("📊 Hali hech kim taklif qilmagan.")
        return
    text = "━━━━━━━━━━━━━━━━━━━━━\n🏆 <b>TOP 10 TAKLIF QILUVCHILAR</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, row in enumerate(rows):
        text += f"{medals[i]} <code>{row['user_id']}</code> — <b>{row['invites_count']}</b> ta taklif\n"
    text += "\n━━━━━━━━━━━━━━━━━━━━━"
    await msg.answer(text, parse_mode="HTML")

@router.message(Command("commands"))
async def cmd_commands(msg: Message, **_):
    await msg.answer(
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📜 <b>BOT BUYRUQLARI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎮 <b>Asosiy:</b>\n"
        "/start — Botni ishga tushirish\n"
        "/daily — Kunlik bonus ball olish\n"
        "/spin — Omad g'ildiragi (12 soatda 1x)\n"
        "/shop — Ballar do'koni\n"
        "/leaderboard — Top reyting\n\n"
        "🛒 <b>Savdo (Trade):</b>\n"
        "🛒 Akkaunt Sotish — Menu → Trade tugmasi\n"
        "   (AI tekshiruv + Admin tasdiqlash)\n\n"
        "🤖 <b>AI:</b>\n"
        "/ai savol — AI dan maslahat olish\n\n"
        "📊 <b>Ma'lumot:</b>\n"
        "👤 Profilim — Ballar va streak ko'rish\n"
        "📊 Statistika — Bot statistikasi\n"
        "💰 UC Narxlar — UC narxlar ro'yxati\n"
        "👥 Takliflarim — Referral ma'lumotlar\n\n"
        "<i>📋 Barchasi Menu tugmasidan ham ochiq!</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
    )

@router.message(Command("help"))
@admin_only
async def cmd_help(msg: Message, **_):
    await msg.answer(
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🛠 <b>ADMIN BUYRUQLARI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 <b>Statistika:</b>\n"
        "/stats — Admin statistika\n"
        "/topreferrals — Top taklif qiluvchilar\n\n"
        "📢 <b>Post yuborish:</b>\n"
        "/sendpromo — Promo post\n"
        "/senduc — UC narxlar posti\n"
        "/sendpayment — To'lov ma'lumoti\n"
        "/setpromo 6 — Auto promo interval (soat)\n\n"
        "🎁 <b>Giveaway:</b>\n"
        "/give 5 — Shu chatga 5 ta akk tashlash\n"
        "/addmilestone 1000 — Milestone qo'shish\n\n"
        "👥 <b>Foydalanuvchilar:</b>\n"
        "/broadcast matn — Barchaga xabar\n"
        "/ban ID — Bloklash\n"
        "/unban ID — Blokdan chiqarish\n\n"
        "🛒 <b>Trade tizimi:</b>\n"
        "Foydalanuvchilar Menu → Trade orqali\n"
        "akkaunt sotadi. AI vision tekshiradi.\n"
        "Sizga tasdiqlash uchun rasm/video keladi.\n\n"
        "ℹ️ /commands — Barcha buyruqlar\n"
        "━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
    )

@router.message(Command("broadcast"))
@admin_only
async def cmd_broadcast(msg: Message, bot: Bot, **_):
    """Barchaga xabar /broadcast matn"""
    text = msg.text.replace("/broadcast", "").strip()
    if not text:
        await msg.answer("❗ Matn yo'q.")
        return
        
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id FROM users").fetchall()
        
    sent, failed = 0, 0
    prompt = await msg.answer("⏳ Broadcast yuborilmoqda...")
    for row in rows:
        try:
            await bot.send_message(row["user_id"], f"📢 <b>ADMIN XABARI</b>\n\n{text}", parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    await prompt.edit_text(f"✅ Yuborildi: {sent}\n❌ Xato: {failed}")

@router.message(Command("ban"))
@admin_only
async def cmd_ban(msg: Message, **_):
    parts = msg.text.split()
    if len(parts) > 1 and parts[1].isdigit():
        uid = int(parts[1])
        set_banned(uid)
        await msg.answer(f"✅ User {uid} bloklandi.")

@router.message(Command("unban"))
@admin_only
async def cmd_unban(msg: Message, **_):
    parts = msg.text.split()
    if len(parts) > 1 and parts[1].isdigit():
        uid = int(parts[1])
        remove_banned(uid)
        await msg.answer(f"✅ User {uid} blokdan chiqarildi.")

# ──────────────────────────────────────────────
# PROMO POST
# ──────────────────────────────────────────────
async def send_promo(bot: Bot):
    _, available, given_cnt = stats()
    try:
        count = await bot.get_chat_member_count(CHANNEL_ID)
    except Exception:
        count = "?"

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎮 Bepul account olish",
            url=f"https://t.me/{(await bot.get_me()).username}?start=promo"
        )
    ]])

    await bot.send_message(
        CHANNEL_ID,
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔥 <b>PUBG BEPUL ACCOUNT GIVEAWAY!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Kanal obunachilari: <b>{count:,}</b>\n"
        f"🎁 Berilgan accountlar: <b>{given_cnt:,}</b>\n"
        f"✅ Hali mavjud: <b>{available:,}</b> ta\n\n"
        f"🎮 <b>Qanday olish mumkin?</b>\n\n"
        f"1️⃣ Kanalga obuna bo'l\n"
        f"2️⃣ Pastdagi tugmani bos\n"
        f"3️⃣ Accountni ol va o'yna!\n\n"
        f"⚡ Tez bo'l — accountlar cheklangan!\n"
        f"🔔 Yangi giveaway lar uchun kanalda qol!\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=kb,
        parse_mode="HTML",
    )

# ──────────────────────────────────────────────
# AI INTEGRATION (OpenRouter)
# ──────────────────────────────────────────────
AI_MODELS = [
    "openai/gpt-oss-20b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-v4-flash:free",
    "google/gemma-4-26b-a4b-it:free",
]

async def get_ai_response(prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    
    for model in AI_MODELS:
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Sen PUBG Mobile ekspertisan. Foydalanuvchilarga o'zbek tilida qisqa va aniq maslahat berasan. Boting nomi 'sdzABU AI'. Javoblarni 500 belgidan oshirma."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as resp:
                    if resp.status == 200:
                        res_json = await resp.json()
                        return res_json["choices"][0]["message"]["content"]
                    else:
                        logger.warning(f"AI model {model} failed: {resp.status}")
                        continue
        except Exception as e:
            logger.error(f"AI error ({model}): {e}")
            continue
            
    return "😔 Hozirda AI xizmati yuklanmoqda, keyinroq urinib ko'ring."

@router.message(Command("ai"))
async def cmd_ai(msg: Message, **_):
    """AI bilan gaplashish"""
    text = msg.text.replace("/ai", "").strip()
    if not text:
        await msg.answer("🤖 Menga savol yozing. Masalan:\n`/ai M416 uchun qaysi nishon (scope) yaxshi?`", parse_mode="Markdown")
        return
    wait_msg = await msg.answer("⏳ <i>O'ylayapman...</i>", parse_mode="HTML")
    answer = await get_ai_response(text)
    try:
        await wait_msg.edit_text(f"🤖 <b>sdzABU AI:</b>\n\n{answer}", parse_mode="HTML")
    except Exception:
        await wait_msg.edit_text(answer)

# ──────────────────────────────────────────────
# UC POST (har 24 soatda avtomatik)
# ──────────────────────────────────────────────
async def send_uc_post(bot: Bot):
    """Kanalga UC narxlarini rasm bilan yuboradi."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 UC SOTIB OLISH", url="https://t.me/WebDev999")],
        [InlineKeyboardButton(text="🔰 AKK SOTIB OLISH", url="https://t.me/sdzAbuPM_AkkSavdo")],
        [InlineKeyboardButton(text="📜 TO'LOV VA QOIDALAR", url="https://t.me/sdzAbuPM_UC")],
    ])

    uc_img = FSInputFile("uc-banner.png")
    await bot.send_photo(
        CHANNEL_ID,
        photo=uc_img,
        caption=UC_PRICES_TEXT,
        reply_markup=kb,
        parse_mode="HTML",
    )

async def uc_auto_scheduler(bot: Bot):
    """Har 24 soatda UC narxlarini kanalga avtomatik yuboradi."""
    while True:
        try:
            await send_uc_post(bot)
            logger.info("UC narxlar kanalga yuborildi (avtomatik 24h)")
        except Exception as e:
            logger.error(f"UC auto post xatosi: {e}")
        # 24 soat kutish
        await asyncio.sleep(24 * 3600)

async def auto_promo_scheduler(bot: Bot):
    """Sozlangan intervalda avtomatik promo yuboradi."""
    while True:
        try:
            with get_conn() as conn:
                row = conn.execute("SELECT value FROM settings WHERE key='promo_interval'").fetchone()
            if row:
                hours = int(row[0])
                await send_promo(bot)
                logger.info(f"Promo kanalga yuborildi (avtomatik {hours}h)")
                await asyncio.sleep(hours * 3600)
            else:
                await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"Auto promo xatosi: {e}")
            await asyncio.sleep(300)

# ──────────────────────────────────────────────
# MILESTONE CHECKER (background task)
# ──────────────────────────────────────────────
async def milestone_checker(bot: Bot):
    """Har 10 daqiqada kanalning obunachi sonini tekshiradi."""
    while True:
        try:
            count = await bot.get_chat_member_count(CHANNEL_ID)
            pending = get_pending_milestones(count)

            for ms in pending:
                acc = next_available_account()
                if acc is None:
                    break
                mark_given(acc["id"], 0)
                mark_milestone_done(ms["id"])
                await bot.send_message(
                    CHANNEL_ID,
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🎊 <b>{ms['target']:,} obunachi!</b> Tabriklaymiz!\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🎁 Giveaway account:\n{account_text(acc)}\n\n"
                    f"🔔 Ko'proq accountlar uchun kanalda qoling!\n"
                    f"━━━━━━━━━━━━━━━━━━━━━",
                    parse_mode="HTML",
                )
                logger.info(f"Milestone {ms['target']} triggered, account #{acc['id']} posted.")
        except Exception as e:
            logger.error(f"Milestone checker xatosi: {e}")

        await asyncio.sleep(600)

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
async def main():
    init_db()
    load_accounts_from_json("pubg-accounts.json")

    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher()
    dp.include_router(router)

    from keep_alive import start_webserver
    await start_webserver()

    asyncio.create_task(milestone_checker(bot))
    asyncio.create_task(auto_promo_scheduler(bot))
    asyncio.create_task(uc_auto_scheduler(bot))
    
    from harvester import harvest
    async def periodic_harvest():
        while True:
            try:
                harvest()
                load_accounts_from_json() # Baza yangilanganidan keyin qayta yuklash
            except Exception as e:
                logger.error(f"Harvester background error: {e}")
            await asyncio.sleep(12 * 3600) # Har 12 soatda bir marta
            
    asyncio.create_task(periodic_harvest())

    logger.info("Bot ishga tushdi ✅")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())