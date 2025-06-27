import discord
from discord.ext import commands
from discord import Embed
import os
from pytube import YouTube
from yt_dlp import YoutubeDL
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
from datetime import datetime
from pathlib import Path
import asyncio
from dotenv import load_dotenv
from keep_alive import keep_alive

# Load environment variables from .env file
load_dotenv()
bot_token = os.getenv('TOKEN')

# Print the retrieved token (for debugging)
print(f"Retrieved token")

# Define intents
intents = discord.Intents.default()
intents.message_content = True

# Create a bot instance with a command prefix, intents, and disable the default help command
bot = commands.Bot(command_prefix='=', intents=intents, help_command=None)

# Store the bot's start time for the uptime command
start_time = datetime.now()

async def convert_to_mp4(video_path, output_path):
    video_clip = VideoFileClip(video_path)
    video_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    video_clip.close()

async def convert_to_mp3(audio_path, output_path):
    audio_segment = AudioSegment.from_file(audio_path)
    audio_segment.export(output_path, format="mp3")

async def download_and_convert_ytdlp(ctx, url, to_mp3=False):
    try:
        output_folder = Path("mp3" if to_mp3 else "mp4")

        ydl_opts = {
            'format': 'bestaudio/best' if to_mp3 else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': str(output_folder / f"%(id)s.{'mp3' if to_mp3 else 'mp4'}"),
            'default_search': 'auto',  # Set default search
        }

        async with ctx.typing():
            conversion_message = await ctx.send("`Fetching video information...`")

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)

            if 'entries' in info_dict:
                video_info = info_dict['entries'][0]
            else:
                video_info = info_dict

            ydl.download([url])

        await asyncio.sleep(5)

        user = ctx.author
        title = video_info.get('title', 'Unknown Title')

        await conversion_message.edit(content=f"`Converting to {'audio' if to_mp3 else 'video'}: {title}`")

        downloaded_file_path = output_folder / f"{video_info['id']}.{'mp3' if to_mp3 else 'mp4'}"
        renamed_file_path = output_folder / f"{video_info['id']}.{'mp3' if to_mp3 else 'mp4'}"

        # Check if the downloaded file exists before renaming
        if downloaded_file_path.exists():
            downloaded_file_path.rename(renamed_file_path)

            # Try uploading the file
            try:
                await conversion_message.edit(content=f"`Uploading: {title}...`")
                # Send a new message with the converted file, mentioning the user
                await ctx.send(f'{user.mention}, `Here is the converted {"audio" if to_mp3 else "video"}: {title}`', file=discord.File(str(renamed_file_path)))
                await conversion_message.edit(content="`Upload complete.`")
            except discord.errors.HTTPException as upload_error:
                # If uploading fails, send an error message
                await ctx.send(f"`Conversion failed. Please check the input and try again.\nError details: {upload_error}`")
        else:
            await ctx.send("`An error occurred during conversion. The downloaded file does not exist.`")

        # Remove the file after 10 minutes if it exists
        if renamed_file_path.exists():
            renamed_file_path.unlink()

    except Exception as e:
        error_message = str(e)
        await ctx.send(f"`Conversion failed. Please check the input and try again.\nError details: {error_message}`")


@bot.command()
async def ytmp3(ctx, *, query):
    await download_and_convert_ytdlp(ctx, query, to_mp3=True)

@bot.command()
async def ytmp4(ctx, *, query):
    await download_and_convert_ytdlp(ctx, query, to_mp3=False)

async def download_and_convert(ctx, url, file_extension):
    print(f"Command received: {ctx.command.name}")

    if not url:
        await ctx.send("`You need to provide a YouTube URL.`")
        return

    yt = YouTube(url)
    title = yt.title
    video_id = yt.video_id  # Get the video ID

    # Start typing status
    await ctx.send(f"`Converting to {file_extension.upper()}: {title}`")
    async with ctx.typing():
        output_file = f"{video_id}.{file_extension}"  # Use video ID in the output file name

        try:
            if file_extension == 'mp3':
                stream = yt.streams.filter(only_audio=True).first()
            else:
                stream = yt.streams.filter(file_extension=file_extension, progressive=True).get_highest_resolution()

            stream.download(output_path='.', filename=output_file.replace('.', ''))
            os.rename(f'{output_file.replace(".", "")}', output_file)

            if os.path.exists(output_file):
                user_ping = f"<@{ctx.author.id}>"
                message = f"{user_ping}, `Here is the converted {'audio' if file_extension == 'mp3' else 'video'}: {title}`"
                await ctx.send(message, file=discord.File(output_file))
            else:
                await ctx.send("`Conversion failed. Please check the input and try again.`")
        except Exception as e:
            await ctx.send(f"`An error occurred: {e}`")
        finally:
            os.remove(output_file)  # Always try to remove the temporary file

