import os
import logging
import logging.handlers
import discord
import yt_dlp as youtube_dl
import wave
from typing import List, Optional
from dotenv import load_dotenv
from discord.ext import commands
from discord import slash_command

# Load environment variables from our .env file
load_dotenv()

# Setting the preferred bot command prefix with the variable from our .env file
PREFIX = os.getenv('PREFIX')
# Twitch.tv link used for Discord streaming status
TTV_STREAM = os.getenv('TTV_STREAM')
# OAuth Token needed to login under her Discord app user.
TOKEN = os.getenv('TOKEN')
# Setting the home guild you wish to use for Himari. Must be casted to an integer.
GUILD_ID = discord.Object(id=int(os.getenv('GUILD')))    

# Checking to see if the REQUIRED environment variables are set
if not TOKEN or not PREFIX:
    raise ValueError("Environment variables TOKEN and PREFIX must be set!")

class HimariBot(commands.Bot):
    
    async def setup_hook(self):
        print("Running setup_hook...!")
        print("Setup hook completed! Yay!")
    
if __name__ == "__main__":
    # Declaring our intents and Himari instance
    intents = discord.Intents.all()
    intents.message_content = True 
    himariBot = HimariBot(command_prefix=PREFIX, intents=intents)
    himariBot.load_extension('cogs.himari_cog')
    
    try:
        himariBot.run(TOKEN, reconnect=True)
    except KeyboardInterrupt:
        print("Received interrupt. Shutting down gracefully...")
    except Exception as e:
        logging.error(f"Disaster! Critical error has occurred: {e}") 
        print("Oh no! Critical error! Help me, Hina-chan!")
    finally:
        if himariBot.is_closed():
            print("I'm already closed!!")
        else:
            himariBot.close()