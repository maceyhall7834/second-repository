import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
import os
import asyncio
import time
import random
from dotenv import load_dotenv  # Import dotenv to load environment variables
from keep_alive import keep_alive

# Load environment variables from .env file
load_dotenv()

# Set up the bot with a command prefix
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.idle)
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')

# Create a folder for downloads if it doesn't exist
os.makedirs("downloads/mp3", exist_ok=True)
os.makedirs("downloads/mp4", exist_ok=True)

async def download_and_convert_with_dropdown(ctx, url, to_mp3=False):
    if not url:
        await ctx.send("`Please provide a URL to convert. Use !convert <url>`")
        return
    try:
        output_folder = f"downloads/{'mp3' if to_mp3 else 'mp4'}"

        # Choose a random proxy from the list
        proxy = random.choice(proxies)

        ydl_opts = {
            'format': 'bestaudio/best' if to_mp3 else 'bestvideo+bestaudio/best',
            'outtmpl': f"{output_folder}/%(id)s.{ 'mp3' if to_mp3 else 'webm'}",
            'proxy': proxy,  # Use the selected proxy
        }

        conversion_message = await ctx.send("`Getting available qualities...`")

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = [
                discord.SelectOption(
                    label=f"{format['format_id']} - {format.get('resolution', 'Audio')}",
                    value=format['format_id']
                ) for format in info['formats']
            ]

            # Create a Select component
            quality_view = discord.ui.Select(
                placeholder="Quality options",
                options=formats,
                custom_id="quality_select"
            )

            # Create a message with the Select component
            message = await ctx.send("Please select the preferred video quality:", view=discord.ui.View().add_item(quality_view))

            # Wait for the interaction
            interaction_check = lambda inter: inter.custom_id == "quality_select" and inter.message.id == message.id
            interaction = await bot.wait_for("select_option", check=interaction_check, timeout=120)

            # Respond to the interaction
            await interaction.response.defer()

            selected_format = next(
                (option for option in formats if option.value == interaction.values[0]),
                None
            )

            if not selected_format:
                await interaction.followup.send("`Invalid selection. Please try the command again.`")
                return

            await interaction.followup.send(f"`Selected video quality: {selected_format.label}`")

            # Download the video
            await interaction.followup.send(f"`Converting video to {selected_format.label}...`")
            ydl.download([url])

            user = ctx.message.author
            downloaded_file_path = f"{output_folder}/{info['id']}.{ 'mp3' if to_mp3 else 'webm'}"
            renamed_file_path = f"{output_folder}/{info['id']}.{ 'mp3' if to_mp3 else 'mp4'}"

            # Try uploading the file
            try:
                await conversion_message.edit(content=f"`Uploading video...`")
                # Send a new message with the converted file, mentioning the user
                await ctx.send(f'{user.mention}, `Here is the converted video:`',
                               file=discord.File(renamed_file_path))
                await conversion_message.edit(content=f"`Video uploaded successfully.`")
            except discord.errors.HTTPException as upload_error:
                # If uploading fails, send an error message
                await ctx.send(f"`An error occurred during upload. Please check the file and try again.\nError details: {upload_error}`")

            # Remove the file after 10 minutes if it exists
            await asyncio.sleep(600)  # Wait for 10 minutes
            if os.path.exists(renamed_file_path):
                os.remove(renamed_file_path)

    except asyncio.TimeoutError:
        await ctx.send("`Selection timeout. Please try the command again.`")
    except Exception as e:
        error_message = str(e)
        await ctx.send(f"`An error occurred during conversion. Please check the URL and try again.\nError details: {error_message}`")


@bot.command()
async def convert(ctx, url):
    """
    Converts a YouTube video to MP4 or MP3.

    Parameters:
    `<url>` The URL of the video you want to convert.
    """
    await download_and_convert_with_dropdown(ctx, url, to_mp3=False)

@bot.command()
async def ping(ctx):
    """
    Responds to the ping command and sends the response time in an embed.
    """
    start_time = time.time()
    await ctx.send('Pong!')
    end_time = time.time()
    response_time = (end_time - start_time) * 1000  # Convert to milliseconds

    # Create an embed to send the response time
    embed = discord.Embed(title="Ping Response Time", color=discord.Color.red())
    embed.add_field(name="Response Time", value=f"{response_time:.2f} ms", inline=False)

keep_alive()
# Run the bot with your token
bot.run(os.getenv('TOKEN'))
