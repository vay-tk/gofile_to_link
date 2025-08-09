import os
import requests
from pyrogram import Client, filters
from pyrogram.types import Message

APP_ID = int(os.environ.get("APP_ID"))
APP_HASH = os.environ.get("APP_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GOFILE_UPLOAD_URL = "https://upload.gofile.io/uploadFile"

# Initialize Pyrogram client
app = Client("gofilebot", api_id=APP_ID, api_hash=APP_HASH, bot_token=BOT_TOKEN)

class ProgressFile:
    def __init__(self, filepath, message: Message, client: Client, chunk_size=1024*1024):
        self.file = open(filepath, 'rb')
        self.file_size = os.path.getsize(filepath)
        self.message = message
        self.client = client
        self.chunk_size = chunk_size
        self.uploaded = 0
        self.last_update = 0

    def __len__(self):
        return self.file_size

    def read(self, size=None):
        if size is None:
            size = self.chunk_size
        data = self.file.read(size)
        if not data:
            return b""
        self.uploaded += len(data)

        # Limit updates to every ~1MB or if first chunk
        if self.uploaded - self.last_update > 1024*1024 or self.uploaded == len(data):
            self.last_update = self.uploaded
            percentage = (self.uploaded / self.file_size) * 100
            # Schedule async edit to update progress message without awaiting here
            self.client.loop.create_task(
                self.message.edit_text(f"📤 Uploading to Gofile... {percentage:.2f}%")
            )
        return data

    def close(self):
        self.file.close()

def upload_to_gofile_with_progress(file_path, message, client):
    """
    Upload file in chunks and update progress message in Telegram.
    """
    try:
        pf = ProgressFile(file_path, message, client)
        files = {'file': ('filename', pf)}

        response = requests.post(GOFILE_UPLOAD_URL, files=files, timeout=300)
        pf.close()
    except Exception as e:
        print(f"[ERROR] Exception during upload: {e}")
        return None

    # Parse response safely
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
        "- I'll download it, upload it to Gofile.io,\n"
        "  and show upload progress in this chat.\n"
        "- After upload, I'll send you the download link.\n\n"
        "⚠️ Large files should be sent as documents for reliability.\n"
        "If upload fails, try again later."
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
