import os
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ChatAction
import google.generativeai as genai

# Load environment variables
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Validation
if not API_ID or not API_HASH:
    raise SystemExit("❌ Missing API_ID or API_HASH")
if not BOT_TOKEN:
    raise SystemExit("❌ Missing BOT_TOKEN")
if not GEMINI_KEY:
    raise SystemExit("❌ Missing GEMINI_API_KEY")

# Gemini setup
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# User state
user_scenarios = {}

def scenario_prompt(s):
    return {
        "dating": "Act like a romantic partner. Speak softly and simply.",
        "job": "Act like a job interviewer. Ask simple interview questions.",
        "travel": "Act like a friendly travel guide.",
        "casual": "Act like a friendly English practice partner."
    }.get(s, "Act like a friendly English practice partner.")

# Pyrogram client
app = Client(
    "engchatbot",
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

# ---------------- START ----------------
@app.on_message(filters.command("start"))
async def start(_, message):
    uid = message.from_user.id
    current = user_scenarios.get(uid, "casual").capitalize()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Choose Scenario", callback_data="scenarios")],
        [InlineKeyboardButton("⚙ Settings", callback_data="settings")]
    ])

    await message.reply(
        f"👋 Welcome to English Practice Bot!\n\n"
        f"**Current Scenario:** {current}\n\n"
        "Choose a scenario to begin:",
        reply_markup=keyboard
    )

# ---------------- BUTTONS ----------------
@app.on_callback_query()
async def callbacks(_, query):
    data = query.data
    uid = query.from_user.id
    current = user_scenarios.get(uid, "casual").capitalize()

    if data == "scenarios":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❤️ Dating", callback_data="set_dating")],
            [InlineKeyboardButton("💼 Job Interview", callback_data="set_job")],
            [InlineKeyboardButton("✈ Travel", callback_data="set_travel")],
            [InlineKeyboardButton("💬 Casual", callback_data="set_casual")]
        ])
        await query.message.edit_text(
            f"**Current:** {current}\n\nChoose a scenario:",
            reply_markup=keyboard
        )
        await query.answer()
        return

    if data.startswith("set_"):
        scenario = data.replace("set_", "")
        user_scenarios[uid] = scenario
        await query.message.edit_text(
            f"✅ Scenario set to **{scenario.capitalize()}**.\n\nStart chatting!"
        )
        await query.answer()
        return

    if data == "settings":
        await query.message.edit_text(
            f"⚙ Settings\n\nCurrent Scenario: **{current}**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 Change Scenario", callback_data="scenarios")],
                [InlineKeyboardButton("❓ Help", callback_data="help")]
            ])
        )
        await query.answer()
        return

    if data == "help":
        await query.message.edit_text(
            "Send any message and I’ll reply in simple English.\n"
            "Use scenarios to practice different situations."
        )
        await query.answer()

# ---------------- CHAT ----------------
@app.on_message(filters.text & ~filters.command(["start"]))
async def chat(_, message):
    uid = message.from_user.id
    scenario = user_scenarios.get(uid, "casual")
    instruction = scenario_prompt(scenario)

    prompt = f"""
You are an English practice partner.

Scenario: {scenario}
Role: {instruction}

Rules:
- Simple vocabulary
- Short sentences
- Friendly tone

User says:
{message.text}

Reply:
"""

    try:
        # ✅ Correct typing indicator
        await message.reply_chat_action(ChatAction.TYPING)

        response = model.generate_content(prompt)
        text = getattr(response, "text", None)

        if not text:
            text = "🙂 I didn’t understand. Can you try again?"

        await message.reply(text)

    except Exception as e:
        print(f"[Gemini ERROR] user={uid} → {e}")
        await message.reply("❌ Sorry, something went wrong. Try again.")

# ---------------- RUN ----------------
if __name__ == "__main__":
    print("🤖 Bot is starting up...")
    app.run()
