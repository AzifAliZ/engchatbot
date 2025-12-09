import os
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import google.generativeai as genai

# Load environment variables
load_dotenv()

# --- Telegram Credentials (NEWLY REQUIRED) ---
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Gemini Credentials ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# --- Validation Checks ---
if not API_ID or not API_HASH:
    # We must provide the Telegram API credentials (ID and HASH)
    raise SystemExit("Missing Telegram API_ID or API_HASH in .env. Please check the Pyrogram documentation for setup.")
if not BOT_TOKEN:
    raise SystemExit("Missing BOT_TOKEN in .env")
if not GEMINI_KEY:
    raise SystemExit("Missing GEMINI_API_KEY in .env")

# Configure Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Store each user's selected scenario
user_scenarios = {}


def scenario_prompt(s):
    prompts = {
        "dating": "Act like a romantic partner. Speak softly and simply.",
        "job": "Act like a job interviewer. Ask simple interview questions.",
        "travel": "Act like a friendly travel guide.",
        "casual": "Act like a friendly English practice partner."
    }
    # Ensure a basic system instruction is always present
    return prompts.get(s, prompts["casual"])


# Create Pyrogram Bot client (NOW includes API_ID and API_HASH)
app = Client(
    "engchatbot",
    api_id=int(API_ID),  # Must be an integer
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True  # avoids creating a session file
)


# -------- COMMAND HANDLERS --------

@app.on_message(filters.command("start"))
async def start(_, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Choose Scenario", callback_data="scenarios")],
        [InlineKeyboardButton("⚙ Settings", callback_data="settings")]
    ])

    # Also display the currently active scenario
    uid = message.from_user.id
    current_scenario = user_scenarios.get(uid, "casual").capitalize()
    
    await message.reply(
        f"👋 Welcome to English Practice Bot!\n\nCurrent Scenario: **{current_scenario}**\n\nSelect a scenario to begin:",
        reply_markup=keyboard
    )


# -------- BUTTON HANDLERS --------

@app.on_callback_query()
async def callback_handler(_, query):
    data = query.data or ""
    uid = query.from_user.id
    current_scenario = user_scenarios.get(uid, "casual").capitalize()

    # Show scenario menu
    if data == "scenarios":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❤️ Dating", callback_data="set_dating")],
            [InlineKeyboardButton("💼 Job Interview", callback_data="set_job")],
            [InlineKeyboardButton("✈ Travel", callback_data="set_travel")],
            [InlineKeyboardButton("💬 Casual Chat", callback_data="set_casual")],
        ])
        await query.message.edit_text(
            f"Current Scenario: **{current_scenario}**\n\nChoose a new scenario:",
            reply_markup=keyboard
        )
        await query.answer() # Acknowledge the query immediately
        return

    # Set selected scenario
    if data.startswith("set_"):
        scenario = data.replace("set_", "")
        user_scenarios[uid] = scenario
        
        # Use a more subtle notification instead of editing the message text
        await query.answer(f"Scenario selected: {scenario.capitalize()}. Start chatting now!", show_alert=False)
        await query.message.edit_text(
            f"✅ Scenario selected: **{scenario.capitalize()}**.\n\nYou can start chatting immediately!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✨ Choose Scenario", callback_data="scenarios")]
            ])
        )
        return

    # Settings menu
    if data == "settings":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 Change Scenarios", callback_data="scenarios")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ])
        await query.message.edit_text(f"⚙ Settings Menu\n\nCurrent Scenario: **{current_scenario}**", reply_markup=keyboard)
        await query.answer()
        return

    if data == "help":
        await query.message.edit_text("Use /start to reset the conversation and select a new scenario. The bot uses the Gemini AI model to help you practice English in various contexts.")
        await query.answer()
        return


# -------- MAIN CHAT HANDLER --------
@app.on_message(filters.text & ~filters.command(["start"]))
async def chat(_, message):
    uid = message.from_user.id
    scenario_key = user_scenarios.get(uid, "casual")
    
    # 1. Get the system instruction for the current scenario
    system_instruction = scenario_prompt(scenario_key)

    # 2. Construct the full prompt for Gemini
    prompt = f"""
SYSTEM INSTRUCTION: You are an English practice partner.
Your persona must be based on the following scenario: {scenario_key} ({system_instruction}).
Your response should be friendly and helpful.
MOST IMPORTANTLY: Keep your vocabulary simple and your sentence structures easy to understand, as the user is practicing English.

USER INPUT: {message.text}
YOUR RESPONSE:
"""

    try:
        # Use a more structured call if possible, or stick to the simple prompt
        # Using the prompt structure above implicitly guides the model
        
        # Add typing indicator while waiting for AI
        await app.send_chat_action(message.chat.id, "typing")
        
        # Gemini call
        response = model.generate_content(prompt)
        text = response.text
        
        if not text:
            text = "I received your message, but the AI did not generate a text response. Please try a different message."

        await message.reply(text)
        
    except Exception as e:
        await message.reply("❌ Sorry — I couldn't generate a response. There was an AI processing error.")
        print(f"Gemini error for user {uid}: {repr(e)}")


# -------- RUN BOT --------

if __name__ == "__main__":
    print("🤖 Bot is starting up...")
    try:
        app.run()
    except KeyboardInterrupt:
        print("Stopping bot...")