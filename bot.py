import os
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ChatAction
from google import genai
from google.genai import types

# ---------------- ENV ----------------
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not all([API_ID, API_HASH, BOT_TOKEN, GEMINI_KEY]):
    raise SystemExit("❌ Missing required environment variables")

# ---------------- GEMINI ----------------
# genai.configure moved to client init

# We will create model dynamically per message
MODEL_NAME = "gemini-1.5-flash"

# ---------------- STATE ----------------
user_scenarios = {}

def scenario_prompt(scenario: str) -> str:
    roles = {
        "dating": "Act like a romantic partner. Speak softly and simply.",
        "job": "Act like a job interviewer. Ask simple interview questions.",
        "travel": "Act like a friendly travel guide.",
        "casual": "Act like a friendly English practice partner."
    }

    return (
        "You are an English practice assistant.\n"
        f"Scenario role: {roles.get(scenario, roles['casual'])}\n"
        "Rules:\n"
        "- Use simple English\n"
        "- Short sentences\n"
        "- Friendly tone\n"
        "- Help the user improve grammar and vocabulary"
    )

# ---------------- TELEGRAM ----------------
app = Client(
    "engchatbot",
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
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
            [InlineKeyboardButton("💼 Job", callback_data="set_job")],
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

    system_instruction = scenario_prompt(scenario)

    try:
        await app.send_chat_action(message.chat.id, ChatAction.TYPING)

        client = genai.Client(api_key=GEMINI_KEY)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=message.text,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )

        text = response.text or "Can you say that in another way?"

        await message.reply(text)

    except Exception as e:
        await message.reply("❌ AI error. Please try again.")
        print(f"Gemini error for user {uid}: {e}")

# ---------------- RUN ----------------
if __name__ == "__main__":
    print("🤖 Bot is starting up...")
    app.run()
