import os
import discord
from discord.ext import commands
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Debugging step to check if the token is loaded
print(f"DISCORD_TOKEN: {os.getenv('DISCORD_TOKEN')}")


# Get the bot token and database URL from the .env file
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

# Debugging step: Check if the token is loaded
if not TOKEN:
    print("DISCORD_TOKEN is not set. Please check your .env file.")

# Enable necessary intents (including message content intent)
intents = discord.Intents.default()
intents.message_content = True  # Enables the bot to read message content

# Initialize the bot with the specified intents
bot = commands.Bot(command_prefix="!", intents=intents)

# Function to connect to the PostgreSQL database
def connect_db():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

# Function to initialize the database with a raids table
def init_db():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raids (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50),
            map_name VARCHAR(100),
            map_section VARCHAR(100),
            boss_name VARCHAR(100),
            gear TEXT,
            reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    cursor.close()
    conn.close()

# Ensure the database is initialized when the bot is ready
@bot.event
async def on_ready():
    init_db()
    print(f'Bot connected as {bot.user}')

# Command to report a boss encounter
@bot.command(name='report_boss')
async def report_boss(ctx, map_name: str, map_section: str, boss_name: str, *, gear: str):
    user_id = str(ctx.author.id)
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO raids (user_id, map_name, map_section, boss_name, gear)
        VALUES (%s, %s, %s, %s, %s);
    ''', (user_id, map_name, map_section, boss_name, gear))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    await ctx.send(f"Boss {boss_name} reported on {map_name} in {map_section} carrying {gear}.")

# Function to calculate the most reported boss location
def calculate_boss_prediction(boss_name):
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT map_name, map_section, COUNT(*) AS report_count
        FROM raids
        WHERE boss_name = %s
        GROUP BY map_name, map_section
        ORDER BY report_count DESC
        LIMIT 1;
    ''', (boss_name,))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if result:
        return result
    else:
        return None

# Command to predict the most likely boss location
@bot.command(name='predict_boss')
async def predict_boss(ctx, boss_name: str):
    prediction = calculate_boss_prediction(boss_name)
    
    if prediction:
        map_name, map_section, report_count = prediction
        await ctx.send(f"{boss_name} is most likely to spawn on {map_name} in {map_section} (based on {report_count} reports).")
    else:
        await ctx.send(f"No data available for {boss_name} yet.")

# Run the bot
bot.run(TOKEN)

