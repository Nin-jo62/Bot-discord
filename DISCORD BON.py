import discord
import os
import sqlite3
import qrcode
import atexit
import secrets
import string
from io import BytesIO
from dotenv import load_dotenv
from datetime import datetime
from discord.ext import commands
from discord import app_commands

# ======================
# ENV
# ======================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 877372951064875038
SALON_BON_ID = 1455933702692667412
SALON_LOG_ID = 1455951537380655338

ROLE_AUTORISE_ID = 1455947238340558939
ROLE_BONS_ID = 1456071275830186035

STATE_FILE = "bot_state.txt"

# ======================
# INTENTS
# ======================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ======================
# DATABASE
# ======================
db = sqlite3.connect("bons.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS bons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT,
    prenom TEXT,
    nom TEXT,
    telephone TEXT,
    valeur TEXT,
    date TEXT,
    auteur TEXT,
    image_url TEXT,
    statut TEXT
)
""")
db.commit()

# ======================
# MÉMOIRE TEMPORAIRE
# ======================
bons_en_attente = {}

# ======================
# UTILS
# ======================

def generer_numero_bon():
    alphabet = string.ascii_uppercase + string.digits
    code = ''.join(secrets.choice(alphabet) for _ in range(10))
    return f"BON-{code}"


def generer_qr(data: str):
    qr = qrcode.make(data)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

async def log_action(message):
    salon = bot.get_channel(SALON_LOG_ID)
    if salon:
        await salon.send(message)

# ======================
# MODAL
# ======================
class BonModal(discord.ui.Modal, title="Bon d'achat"):
    prenom = discord.ui.TextInput(label="Prénom")
    nom = discord.ui.TextInput(label="Nom")
    telephone = discord.ui.TextInput(label="Téléphone")
    valeur = discord.ui.TextInput(label="Valeur du bon")

    async def on_submit(self, interaction: discord.Interaction):
        numero = generer_numero_bon()
        date_now = datetime.now().strftime("%d/%m/%Y %H:%M")

        bons_en_attente[interaction.user.id] = {
            "numero": numero,
            "prenom": self.prenom.value,
            "nom": self.nom.value,
            "telephone": self.telephone.value,
            "valeur": self.valeur.value,
            "date": date_now,
            "auteur": str(interaction.user)
        }

        await interaction.response.send_message(
            f"🧾 **Bon {numero} créé**\n📸 Envoie maintenant la photo de la facture.",
            ephemeral=True
        )

# ======================
# CAPTURE IMAGE
# ======================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    data = bons_en_attente.get(message.author.id)
    if not data or not message.attachments:
        return

    image = message.attachments[0]

    try:
        await message.delete()
    except:
        pass

    statut = "EN_ATTENTE"

    cursor.execute("""
    INSERT INTO bons VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["numero"],
        data["prenom"],
        data["nom"],
        data["telephone"],
        data["valeur"],
        data["date"],
        data["auteur"],
        image.url,
        statut
    ))
    db.commit()

    del bons_en_attente[message.author.id]

    qr_buffer = generer_qr(
        f"http://127.0.0.1:8080/bon/{data['numero']}"
    )


    file = discord.File(fp=qr_buffer, filename="qr.png")

    embed = discord.Embed(
        title="🎟️ Nouveau bon d'achat",
        color=discord.Color.green()
    )
    embed.add_field(name="Numéro", value=data["numero"], inline=False)
    embed.add_field(name="Client", value=f"{data['prenom']} {data['nom']}", inline=False)
    embed.add_field(name="Téléphone", value=data["telephone"], inline=False)
    embed.add_field(name="Valeur", value=data["valeur"], inline=False)
    embed.add_field(name="Statut", value=statut, inline=False)
    embed.add_field(name="Date", value=data["date"], inline=False)
    embed.set_image(url=image.url)
    embed.set_thumbnail(url="attachment://qr.png")

    salon = bot.get_channel(SALON_BON_ID)
    await salon.send(embed=embed, file=file)

    await log_action(
        f"🎟️ **Nouveau bon créé**\n"
        f"📄 Numéro : `{data['numero']}`\n"
        f"👤 Client : {data['prenom']} {data['nom']}\n"
        f"👤 Par : {message.author}\n"
        f"💰 Valeur : {data['valeur']}\n"
        f"🕒 {data['date']}"
    )

# ======================
# COMMANDES
# ======================
@bot.tree.command(name="bon", description="Créer un bon")
@app_commands.checks.has_role(ROLE_AUTORISE_ID)
async def bon(interaction: discord.Interaction):

    if interaction.channel.id != SALON_BON_ID:
        await interaction.response.send_message(
            "⛔ Cette commande est utilisable uniquement dans le salon des bons.",
            ephemeral=True
        )
        return

    await interaction.response.send_modal(BonModal())

@bot.tree.command(name="bons", description="Lister les bons")
@app_commands.checks.has_role(ROLE_BONS_ID)
async def bons(interaction: discord.Interaction):

    if interaction.channel.id != SALON_LOG_ID:
        await interaction.response.send_message(
            "⛔ Cette commande est utilisable uniquement dans le salon des logs.",
            ephemeral=True
        )
        return

    cursor.execute("""
    SELECT numero, valeur, statut, prenom, nom
    FROM bons
    ORDER BY id DESC
    LIMIT 10
    """)
    rows = cursor.fetchall()

    if not rows:
        await interaction.response.send_message("📭 Aucun bon.", ephemeral=True)
        return

    msg = "🎟️ **Derniers bons enregistrés**\n\n"
    for n, v, s, p, nom in rows:
        msg += f"• `{n}` | {v}€ | **{s}** | {p} {nom}\n"

    await interaction.response.send_message(msg)

# ======================
# READY (LOG FIABLE)
# ======================
@bot.event
async def on_ready():
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    if os.path.exists(STATE_FILE):
        await log_action(
            "🔴 **Bot arrêté précédemment (crash ou arrêt détecté)**\n"
            f"🕒 {now}"
        )

    with open(STATE_FILE, "w") as f:
        f.write("ONLINE")

    print(f"✅ Bot connecté : {bot.user}")
    await bot.tree.sync()
    await log_action(f"🟢 **Bot démarré**\n🕒 {now}")

# ======================
# CLEAN EXIT (OPTIONNEL)
# ======================
def clean_exit():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

atexit.register(clean_exit)

bot.run(TOKEN)
