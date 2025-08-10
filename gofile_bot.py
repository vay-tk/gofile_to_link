import os
import re
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor

# Telegram API credentials from environment variables
APP_ID = int(os.environ.get("APP_ID"))
APP_HASH = os.environ.get("APP_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# SendBig free upload endpoint
SENDBIG_UPLOAD_URL = "https://www.sendbig.com/api-files/upload"

# Initialize bot
app = Client("sendbigbot", api_id=APP_ID, api_hash=APP_HASH, bot_token=BOT_TOKEN)


# Progress callback factory
def make_progress_callback(message: Message, client: Client):
    def progress(monitor: MultipartEncoderMonitor):
        try:
            percent = (monitor.bytes_read / monitor.len) * 100
            if not hasattr(progress, "last_percent") or percent - progress.last_percent >= 1:
                progress.last_percent = percent
                client.loop.create_task(
                    message.edit(f"📤 Uploading to SendBig... {percent:.2f}%")
                )
        except Exception as e:
            print(f"[WARNING] Progress update failed: {e}")
    progress.last_percent = 0
    return progress


# Upload to SendBig
def upload_to_sendbig(file_path, message, client):
    try:
        m_encoder = MultipartEncoder(
            fields={'file': (os.path.basename(file_path), open(file_path, 'rb'))}
        )
        monitor = MultipartEncoderMonitor(m_encoder, make_progress_callback(message, client))

        headers = {"Content-Type": monitor.content_type}
        print("[INFO] Starting upload to SendBig...")
        response = requests.post(SENDBIG_UPLOAD_URL, data=monitor, headers=headers, timeout=1200)

        print("[INFO] Upload POST finished. Status:", response.status_code)

        # Try JSON first
        try:
            data = response.json()
            if "download_page" in data:
                return data["download_page"]
        except Exception:
            pass

        # Fallback: extract download link from HTML/text
        match = re.search(r"https://www\.sendbig\.com/view-file/[A-Za-z0-9]+", response.text)
        if match:
            return match.group(0)

        print("[ERROR] Could not parse SendBig response:", response.text[:500])
        return None

    except Exception as e:
        print(f"[ERROR] Exception in upload_to_sendbig: {e}")
        return None


# START command
@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await message.reply(
        "👋 Hello! Send me any file (photo, video, audio, document) up to 2 GB "
        "and I’ll upload it to SendBig and give you a download link.\n\n"
        "Use /help for more info."
    )


# HELP command
@app.on_message(filters.command("help"))
async def help_cmd(client: Client, message: Message):
    await message.reply(
        "📚 *How to use this bot:*\n"
        "- Send me any file up to 2 GB.\n"
        "- I will upload it to SendBig with live progress updates.\n"
        "- After upload, you will get a direct download link.\n\n"
        "💡 Tip: For very large files, send as a document."
    )


# File handler
@app.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def file_handler(client: Client, message: Message):
    reply = await message.reply("⏳ Downloading your file...")
    file_path = None

    try:
        # Download file from Telegram
        file_path = await message.download()
        await reply.edit("📤 Preparing upload to SendBig... 0.00%")

        # Upload file to SendBig
        link = upload_to_sendbig(file_path, reply, client)

        # Delete local file
        if file_path:
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"[WARNING] Could not delete file: {e}")

        # Reply with link or fail message
        if link:
            await reply.edit(f"✅ Upload complete!\n🔗 Download here:\n{link}")
        else:
            await reply.edit("❌ Upload failed. SendBig may be busy. Try again later.")

    except Exception as e:
        import traceback
        print(f"[ERROR] Exception in file_handler: {e}")
        traceback.print_exc()
        await reply.edit("❌ Error processing your file. Please try again.")


if __name__ == "__main__":
    print("Bot is starting...", flush=True)
    try:
        app.run()
    except Exception as e:
        import traceback
        print("[FATAL] Bot crashed:", e)
        traceback.print_exc()
