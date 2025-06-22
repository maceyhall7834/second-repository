import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
import os
import asyncio
import random
from ping3 import ping  # Make sure to install ping3 with `pip install ping3`
from dotenv import load_dotenv  # Import dotenv to load environment variables
from keep_alive import keep_alive

# Load environment variables from .env file
load_dotenv()

# Set up the bot with a command prefix
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Create a folder for downloads if it doesn't exist
os.makedirs("downloads/mp3", exist_ok=True)
os.makedirs("downloads/mp4", exist_ok=True)

async def download_and_convert_with_dropdown(ctx, url, to_mp3=False):
    try:
        output_folder = f"downloads/{'mp3' if to_mp3 else 'mp4'}"

        ydl_opts = {
            'format': 'bestaudio/best' if to_mp3 else 'bestvideo+bestaudio/best',
            'outtmpl': f"{output_folder}/%(id)s.{ 'mp3' if to_mp3 else 'webm'}",
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
async def ping(ctx, ip_address: str = "8.8.8.8"):
    """
    Pings the specified IP address and returns the average, highest, and lowest ping times.

    Parameters:
        `<ip_address>` The IP address to ping (default is 8.8.8.8).
    """
    ping_times = []
    num_pings = 5  # Number of pings to perform

    for _ in range(num_pings):
        response = ping(ip_address)
        if response is not None:
            ping_times.append(response * 1000)  # Convert to milliseconds
        await asyncio.sleep(0.5)  # Wait a bit between pings

    if not ping_times:
        await ctx.send(f"`Failed to ping {ip_address}.`")
        return

    average_ping = sum(ping_times) / len(ping_times)
    highest_ping = max(ping_times)
    lowest_ping = min(ping_times)

    # Create an embed for the ping results
    embed = discord.Embed(title=f"Ping results for {ip_address}", color=discord.Color.blue())
    embed.add_field(name="Average Ping", value=f"{average_ping:.2f} ms", inline=False)
    embed.add_field(name="Highest Ping", value=f"{highest_ping:.2f} ms", inline=False)
    embed.add_field(name="Lowest Ping", value=f"{lowest_ping:.2f} ms", inline=False)
    embed.add_field(name="Ping Speeds", value=", ".join(f"{ping:.2f} ms" for ping in ping_times), inline=False)

    await ctx.send(embed=embed)

# Run the bot with your token
bot.run(os.getenv('TOKEN'))
keep_alive()
