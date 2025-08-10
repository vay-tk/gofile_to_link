import os
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor

# Telegram credentials
APP_ID = int(os.environ.get("APP_ID"))
APP_HASH = os.environ.get("APP_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Smash.com upload URL
SMASH_UPLOAD_URL = "https://api.fromsmash.com/upload"

# Init bot
app = Client("smashbot", api_id=APP_ID, api_hash=APP_HASH, bot_token=BOT_TOKEN)


def make_progress_callback(message: Message, client: Client):
    """Progress callback for MultipartEncoderMonitor."""
    def progress(monitor: MultipartEncoderMonitor):
        try:
            percent = (monitor.bytes_read / monitor.len) * 100
            if not hasattr(progress, "last_percent") or percent - progress.last_percent >= 1:
                progress.last_percent = percent
                client.loop.create_task(
                    message.edit_text(f"📤 Uploading... {percent:.2f}%")
                )
        except Exception as e:
            print(f"[WARNING] Progress update error: {e}")
    progress.last_percent = 0
    return progress


def upload_to_smash(file_path, message, client):
    """Upload the file to Smash and return download link."""
    try:
        m_encoder = MultipartEncoder(
            fields={'files': (os.path.basename(file_path), open(file_path, 'rb'))}
        )
        monitor = MultipartEncoderMonitor(m_encoder, make_progress_callback(message, client))
        headers = {"Content-Type": monitor.content_type}
        print("[INFO] Starting upload to Smash...")

        r = requests.post(SMASH_UPLOAD_URL, data=monitor, headers=headers, timeout=1200)

        print("[INFO] Upload POST finished. Status:", r.status_code)

        # Smash responds with JSON containing `uri`
        data = r.json()
        uri = data.get("uri")
        if uri:
            link = f"https://fromsmash.com{uri}"
            return link
        else:
            print("[ERROR] Could not extract Smash link:", data)
            return None
    except Exception as e:
        print(f"[ERROR] Upload to Smash failed: {e}")
        return None


@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await message.reply(
        "👋 Hello! Send me any file up to 2 GB and I will upload it to Smash.com and send you the link.\n"
        "Use /help for usage instructions."
    )


@app.on_message(filters.command("help"))
async def help_cmd(client: Client, message: Message):
    await message.reply(
        "📚 *How to use this bot:*\n"
        "- Send any file (document, video, audio, or photo) up to 2 GB.\n"
        "- I’ll upload it to Smash.com with real-time progress.\n"
        "- You’ll get a direct download link.\n\n"
        "💡 For files > 50MB, send as *Document* for reliability."
    )


@app.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def file_handler(client: Client, message: Message):
    reply = await message.reply("⏳ Downloading your file...")
    file_path = None

    try:
        # Download from Telegram
        file_path = await message.download()
        await reply.edit("📤 Preparing upload... 0.00%")

        # Upload to Smash
        link = upload_to_smash(file_path, reply, client)

        # Clean up file
        if file_path:
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"[WARNING] Could not delete file: {e}")

        if link:
            await reply.edit(f"✅ Upload complete!\n🔗 Download link:\n{link}")
        else:
            await reply.edit("❌ Upload failed. Please try again later.")

    except Exception as e:
        import traceback
        print(f"[ERROR] Exception in file_handler: {e}")
        traceback.print_exc()
        await reply.edit("❌ Error processing your file. Try again.")


if __name__ == "__main__":
    print("Bot is starting...", flush=True)
    try:
        app.run()
    except Exception as e:
        import traceback
        print("[FATAL] Bot crashed:", e)
        traceback.print_exc()
