import os
import requests
from pyrogram import Client, filters
from pyrogram.types import Message

APP_ID = int(os.environ.get("APP_ID"))
APP_HASH = os.environ.get("APP_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GOFILE_UPLOAD_URL = "https://upload.gofile.io/uploadFile"

# Initialize Pyrogram bot session
app = Client("gofilebot", api_id=APP_ID, api_hash=APP_HASH, bot_token=BOT_TOKEN)

def upload_to_gofile(file_path):
    """
    Upload a file to Gofile and return the download link.
    All exceptions are handled internally.
    """
    try:
        with open(file_path, "rb") as f:
            files = {'file': f}
            response = requests.post(GOFILE_UPLOAD_URL, files=files, timeout=300)

        # Try parsing JSON, else log raw response
        try:
            data = response.json()
        except Exception as e:
            print(f"[ERROR] JSON decode error: {e}")
            print("Gofile response:", response.text)
            return None

        # API-level error handling
        if data.get("status") == "ok":
            return data["data"]["downloadPage"]
        else:
            print("[ERROR] Gofile API error:", data)
            return None

    except Exception as e:
        print(f"[ERROR] Exception in upload_to_gofile: {e}")
        return None

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply(
        "👋 Hello! Send me any file (photo, video, audio, document) up to 2GB, "
        "and I will upload it to Gofile.io for you and send a download link.\n\n"
        "Use /help for more info."
    )

@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    await message.reply(
        "📝 *How to use this bot:*\n"
        "• Send any file (document, video, audio, photo) upto 2GB.\n"
        "• I will reply with a Gofile download link.\n"
        "• For big files, send as document.\n"
        "\n"
        "If you get upload errors, try again later. Have fun!"
    )

@app.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def handle_file(client: Client, message: Message):
    # Send initial feedback message
    reply = await message.reply("⏳ Downloading your file...")
    file_path = None

    try:
        # Download the file locally
        file_path = await message.download()
        await reply.edit("📤 Uploading to Gofile...")

        # Upload to Gofile with robust error handling
        download_link = upload_to_gofile(file_path)

        # Remove temp file
        try:
            if file_path:
                os.remove(file_path)
        except Exception as e:
            print(f"[WARNING] Couldn't delete file {file_path}: {e}")

        # Reply with link or error
        if download_link:
            await reply.edit(f"✅ Uploaded!\nDownload link:\n{download_link}")
        else:
            await reply.edit("❌ Upload failed (Gofile server/API issue). Try again later.")

    except Exception as e:
        print(f"[ERROR] Exception in handle_file: {e}")
        await reply.edit("❌ An error occurred while processing your file. Try again.")

if __name__ == "__main__":
    print("Bot is starting...", flush=True)
    try:
        app.run()
    except Exception as e:
        import traceback
        print("[FATAL] Bot crashed:", e)
        traceback.print_exc()
