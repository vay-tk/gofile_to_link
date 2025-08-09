from pyrogram import Client, filters
import requests
import os

# Read from environment variables (set these in Railway)
APP_ID = int(os.environ.get("APP_ID"))
APP_HASH = os.environ.get("APP_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Initialize the bot
app = Client("gofilebot", api_id=APP_ID, api_hash=APP_HASH, bot_token=BOT_TOKEN)

def get_gofile_server():
    """Get an available Gofile server."""
    try:
        response = requests.get("https://api.gofile.io/getServer", timeout=10)
        if response.status_code == 200 and response.text.strip():
            data = response.json()
            if data.get('status') == 'ok':
                return data.get('data', {}).get('server')
    except Exception as e:
        print(f"Error getting Gofile server: {e}")
    return None

def upload_to_gofile(file_path):
    """Upload file to Gofile and return download link."""
    # First get an available server
    server = get_gofile_server()
    if not server:
        print("Failed to get Gofile server")
        return None
    
    url = f"https://{server}.gofile.io/uploadFile"
    try:
        with open(file_path, "rb") as f:
            files = {'file': f}
            response = requests.post(url, files=files, timeout=60)
        
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text[:200]}...")  # First 200 chars for debugging
        
        # Check if response is successful
        if response.status_code != 200:
            return None
            
        # Check if response has content
        if not response.text.strip():
            return None
            
        data = response.json()
        if data.get('status') == 'ok':
            return data.get('data', {}).get('downloadPage')
        else:
            print(f"API returned status: {data.get('status')}")
            return None
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Error uploading to Gofile: {e}")
        return None

@app.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def handle_file(client, message):
    """When a user sends a file, upload to Gofile and return link."""
    try:
        await message.reply("📤 Uploading file to Gofile...")
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
            await message.reply("❌ Failed to upload the file to Gofile. Please try again later.")
    except Exception as e:
        await message.reply("❌ An error occurred while processing your file.")
        print(f"Error in handle_file: {e}")

if __name__ == "__main__":
    app.run()
