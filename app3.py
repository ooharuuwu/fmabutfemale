import discord
import requests
import json
import re
import os
import glob
import instaloader
import yt_dlp
from dotenv import load_dotenv
import asyncio
from yt_dlp import YoutubeDL
import uuid

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI = os.getenv("GEMINI_API_KEY")

loader = instaloader.Instaloader(
    download_pictures=False,
    download_comments=False,
    download_geotags=False,
    download_video_thumbnails=False,
    save_metadata=False,
    post_metadata_txt_pattern="",
    compress_json=False
)

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    content = message.content.strip()

    if content.startswith("https://www.instagram.com/"):
        try:
            await message.edit(suppress = True)
        except Exception:
            pass


        await message.channel.send("📸 Downloading Instagram media...", delete_after=3)
        media_files = downloadinsta(content)

        if media_files:
            discord_files = [discord.File(fp) for fp in media_files]
            await message.reply(files=discord_files, mention_author=True)            
            # Clean up
            for fp in media_files:
                try:
                    os.remove(fp)
                except OSError:
                    pass


            try:  # shut moxbt
                def check(m):
                    return (
                        m.author.id == 760904896970096660 and
                        m.channel == message.channel
                    )

                reply = await bot.wait_for("message", timeout=55, check=check)
                await reply.delete()
            except asyncio.TimeoutError:
                        pass
            

        else:
            await message.channel.send("No media found or failed to download.", delete_after=3)
        return

    if content.startswith("https://x.com/"):
        video = downloadtwitter(content)
        if video:
            try:
                await message.edit(suppress = True)
            except Exception:
                pass

            await message.reply(file=discord.File(video), mention_author=True)
            os.remove(video)

            try:  # shut moxbt
                def check(m):
                    return (
                        m.author.id == 760904896970096660 and
                        m.channel == message.channel
                    )

                reply = await bot.wait_for("message", timeout=55, check=check)
                await reply.delete()
            except asyncio.TimeoutError:
                        pass
        return

def downloadinsta(url):
    os.makedirs("insta", exist_ok=True)

    # 1. Try video download with yt-dlp
    try:
        output_path = f"insta/{uuid.uuid4()}.mp4"
        ydl_opts = {
            'outtmpl': output_path,
            'format': 'bv*[height<=720]+ba/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'quiet': True,
            'noplaylist': True,
            'no_mtime': True,
            'writesubtitles': False,
            'writeinfojson': False,
            'writeannotations': False,
            'cookiefile': 'cookies.txt'

        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        if os.path.exists(output_path):
            return [output_path]
    except Exception as e:
        print(f"yt-dlp Error (video): {e}")

    # 2. Fallback to download images via instaloader
    try:
        match = re.search(r"instagram\.com/p/([A-Za-z0-9_-]+)/?", url)
        if not match:
            return None
        shortcode = match.group(1)
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        media_files = []
        nodes = post.get_sidecar_nodes() if post.typename == "GraphSidecar" else [post]

        for idx, node in enumerate(nodes):
            if hasattr(node, 'display_url'):
                img_url = node.display_url
                base_filename = f"insta/{shortcode}_{idx}"
                # Download image manually to avoid double extension
                try:
                    response = requests.get(img_url)
                    response.raise_for_status()
                    file_path = base_filename + ".jpg"
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    media_files.append(file_path)
                except Exception as img_err:
                    print(f"Image download error: {img_err}")
        if media_files:
            return media_files
    except Exception as e:
        print(f"Instaloader Error (images): {e}")

    # 3. No media found
    return None

def downloadtwitter(url):
    FOLDER = "x"
    os.makedirs(FOLDER, exist_ok=True)
    ydl_opts = {
        'outtmpl': f'{FOLDER}/%(id)s.%(ext)s',
        'quiet': True,
        'noplaylist': True,
        'merge_output_format': 'mp4',
        'format': 'best[ext=mp4]/best',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
            return video_path
    except Exception as e:
        print(f"Download Error: {e}")
        return None

bot.run(TOKEN)
