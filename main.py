import os
import sqlite3
import random
import string
import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========== CONFIGURATION ==========
API_ID = 20346419
API_HASH = "b5dfd37f315213ada6ab0e2c7acfefa1"
BOT_TOKEN = "7410841245:AAHQqGRA7ZrcYbarjMfIo_Ok-iS245dAAVI"
OWNER_ID = 6847499628
FORCE_JOIN = ["@YourChannel1", "@YourChannel2"]
WEBHOOK_URL = "https://your-choreo-app-url.choreoapps.dev"
PORT = int(os.environ.get("PORT", 8080))
# ===================================

app = Client("giveaway_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Database setup
conn = sqlite3.connect("giveaway.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    banned INTEGER DEFAULT 0,
    redeemed_count INTEGER DEFAULT 0
)""")
cur.execute("""CREATE TABLE IF NOT EXISTS codes (
    code TEXT PRIMARY KEY,
    creator_id INTEGER,
    limit_users INTEGER DEFAULT 1,
    expiry TEXT,
    used_count INTEGER DEFAULT 0
)""")
cur.execute("CREATE TABLE IF NOT EXISTS admins (admin_id INTEGER PRIMARY KEY)")
conn.commit()

# Utility
def is_admin(uid):
    if uid == OWNER_ID:
        return True
    cur.execute("SELECT * FROM admins WHERE admin_id=?", (uid,))
    return cur.fetchone() is not None

def is_banned(uid):
    cur.execute("SELECT banned FROM users WHERE user_id=?", (uid,))
    row = cur.fetchone()
    return row and row[0] == 1

def add_user(uid):
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
    conn.commit()

async def check_force_join(client, message):
    for channel in FORCE_JOIN:
        try:
            member = await client.get_chat_member(channel, message.from_user.id)
            if member.status in ["left", "kicked"]:
                await message.reply_text(
                    f"Please join {channel} first to use the bot.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join", url=f"https://t.me/{channel.replace('@','')}")]])
                )
                return False
        except:
            pass
    return True

# Commands
@app.on_message(filters.command("start"))
async def start(_, m):
    add_user(m.from_user.id)
    if is_banned(m.from_user.id):
        return await m.reply("🚫 You are banned from using this bot.")
    if not await check_force_join(app, m):
        return
    await m.reply("🎉 Welcome to Giveaway Bot!\nUse /redeem <code> to claim.\nAdmins: /createcode /ban /unban /broadcast /backup /stats")

@app.on_message(filters.command("createcode"))
async def create_code(_, m):
    if not is_admin(m.from_user.id):
        return await m.reply("❌ Admins only.")
    try:
        args = m.text.split()
        if len(args) < 3:
            return await m.reply("Usage: /createcode <limit> <days_valid>\nExample: /createcode 5 2")
        limit_users = int(args[1])
        days = int(args[2])
        expiry = (datetime.datetime.utcnow() + datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        cur.execute("INSERT INTO codes (code, creator_id, limit_users, expiry) VALUES (?,?,?,?)", (code, m.from_user.id, limit_users, expiry))
        conn.commit()
        await m.reply(f"✅ Code: `{code}`\nUsers allowed: {limit_users}\nExpires: {expiry} UTC")
    except Exception as e:
        await m.reply(f"Error: {e}")

@app.on_message(filters.command("redeem"))
async def redeem(_, m):
    if len(m.command) < 2:
        return await m.reply("Usage: /redeem <code>")
    uid = m.from_user.id
    add_user(uid)
    if is_banned(uid):
        return await m.reply("🚫 You are banned.")
    if not await check_force_join(app, m):
        return
    code = m.command[1].strip().upper()
    cur.execute("SELECT * FROM codes WHERE code=?", (code,))
    code_data = cur.fetchone()
    if not code_data:
        return await m.reply("❌ Invalid code.")
    _, creator_id, limit_users, expiry, used_count = code_data
    if datetime.datetime.utcnow() > datetime.datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S"):
        return await m.reply("⏰ Code expired.")
    if used_count >= limit_users:
        return await m.reply("❌ Code fully used.")
    cur.execute("UPDATE codes SET used_count=used_count+1 WHERE code=?", (code,))
    cur.execute("UPDATE users SET redeemed_count=redeemed_count+1 WHERE user_id=?", (uid,))
    conn.commit()
    await m.reply("🎁 Redeemed successfully! You got your reward.")
    await app.send_message(OWNER_ID, f"✅ {m.from_user.mention} redeemed code `{code}`.")

@app.on_message(filters.command("ban"))
async def ban(_, m):
    if not is_admin(m.from_user.id):
        return
    if len(m.command) < 2:
        return await m.reply("Usage: /ban <user_id>")
    uid = int(m.command[1])
    cur.execute("UPDATE users SET banned=1 WHERE user_id=?", (uid,))
    conn.commit()
    await m.reply(f"🚫 User {uid} banned.")

@app.on_message(filters.command("unban"))
async def unban(_, m):
    if not is_admin(m.from_user.id):
        return
    if len(m.command) < 2:
        return await m.reply("Usage: /unban <user_id>")
    uid = int(m.command[1])
    cur.execute("UPDATE users SET banned=0 WHERE user_id=?", (uid,))
    conn.commit()
    await m.reply(f"✅ User {uid} unbanned.")

@app.on_message(filters.command("addadmin"))
async def add_admin(_, m):
    if m.from_user.id != OWNER_ID:
        return
    if len(m.command) < 2:
        return await m.reply("Usage: /addadmin <user_id>")
    uid = int(m.command[1])
    cur.execute("INSERT OR IGNORE INTO admins (admin_id) VALUES (?)", (uid,))
    conn.commit()
    await m.reply(f"✅ {uid} added as admin.")

@app.on_message(filters.command("broadcast"))
async def broadcast(_, m):
    if not is_admin(m.from_user.id):
        return
    msg = m.text.split(" ", 1)[1] if len(m.text.split(" ", 1)) > 1 else None
    if not msg:
        return await m.reply("Usage: /broadcast <message>")
    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()
    sent = 0
    for u in users:
        try:
            await app.send_message(u[0], msg)
            sent += 1
        except:
            pass
    await m.reply(f"📢 Broadcast sent to {sent} users.")

@app.on_message(filters.command("stats"))
async def stats(_, m):
    if not is_admin(m.from_user.id):
        return
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM codes")
    total_codes = cur.fetchone()[0]
    await m.reply(f"📊 Stats:\nUsers: {total_users}\nCodes: {total_codes}")

@app.on_message(filters.command("backup"))
async def backup(_, m):
    if m.from_user.id != OWNER_ID:
        return
    await app.send_document(OWNER_ID, "giveaway.db", caption="📦 Database Backup")

@app.on_message(filters.photo & filters.caption)
async def login_screenshot(_, m):
    if "login" in m.caption.lower():
        await m.reply("✅ Login screenshot received.")

# Run bot using webhook for Choreo
if __name__ == "__main__":
    print("✅ Giveaway Bot Running via Webhook...")
    app.run(webhook=WEBHOOK_URL, port=PORT)
