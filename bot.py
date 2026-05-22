import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN  = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")   # masalan: @mening_kanalim
ADMIN_ID   = int(os.getenv("ADMIN_ID", "0"))

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
        """)

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
    total, available, _ = stats()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}"),
        ],
        [
            InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub"),
        ],
        [
            InlineKeyboardButton(text="🪙 UC Narxlari", callback_data="uc_prices"),
            InlineKeyboardButton(text="📊 Statistika", callback_data="public_stats"),
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
        f"📦 Jami accountlar: <b>{total:,}</b>\n"
        f"✅ Hali mavjud: <b>{available:,}</b>\n\n"
        f"📢 Kanal: {CHANNEL_ID}\n"
        f"📺 YouTube: youtube.com/@sdzABU\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=kb,
        parse_mode="HTML",
    )

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

    await call.message.answer(
        f"🎉 <b>Tabriklaymiz!</b> Sizga account berildi:\n\n{account_text(acc)}",
        parse_mode="HTML",
    )
    await call.answer("✅ Account yuborildi! DM ni tekshiring.", show_alert=True)

@router.callback_query(F.data == "uc_prices")
async def cb_uc_prices(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 UC SOTIB OLISH", url="https://t.me/WebDev999")],
        [InlineKeyboardButton(text="🔰 AKK SOTIB OLISH", callback_data="check_sub")],
        [InlineKeyboardButton(text="📜 TO'LOV VA QOIDALAR", callback_data="public_stats")],
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

@router.message(Command("giveaccount"))
@admin_only
async def cmd_give_manual(msg: Message, **_):
    """Admin qo'lda account beradi: /giveaccount <user_id>"""
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("❗ Ishlatish: /giveaccount <user_id>")
        return
    uid = int(parts[1])
    acc = next_available_account()
    if acc is None:
        await msg.answer("😔 Accountlar tugadi.")
        return
    mark_given(acc["id"], uid)
    await msg.answer(
        f"✅ Account berildi (user {uid}):\n\n{account_text(acc)}", parse_mode="HTML"
    )

@router.message(Command("help"))
@admin_only
async def cmd_help(msg: Message, **_):
    await msg.answer(
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🛠 <b>Admin Buyruqlar</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "/stats — Statistikani ko'rish\n"
        "/sendpromo — Promo post yuborish\n"
        "/senduc — UC narxlarni yuborish\n"
        "/setpromo 6 — Auto promo interval\n"
        "/addmilestone 1000 — Milestone\n"
        "/giveaccount 12345 — Qo'lda berish\n"
        "/help — Shu yordam\n"
        "━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
    )

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
# UC POST (har 24 soatda avtomatik)
# ──────────────────────────────────────────────
async def send_uc_post(bot: Bot):
    """Kanalga UC narxlarini rasm bilan yuboradi."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 UC SOTIB OLISH", url="https://t.me/WebDev999")],
        [InlineKeyboardButton(text="🔰 AKK SOTIB OLISH", url=f"https://t.me/{(await bot.get_me()).username}?start=giveaway")],
        [InlineKeyboardButton(text="📜 TO'LOV VA QOIDALAR", url=f"https://t.me/{(await bot.get_me()).username}?start=stats")],
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

    logger.info("Bot ishga tushdi ✅")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())