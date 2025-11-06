from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import random
import string

API_ID = 20346419  # your API_ID
API_HASH = "b5dfd37f315213ada6ab0e2c7acfefa1"
BOT_TOKEN = "7410841245:AAHQqGRA7ZrcYbarjMfIo_Ok-iS245dAAVI"
OWNER_ID = 6847499628  # your Telegram ID

FORCE_JOIN = ["EscrowMoon", "@EscrowMoon"]  # Channels for force join

app = Client("giveaway_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- Database setup ---
conn = sqlite3.connect("giveaway.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, banned INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS codes (code TEXT, used_by INTEGER, creator_id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS admins (admin_id INTEGER)")
conn.commit()


# --- Utility functions ---
def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    cur.execute("SELECT * FROM admins WHERE admin_id=?", (user_id,))
    return cur.fetchone() is not None


def is_banned(user_id):
    cur.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
    data = cur.fetchone()
    return data and data[0] == 1


def add_user(user_id):
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()


# --- Force Join Check ---
async def check_force_join(client, message):
    for channel in FORCE_JOIN:
        try:
            member = await client.get_chat_member(channel, message.from_user.id)
            if member.status in ["left", "kicked"]:
                await message.reply_text(
                    f"Please join {channel} first to use the bot.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel", url=f"https://t.me/{channel.replace('@','')}")]])
                )
                return False
        except Exception:
            pass
    return True


# --- Start Command ---
@app.on_message(filters.command("start"))
async def start(client, message):
    user = message.from_user
    add_user(user.id)

    if is_banned(user.id):
        await message.reply("🚫 You are banned from using this bot.")
        return

    if not await check_force_join(client, message):
        return

    await message.reply_text("🎉 Welcome to the Giveaway Bot!\nUse /redeem <code> to claim rewards.\nAdmins can use /createcode to generate redeem codes.")


# --- Create Redeem Code ---
@app.on_message(filters.command("createcode"))
async def create_code(client, message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.reply("❌ Only admins can create redeem codes.")
        return

    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    cur.execute("INSERT INTO codes (code, creator_id) VALUES (?, ?)", (code, user_id))
    conn.commit()
    await message.reply(f"✅ Redeem Code Created: `{code}`", quote=True)


# --- Redeem Code ---
@app.on_message(filters.command("redeem"))
async def redeem(client, message):
    user_id = message.from_user.id
    add_user(user_id)

    if is_banned(user_id):
        await message.reply("🚫 You are banned from using this bot.")
        return

    if not await check_force_join(client, message):
        return

    if len(message.command) < 2:
        await message.reply("⚠️ Usage: /redeem <code>")
        return

    code = message.command[1]
    cur.execute("SELECT * FROM codes WHERE code=? AND used_by IS NULL", (code,))
    result = cur.fetchone()
    if result:
        cur.execute("UPDATE codes SET used_by=? WHERE code=?", (user_id, code))
        conn.commit()
        await message.reply("🎁 Redeem Successful! You got the reward.")
    else:
        await message.reply("❌ Invalid or already used code.")


# --- Upload Screenshot (Login Proof) ---
@app.on_message(filters.photo & filters.caption)
async def login_screenshot(client, message):
    if "login" in message.caption.lower():
        await message.reply("✅ Login screenshot received and verified.")


# --- Admin Controls ---
@app.on_message(filters.command("ban"))
async def ban_user(client, message):
    if not is_admin(message.from_user.id):
        return await message.reply("❌ Only admins can ban users.")
    if len(message.command) < 2:
        return await message.reply("⚠️ Usage: /ban <user_id>")

    uid = int(message.command[1])
    cur.execute("UPDATE users SET banned=1 WHERE user_id=?", (uid,))
    conn.commit()
    await message.reply(f"🚫 User {uid} has been banned.")


@app.on_message(filters.command("unban"))
async def unban_user(client, message):
    if not is_admin(message.from_user.id):
        return await message.reply("❌ Only admins can unban users.")
    if len(message.command) < 2:
        return await message.reply("⚠️ Usage: /unban <user_id>")

    uid = int(message.command[1])
    cur.execute("UPDATE users SET banned=0 WHERE user_id=?", (uid,))
    conn.commit()
    await message.reply(f"✅ User {uid} has been unbanned.")


@app.on_message(filters.command("addadmin"))
async def add_admin(client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ Only owner can add admins.")
    if len(message.command) < 2:
        return await message.reply("⚠️ Usage: /addadmin <user_id>")

    uid = int(message.command[1])
    cur.execute("INSERT OR IGNORE INTO admins (admin_id) VALUES (?)", (uid,))
    conn.commit()
    await message.reply(f"✅ Added {uid} as admin.")


# --- Run Bot ---
print("✅ Giveaway Bot Running...")
app.run()
