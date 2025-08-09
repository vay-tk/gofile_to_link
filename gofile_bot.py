from pyrogram import Client, filters
import requests
import os

# Read from environment variables (set these in Railway)
APP_ID = int(os.environ.get("APP_ID"))
APP_HASH = os.environ.get("APP_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Initialize the bot
app = Client("gofilebot", api_id=APP_ID, api_hash=APP_HASH, bot_token=BOT_TOKEN)

def upload_to_gofile(file_path):
    """Upload file to Gofile and return download link."""
    url = "https://api.gofile.io/uploadFile"
    with open(file_path, "rb") as f:
        files = {'file': f}
        response = requests.post(url, files=files)
    data = response.json()
    if data['status'] == 'ok':
        return data['data']['downloadPage']
    else:
        return None

@app.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def handle_file(client, message):
    """When a user sends a file, upload to Gofile and return link."""
    file_path = await message.download()
    download_link = upload_to_gofile(file_path)

    # Remove local file after upload
    try:
        os.remove(file_path)
    except:
        pass

    if download_link:
        await message.reply(f"✅ File uploaded!\nDownload link: {download_link}")
    else:
        await message.reply("❌ Failed to upload the file to Gofile.")

if __name__ == "__main__":
    app.run()
