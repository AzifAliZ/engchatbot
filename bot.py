import os
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ChatAction
import google.generativeai as genai

# NOTE: The problematic import 'import google.generativeai.types as genai_types' has been removed
# to prevent the AttributeError.

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

# FIX 1 (Addressing NotFound error): Initialize model without client_options
# We will NOT use this 'model' global variable directly for chat, 
# but rather re-initialize a temporary model in 'chat' to correctly set the system instruction.
try:
    # Use a current, recommended model name
    initial_model = genai.GenerativeModel("gemini-2.5-flash") 
except Exception as e:
    # Fallback in case gemini-2.5-flash is not available
    print(f"Failed to load gemini-2.5-flash for initial check, trying gemini-1.5-flash: {e}")
    initial_model = genai.GenerativeModel("gemini-1.5-flash")


# User state
user_scenarios = {}

def scenario_prompt(s):
    # Base role instruction
    base_role = {
        "dating": "Act like a romantic partner. Speak softly and simply.",
        "job": "Act like a job interviewer. Ask simple interview questions.",
        "travel": "Act like a friendly travel guide.",
        "casual": "Act like a friendly English practice partner."
    }.get(s, "Act like a friendly English practice partner.")

    # Rules included in the system instruction
    rules = (
        "Rules: - Use simple English - Short sentences - Friendly tone - Help the user improve English"
    )
    
    # Return the complete system instruction string
    return f"You are an English practice partner. Role: {base_role} {rules}"


# Pyrogram client
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
    scenario_key = user_scenarios.get(uid, "casual")
    
    # Generate the full system instruction string
    full_system_instruction = scenario_prompt(scenario_key)

    try:
        await app.send_chat_action(message.chat.id, ChatAction.TYPING)

        # FIX 2 (Addressing AttributeError): Re-create the model instance 
        # inside the function using the 'system_instruction' argument, 
        # which is the most robust way to pass the prompt configuration.
        temp_model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", 
            system_instruction=full_system_instruction
        )
        
        # Call generate_content with the system instruction and user's message
        response = temp_model.generate_content(
            contents=[
                {"role": "system", "parts": [full_system_instruction]},
                {"role": "user", "parts": [message.text]}
            ]
        )
        
        # Use .text, which is the preferred way to get the response
        text = response.text 

        if not text:
            text = "Can you say that in another way?"

        await message.reply(text)

    except Exception as e:
        await message.reply("❌ Sorry, something went wrong. Please try again.")
        print(f"Gemini error for user {uid}: {repr(e)}")

# ---------------- RUN ----------------
if __name__ == "__main__":
    print("🤖 Bot is starting up...")
    app.run()