import discord
from discord.ext import commands
import asyncio
import datetime
from discord.ui import Button, View
import mysql.connector
from mysql.connector import Error
import pytz
import re

TOKEN = "YOUR_BOT_TOKEN" # Or you can use .env file

# ======== CONFIG ========
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True  

bot = commands.Bot(command_prefix='@', intents=intents)

SOURCE_CHANNEL_ID = 1324748047342637138 # Change to your source channel ID
TARGET_CHANNEL_ID = 1339364514700988549 # Change to your target channel ID
BOT_OWNER_ID = 427485822154178570 # Change to your bot owner ID
BOT_STATUS_CHANNEL_ID = 1343717255388725319 # Change to your bot status channel ID

ALLOWED_ROLES = [CHANGE FOR YOUR ALLOWED ROLES ID]
ALLOWED_CHANNELS = [CHANGE FOR YOUR ALLOWED CHANNELS ID]

ALLOWED_STRIKE_ROLE_IDS = [CHANGE FOR YOUR ALLOWED STRIKE ROLE ID (for example: 1324457046850146394, 1324458184731000943, 1335004257786658886)]

ALLOWED_DELETE_USER_IDS = [CHANGE FOR YOUR ALLOWED DELETE USER ID (for example: 552517186309193731, 427485822154178570)]

PING_USERS_IDS = [CHANGE FOR YOUR PING USERS ID (for example: 968786450030145567, 695368533927919696, 427485822154178570)]

gank_logs = []
strikes = {}
gank_count = 0  # Variable to track the number of ganks
current_participants = []  # Variable to store the participants of the current gank

DB_CONFIG = {
    'host': 'CHANGE FOR YOUR DATABASE HOST',
    'user': 'CHANGE FOR YOUR DATABASE USER',
    'password': 'CHANGE FOR YOUR DATABASE PASSWORD',
    'database': 'YOUR_DATABASE_NAME', # Change to your database name   
    'port': 3306 # TODO: Change to 3306 if you're using a local database    
}

def create_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def initialize_database():
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gank_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    message_id BIGINT,
                    message_content TEXT,
                    participants TEXT,
                    timestamp DATETIME,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
        except Error as e:
            print(f"Database initialization error: {e}")
        finally:
            connection.close()

def load_gank_logs():
    global gank_logs
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT message_id, message_content, participants, 
                CONVERT_TZ(timestamp, '+00:00', '+01:00') as timestamp 
                FROM gank_logs ORDER BY timestamp DESC
            """)
            rows = cursor.fetchall()
            print(f"Loaded {len(rows)} gank logs from the database.")
            gank_logs = [(row[0], row[1], row[2], row[3].strftime("%Y-%m-%d %H:%M")) for row in rows]
            print(f"Gank logs: {gank_logs}")
        except Error as e:
            print(f"Error loading gank logs: {e}")
        finally:
            connection.close()

def save_gank_log(message_id, message_content, participants, timestamp):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO gank_logs (message_id, message_content, participants, timestamp)
                VALUES (%s, %s, %s, %s)
            """, (message_id, message_content, participants, timestamp))
            connection.commit()
            load_gank_logs()  # Odświeżamy listę gank_logs po dodaniu nowego ganka
        except Error as e:
            print(f"Error saving gank log: {e}")
        finally:
            connection.close()