# Command to convert YouTube video to MP3
@bot.command()
async def mp3(ctx, url=None):
    await download_and_convert(ctx, url, 'mp3')

# Command to convert YouTube video to MP4
@bot.command()
async def mp4(ctx, url=None):
    await download_and_convert(ctx, url, 'mp4')

# Ping command with embed
@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)  # Convert to milliseconds

    embed = Embed(title="Ping Command", color=0xff342c)
    embed.add_field(name="Latency", value=f"{latency}ms", inline=False)

    await ctx.send(embed=embed)

# Uptime command with embed
@bot.command()
async def uptime(ctx):
    uptime_duration = datetime.now() - start_time
    days, hours, minutes, seconds = uptime_duration.days, uptime_duration.seconds // 3600, (uptime_duration.seconds // 60) % 60, uptime_duration.seconds % 60

    embed = Embed(title="Uptime Command", color=0xff342c)
    embed.add_field(name="Uptime", value=f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds", inline=False)

    await ctx.send(embed=embed)

# Custom help command with embed
@bot.command(name='help')
async def custom_help(ctx):
    embed = Embed(title="Bot Commands", color=0xff342c)  # Set color to #ff342c
    embed.add_field(name="=ytmp3 [URL]", value="Converts a YouTube video to MP3 using YoutubeDLP. `recommended`", inline=False)
    embed.add_field(name="=ytmp4 [URL]", value="Converts a YouTube video to MP4 using YoutubeDLP. `recommended`", inline=False)
    embed.add_field(name="=mp3 [URL]", value="Converts a YouTube video to MP3 using Pytube.", inline=False)
    embed.add_field(name="=mp4 [URL]", value="Converts a YouTube video to MP4 using Pytube.", inline=False)
    embed.add_field(name="=ping", value="Displays the bot's latency.", inline=False)
    embed.add_field(name="=uptime", value="Shows how long the bot has been running.", inline=False)

    await ctx.send(embed=embed)

# Event for handling command errors
@bot.event
async def on_command_error(ctx, error):
    print(f"An error occurred: {error}")

# Command to get the list of joined guilds (exclusive to the owner)
@bot.command(name='guilds')
async def guilds(ctx):
    if ctx.author.id == OWNER_ID:
        guilds_info = '\n'.join([f"{guild.name} (ID: {guild.id})" for guild in bot.guilds])

        embed = Embed(title="List of Joined Guilds", color=0xff342c, description=guilds_info)
        await ctx.send(embed=embed)
    else:
        await ctx.send("`You do not have permission to use this command.`")

# Command to leave a specific guild (exclusive to the owner)
@bot.command(name='leave')
async def leave(ctx, guild_id: int = None):
    if ctx.author.id == OWNER_ID:
        if guild_id is None:
            await ctx.send("`You need to provide a guild ID.`")
            return

        guild = discord.utils.get(bot.guilds, id=guild_id)
        if guild:
            await guild.leave()
            await ctx.send(f"`Left the guild: {guild.name}`")
        else:
            await ctx.send("`Guild not found.`")
    else:
        await ctx.send("`You do not have permission to use this command.`")

# command to get guild info
@bot.command(name='guildinfo')
async def guild_info(ctx, guild_id: int = None):
    if ctx.author.id == OWNER_ID:
        if guild_id is None:
            await ctx.send("`You need to provide a guild ID.`")
            return

        guild = discord.utils.get(bot.guilds, id=guild_id)
        if guild:
            try:
                owner = await bot.fetch_user(guild.owner_id)

                channels_info = '\n'.join([f"{channel.name} (ID: {channel.id})" for channel in guild.channels])

                embed = Embed(title=f"Guild Information: {guild.name}", color=0xff342c)
                embed.add_field(name="Owner", value=f"{owner.name} (ID: {owner.id})", inline=False)

                if channels_info:
                    embed.add_field(name="Channels", value=channels_info, inline=False)

                await ctx.send(embed=embed)
            except discord.errors.Forbidden:
                await ctx.send("`Bot does not have permission to access owner information.`")
            except discord.errors.NotFound:
                await ctx.send("`Owner not found.`")
        else:
            await ctx.send("`Guild not found.`")
    else:
        await ctx.send("`You do not have permission to use this command.`")

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

    # Set the bot's activity (status) to "Watching"
    activity = discord.Activity(type=discord.ActivityType.watching, name="YouTube | =help")
    await bot.change_presence(activity=activity)

keep_alive()
# Run the bot with your token
bot.run('TOKEN')
