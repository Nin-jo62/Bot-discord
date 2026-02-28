import discord
import os
import sqlite3
import qrcode
import secrets
import string
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands

# ======================
# ENV
# ======================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ======================
# IDs
# ======================
GUILD_ID = 837708000096944138
SALON_BON_ID = 1455904723608666248
SALON_LOG_ID = 1457004426760945838

ROLE_BON_ID = 955204891339534406
ROLE_LOG_ID = 1457499722309963943

BASE_URL = "https://bons.legendary-motorsport.com"

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
    numero TEXT UNIQUE,
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
    return "BON-" + ''.join(secrets.choice(alphabet) for _ in range(10))

def generer_qr(url: str):
    qr = qrcode.make(url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

async def log_action(message: str):
    salon = bot.get_channel(SALON_LOG_ID)
    if salon:
        await salon.send(message)

# ======================
# MODAL
# ======================
class BonModal(discord.ui.Modal, title="Créer un bon d'achat"):
    prenom = discord.ui.TextInput(label="Prénom")
    nom = discord.ui.TextInput(label="Nom")
    telephone = discord.ui.TextInput(label="Téléphone")
    valeur = discord.ui.TextInput(label="Valeur du bon ($)")

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
# IMAGE FACTURE
# ======================
@bot.event
async def on_message(message: discord.Message):
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

    bon_url = f"{BASE_URL}/bon/{data['numero']}"
    qr_buffer = generer_qr(bon_url)
    file = discord.File(fp=qr_buffer, filename="qr.png")

    embed = discord.Embed(title="🎟️ Nouveau bon d'achat", color=discord.Color.orange())
    embed.add_field(name="Numéro", value=data["numero"], inline=False)
    embed.add_field(name="Client", value=f"{data['prenom']} {data['nom']}", inline=False)
    embed.add_field(name="Téléphone", value=data["telephone"], inline=False)
    embed.add_field(name="Valeur", value=f"{data['valeur']} $", inline=False)
    embed.add_field(name="Statut", value=statut, inline=False)
    embed.add_field(name="Date", value=data["date"], inline=False)
    embed.set_image(url=image.url)
    embed.set_thumbnail(url="attachment://qr.png")

    salon = bot.get_channel(SALON_BON_ID)
    await salon.send(embed=embed, file=file)

    await log_action(
        f"🎟️ **Bon créé**\n"
        f"📄 `{data['numero']}`\n"
        f"👤 {data['prenom']} {data['nom']}\n"
        f"💰 {data['valeur']} $\n"
        f"👤 Par : {message.author}"
    )

# ======================
# COMMANDES
# ======================
@bot.tree.command(name="bon", description="Créer un bon d'achat")
@app_commands.checks.has_role(ROLE_BON_ID)
async def bon(interaction: discord.Interaction):

    if interaction.channel.id != SALON_BON_ID:
        await interaction.response.send_message(
            "⛔ Commande utilisable uniquement dans le salon des bons.",
            ephemeral=True
        )
        return

    await interaction.response.send_modal(BonModal())

@bot.tree.command(name="bons", description="Lister les bons")
@app_commands.checks.has_role(ROLE_LOG_ID)
async def bons(interaction: discord.Interaction):

    if interaction.channel.id != SALON_LOG_ID:
        await interaction.response.send_message(
            "⛔ Commande utilisable uniquement dans le salon des logs.",
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
        msg += f"• `{n}` | {v} $ | **{s}** | {p} {nom}\n"

    await interaction.response.send_message(msg, ephemeral=True)

# ======================
# READY
# ======================
@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user}")
    await bot.tree.sync()


bot.run(TOKEN)
