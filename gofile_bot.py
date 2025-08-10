import os
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor

APP_ID = int(os.environ.get("APP_ID"))
APP_HASH = os.environ.get("APP_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GOFILE_UPLOAD_URL = "https://upload.gofile.io/uploadFile"

# Initialize Pyrogram client
app = Client("gofilebot", api_id=APP_ID, api_hash=APP_HASH, bot_token=BOT_TOKEN)

def create_progress_callback(message, client):
    """Returns a callback for MultipartEncoderMonitor that sends progress to Telegram."""
    def callback(monitor):
        try:
            percent = (monitor.bytes_read / monitor.len) * 100
            # Only update every ~1%
            if not hasattr(callback, "last_percent") or percent - callback.last_percent >= 1:
                callback.last_percent = percent
                client.loop.create_task(
                    message.edit(f"📤 Uploading to Gofile... {percent:.2f}%")
                )
        except Exception as e:
            print(f"[WARNING] Progress update error: {e}")
    callback.last_percent = 0
    return callback

def upload_to_gofile_with_progress(file_path, message, client):
    """Uploads file using MultipartEncoderMonitor to show real-time progress."""
    try:
        file_size = os.path.getsize(file_path)
        m_encoder = MultipartEncoder(
            fields={'file': (os.path.basename(file_path), open(file_path, 'rb'))}
        )
        monitor = MultipartEncoderMonitor(
            m_encoder,
            create_progress_callback(message, client)
        )
        headers = {"Content-Type": monitor.content_type}
        response = requests.post(GOFILE_UPLOAD_URL, data=monitor, headers=headers, timeout=600)
    except Exception as e:
        print(f"[ERROR] Exception during upload: {e}")
        return None

    try:
        data = response.json()
    except Exception as e:
        print(f"[ERROR] JSON decode failed: {e}")
        print("Response text:", response.text)
        return None

    if data.get("status") == "ok":
        return data["data"]["downloadPage"]
    else:
        print("[ERROR] Gofile API returned error:", data)
        return None

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply(
        "👋 Hello! Send me any file (photo, video, audio, document) up to 2GB, "
        "and I will upload it to Gofile.io for you with progress updates!\n\n"
        "Use /help for instructions."
    )

@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    await message.reply(
        "📝 How to use:\n"
        "- Send me any file as document, photo, audio, or video up to 2GB.\n"
        "- I'll download it, upload it to Gofile.io, and show upload progress right in this chat.\n"
        "- After upload, I'll send you the download link.\n\n"
        "⚠️ Large files should be sent as documents for reliability. If upload fails, try again later."
    )

@app.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def handle_file(client: Client, message: Message):
    reply = await message.reply("⏳ Downloading your file...")
    file_path = None
    try:
        file_path = await message.download()
        await reply.edit("📤 Starting upload to Gofile... 0.00%")

        download_link = upload_to_gofile_with_progress(file_path, reply, client)

        # Clean up file
        try:
            if file_path:
                os.remove(file_path)
        except Exception as e:
            print(f"[WARNING] Could not remove file: {file_path}, {e}")

        if download_link:
            await reply.edit(f"✅ Uploaded successfully!\nDownload link:\n{download_link}")
        else:
            await reply.edit("❌ Upload failed (possible Gofile API error). Please try again later.")

    except Exception as e:
        print(f"[ERROR] Exception in file handler: {e}")
        await reply.edit("❌ There was an error processing your file. Please try again.")

if __name__ == "__main__":
    print("Bot is starting...", flush=True)
    try:
        app.run()
    except Exception as e:
        import traceback
        print("[FATAL] Bot crashed:", e)
        traceback.print_exc()
