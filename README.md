# 🎮 PUBG Giveaway Bot

Telegram kanalingiz uchun avtomatik PUBG account giveaway boti.

## Qanday ishlaydi?

1. Foydalanuvchi `/start` bosadi
2. Bot kanalga obuna bo'lishni so'raydi
3. Foydalanuvchi «✅ Tekshirish» bosadi
4. Bot obunani tekshirib, ketma-ket account yuboradi
5. Har bir odam faqat **bir marta** account olishi mumkin

**Milestone rejimi:** Kanal 1000, 5000, 10000 obunachiga yetganda, bot avtomatik kanalda account e'lon qiladi.

---

## O'rnatish

### 1. Bot yaratish
[@BotFather](https://t.me/BotFather) → `/newbot` → token oling

### 2. Kanalga bot qo'shish
- Botni kanal adminlariga qo'shing
- Privacy mode: **o'chiring** (BotFather → `/mybots` → Bot Settings → Group Privacy → Disable)

### 3. Render.com ga deploy

1. GitHub repoga push qiling (pubg-accounts.json ham bilan)
2. Render.com → New Web Service → GitHub repo ni tanlang
3. Environment variables qo'shing:

| Variable    | Qiymati                        |
|-------------|-------------------------------|
| BOT_TOKEN   | BotFatherdan olgan token      |
| CHANNEL_ID  | @kanal_username (@ bilan)     |
| ADMIN_ID    | Sizning Telegram user ID ingiz |

4. Deploy!

### 4. UptimeRobot (bot o'chmasligi uchun)
- [uptimerobot.com](https://uptimerobot.com) ga kiring
- New Monitor → HTTP(s)
- URL: `https://sizning-render-url.onrender.com`
- Interval: 5 daqiqa

---

## Admin buyruqlar

| Buyruq | Tavsif |
|--------|--------|
| `/stats` | Statistika: jami / mavjud / berilgan |
| `/addmilestone 1000` | 1000 obunachiga yetganda auto post |
| `/giveaccount 123456789` | Qo'lda user ga account berish |

---

## Eslatma
`pubg-accounts.json` faylini repoga qo'shing.
Bot faqat PUBG account yozuvlarini (email bo'lmagan) yuklaydi.
