import os
import requests
import re
from pyrogram import Client, filters
from pyrogram.types import Message
from bs4 import BeautifulSoup

APP_ID = int(os.environ.get("APP_ID"))
APP_HASH = os.environ.get("APP_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SENDBIG_UPLOAD_URL = "https://www.sendbig.com/api-files/upload"

# Initialize Pyrogram bot session
app = Client("sendbigbot", api_id=APP_ID, api_hash=APP_HASH, bot_token=BOT_TOKEN)

def upload_to_sendbig(file_path, progress_callback=None):
    filename = os.path.basename(file_path)
    filesize = os.path.getsize(file_path)
    with open(file_path, "rb") as f:
        files = {'file': (filename, file_read_with_progress(f, filesize, progress_callback))}
        resp = requests.post(SENDBIG_UPLOAD_URL, files=files)
    try:
        data = resp.json()
        if "download_page" in data:  # Typical SendBig API link structure
            return data["download_page"]
        # Fallback: Parse download link from HTML (if JSON is absent)
        match = re.search(r"https://www.sendbig.com/view-file/\w+", resp.text)
        if match:
            return match.group(0)
    except Exception:
        # Try parsing a download link in the raw HTML response
        match = re.search(r"https://www.sendbig.com/view-file/\w+", resp.text)
        if match:
            return match.group(0)
    return None

def file_read_with_progress(f, filesize, progress_callback=None, chunk=1024 * 1024):
    sent = 0
    while True:
        data = f.read(chunk)
        if not data:
            break
        sent += len(data)
        if progress_callback:
            percent = int(sent * 100 / filesize)
            progress_callback(percent)
        yield data

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply(
        "👋 Hello! Send me any file up to 2GB and I will upload it to SendBig and send you the download link.\n\n"
        "Use /help for more details."
    )

@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    await message.reply(
        "1. Send any file (document, photo, video, audio) as a message.\n"
        "2. I'll upload it to SendBig and reply with the download link.\n"
        "3. Max file size: 2GB (Telegram's own bot upload limit).\n"
        "Note: SendBig file links remain valid per their retention policy."
    )

@app.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def handle_file(client: Client, message: Message):
    reply = await message.reply("⏳ Downloading your file...")
    file_path = None

    def progress_updater(percent):
        try:
            client.loop.create_task(reply.edit(f"📤 Uploading to SendBig... {percent}%"))
        except Exception:
            pass  # Edit failures are not critical

    try:
        file_path = await message.download()
        await reply.edit("📤 Uploading to SendBig... 0%")
        link = upload_to_sendbig(file_path, progress_callback=progress_updater)

        if file_path:
            try:
                os.remove(file_path)
            except Exception:
                pass

        if link:
            await reply.edit(f"✅ Uploaded!\nDownload link:\n{link}")
        else:
            await reply.edit("❌ Upload failed (SendBig service error). Try again later.")
    except Exception as e:
    import traceback
    tb = traceback.format_exc()
    print(f"[ERROR] {e}\n{tb}")
    await reply.edit(f"❌ Error: {str(e)}. Please try a smaller file or try again later.")


if __name__ == "__main__":
    print("Bot is starting...", flush=True)
    try:
        app.run()
    except Exception as e:
        import traceback
        print("[FATAL] Bot crashed:", e)
        traceback.print_exc()
