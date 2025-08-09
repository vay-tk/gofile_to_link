import os
import requests
from pyrogram import Client, filters
from pyrogram.types import Message

# Load Telegram API credentials from environment variables
APP_ID = int(os.environ.get("APP_ID"))
APP_HASH = os.environ.get("APP_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Gofile upload URL (auto region detects)
GOFILE_UPLOAD_URL = "https://upload.gofile.io/uploadFile"

# Initialize Pyrogram client (bot)
app = Client("gofilebot", api_id=APP_ID, api_hash=APP_HASH, bot_token=BOT_TOKEN)

def upload_to_gofile(file_path):
    """
    Uploads a file to Gofile using their API and returns the download page URL.
    Implements error handling and logs important responses.
    """
    try:
        with open(file_path, "rb") as f:
            files = {'file': f}
            response = requests.post(GOFILE_UPLOAD_URL, files=files, timeout=300)
        
        if response.status_code != 200:
            print(f"[ERROR] Gofile upload failed with status code: {response.status_code}")
            print("Response text:", response.text)
            return None

        data = response.json()

        if data.get('status') == 'ok':
            return data['data']['downloadPage']
        else:
            print("[ERROR] Gofile API error:", data)
            return None
    
    except requests.exceptions.RequestException as e:
        print("[ERROR] Network or request exception:", e)
        return None
    except ValueError as e:
        # JSON decode error or similar
        print("[ERROR] JSON decode failed:", e)
        print("Response text:", response.text if 'response' in locals() else "No response")
        return None

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply(
        "👋 Hello! Send me any file (photo, video, audio, document) up to 2GB, "
        "and I will upload it to Gofile.io for you and send back a download link.\n\n"
        "Use /help to see more info."
    )

@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    await message.reply(
        "📚 *How to use*:\n"
        "- Send me a file as a document, photo, video, or audio.\n"
        "- I will upload the file to Gofile and reply with a downloadable link.\n\n"
        "⚠️ Note:\n"
        "- Max file size is 2GB (Telegram limit).\n"
        "- For large files, send as document for best results.\n"
        "- If upload fails, try again later.\n\n"
        "Made with ❤️"
    )

@app.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def handle_file(client: Client, message: Message):
    # Inform user upload has started
    msg = await message.reply("⏳ Downloading your file...")
    
    try:
        # Download file locally
        file_path = await message.download()

        # Inform user upload has started
        await msg.edit("📤 Uploading file to Gofile...")

        # Upload file to Gofile
        download_link = upload_to_gofile(file_path)

        # Remove local file to save space
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"[WARNING] Could not delete file {file_path}: {e}")

        # Send result
        if download_link:
            await msg.edit(f"✅ File uploaded successfully!\nDownload link:\n{download_link}")
        else:
            await msg.edit("❌ Failed to upload the file to Gofile. Please try again later.")

    except Exception as e:
        # Catch any unexpected errors
        print(f"[ERROR] Exception in handle_file: {e}")
        await msg.edit("❌ An unexpected error occurred. Please try again.")

if __name__ == "__main__":
    print("Bot is starting...")
    app.run()