class GankLogView(View):
    def __init__(self, gank_logs):
        super().__init__(timeout=60)
        self.gank_logs = gank_logs
        self.current_page = 0
        self.total_pages = len(gank_logs)

        self.add_item(Button(label="◀️ Previous", custom_id="prev", style=discord.ButtonStyle.primary, disabled=True))
        self.add_item(Button(label="Next ▶️", custom_id="next", style=discord.ButtonStyle.primary, disabled=self.total_pages <= 1))
        self.add_item(Button(label="👥 Participants", custom_id="participants", style=discord.ButtonStyle.secondary))

    async def update_message(self, interaction, page_change):
        self.current_page += page_change
        
        prev_button = self.children[0]
        next_button = self.children[1]
        
        prev_button.disabled = self.current_page == 0
        next_button.disabled = self.current_page >= self.total_pages - 1

        _, message, _, timestamp = self.gank_logs[self.current_page]
        
        content = (
            "```md\n"
            f"# Gank Log ({self.current_page + 1}/{self.total_pages})\n"
            f"Date: {timestamp}\n"
            "```\n"
            f"{message}"
        )

        await interaction.response.edit_message(content=content, view=self)

    async def interaction_check(self, interaction):
        if interaction.data["custom_id"] == "prev":
            await self.update_message(interaction, -1)
        elif interaction.data["custom_id"] == "next":
            await self.update_message(interaction, 1)
        elif interaction.data["custom_id"] == "participants":
            _, _, participants, _ = self.gank_logs[self.current_page]
            if participants and participants.lower() != "no participants":
                participants_set = set(p.strip().lower().capitalize() for p in participants.split(',') if p.strip())
                participants_list = '\n'.join([f"• {p.capitalize()}" for p in sorted(participants_set)])
                await interaction.response.send_message(
                    "```md\n"
                    f"# Participants for Gank {self.current_page + 1}/{self.total_pages}\n"
                    "```\n"
                    f"{participants_list}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message("❗ No participants found.", ephemeral=True)
        return True

def has_allowed_role(ctx):
    return any(role.id in ALLOWED_ROLES for role in ctx.author.roles) or ctx.author.id == BOT_OWNER_ID

def is_bot_owner(ctx):
    return ctx.author.id == BOT_OWNER_ID

def is_allowed_channel(ctx):
    return ctx.channel.id in ALLOWED_CHANNELS

def has_strike_role(ctx):
    return any(role.id in ALLOWED_STRIKE_ROLE_IDS for role in ctx.author.roles)

@bot.event
async def on_ready():   
    print(f'✅ Logged in as {bot.user}')
    initialize_database()
    load_gank_logs()
    channel = bot.get_channel(BOT_STATUS_CHANNEL_ID)
    if channel:
        poland_tz = pytz.timezone('Europe/Warsaw')
        startup_time = datetime.datetime.now(poland_tz).strftime("%Y-%m-%d %H:%M:%S")
        await channel.send(
            "```md\n"
            "# Bot Status Update\n"
            "```\n"
            f"✅ Bot is now online!\n"
            f"📅 Started at: {startup_time}"
        )

@bot.event
async def on_message(message):
    global gank_count, current_participants  # Używamy globalnych zmiennych

    if message.channel.id == SOURCE_CHANNEL_ID and not message.author.bot:
        content_lower = message.content.lower()
        if "gank won" in content_lower or "gank lost" in content_lower:
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M")
            target_channel = bot.get_channel(TARGET_CHANNEL_ID)
            author_mention = message.author.mention
            
            await target_channel.send(
                "```md\n"
                "# New Gank Log\n"
                "```\n"
                f"Gank author: {author_mention}\n\n\n\n"  
                f"{author_mention}\n\n"  
                f"{message.content}\n\n"
                "**Who were in gank?** (write usernames)"
            )

            def check(m):
                return m.channel.id == TARGET_CHANNEL_ID and not m.author.bot

            try:
                response = await bot.wait_for('message', check=check, timeout=60.0)
                participants = response.content.strip() if response.content.strip() else "No participants"

            except asyncio.TimeoutError:
                participants = "No participants"

            final_message = f"{message.content}"

            sent_message = await target_channel.send(
                "```md\n"
                "# Gank Log\n"
                "```\n"
                f"Gank author: {author_mention}\n\n\n\n"  
                f"{final_message}"
            )
            
            save_gank_log(sent_message.id, final_message, participants, message.created_at)
            gank_logs.append((sent_message.id, final_message, participants, timestamp))

            gank_count += 1  # Zwiększamy licznik ganków

            # Resetujemy lokalną listę uczestników przy dodawaniu nowego ganka
            current_participants = []  # Resetujemy listę uczestników

            # Dodajemy uczestników do current_participants
            if participants and participants != "No participants":
                current_participants.extend([p.strip() for p in participants.split(',')])

    await bot.process_commands(message)

@bot.command(name='ganklogs')
@commands.check(is_allowed_channel)
@commands.dynamic_cooldown(lambda ctx: commands.Cooldown(1, 120) if not has_allowed_role(ctx) else None, commands.BucketType.user)
async def ganklogs_command(ctx):
    if not gank_logs:
        await ctx.send("📭 No gank logs available yet.")
        return

    for index, (_, message, _, timestamp) in enumerate(gank_logs):
        content = (
            "```md\n"
            f"# Gank Log ({index + 1}/{len(gank_logs)})\n"
            f"Date: {timestamp}\n"
            "```\n"
            f"{message}"
        )

        view = GankLogView(gank_logs)
        await ctx.send(content=content, view=view)
        break

@bot.command(name='delete')
@commands.check(is_allowed_channel)
async def delete_gank(ctx, gank_id: int):
    if ctx.author.id not in ALLOWED_DELETE_USER_IDS:
        await ctx.send("🚫 You don't have permission to use this command.")
        return

    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM gank_logs WHERE id = %s", (gank_id,))
            connection.commit()
            if cursor.rowcount > 0:
                await ctx.send(f"✅ Gank with ID {gank_id} has been deleted.")
                # Aktualizujemy listę gank_logs
                load_gank_logs()
            else:
                await ctx.send("❌ Invalid gank ID.")
        except Error as e:
            print(f"Error deleting gank log: {e}")
            await ctx.send("❌ An error occurred while deleting the gank log.")
        finally:
            connection.close()
    else:
        await ctx.send("❌ Could not connect to the database.")

@bot.command(name='gankparty')
@commands.check(is_allowed_channel)
async def gankparty(ctx):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT participants FROM gank_logs 
                ORDER BY timestamp DESC LIMIT 5
            """)
            rows = cursor.fetchall()

            if not rows:
                await ctx.send("📭 No participants found in the last 5 ganks.")
                return

            participants_set = set()  # Używamy zestawu, aby uniknąć duplikatów
            for row in rows:
                participants = row[0]
                if participants:
                    # Rozdzielamy tylko po przecinkach
                    participants_list = participants.split(',')
                    participants_set.update(participant.strip().lower().capitalize() for participant in participants_list if participant.strip().lower() != "no participants")

            if not participants_set:
                await ctx.send("📭 No participants found in the last 5 ganks.")
                return

            # Sortujemy uczestników
            sorted_participants = sorted(participants_set)

            # Estetyczne formatowanie uczestników
            participants_list = '\n'.join([f"• {p.capitalize()}" for p in sorted_participants])
            content = (
                "```md\n"
                "# Participants from the Last 5 Ganks\n"
                "```\n"
                f"{participants_list}"
            )

            await ctx.send(content)

        except Error as e:
            print(f"Error fetching participants: {e}")
            await ctx.send("❌ An error occurred while fetching participants.")
        finally:
            connection.close()
    else:
        await ctx.send("❌ Could not connect to the database.")

@bot.command(name='pavg')
async def participant_average(ctx):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT participants FROM gank_logs WHERE participants IS NOT NULL")
            rows = cursor.fetchall()

            participant_count = {}
            total_ganks = len(rows)

            for row in rows:
                participants = row[0]
                if participants:
                    for participant in participants.split(','):
                        participant = participant.strip().capitalize()
                        if participant:
                            if participant in participant_count:
                                participant_count[participant] += 1
                            else:
                                participant_count[participant] = 1

            if not participant_count:
                await ctx.send("📭 No participants found.")
                return

            result = "```md\n# Average Participation\n"
            for participant, count in participant_count.items():
                average = (count / total_ganks) * 100
                result += f"{participant}: {average:.2f}%\n"
            result += "```"

            await ctx.send(result)

        except Error as e:
            print(f"Error fetching participant averages: {e}")
            await ctx.send("❌ An error occurred while calculating averages.")
        finally:
            connection.close()
    else:
        await ctx.send("❌ Could not connect to the database.")

# Add other commands as needed...

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        remaining_time = int(error.retry_after)
        minutes = remaining_time // 60
        seconds = remaining_time % 60
        await ctx.send(f"⏳ Please wait {minutes}m {seconds}s before using this command again.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ Missing required arguments. Check the command format.")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("🚫 You don't have permission to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")

bot.run(TOKEN)