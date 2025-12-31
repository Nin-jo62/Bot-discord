import discord
import os
from dotenv import load_dotenv
load_dotenv()
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import sqlite3

GUILD_ID = 877372951064875038
SALON_BON_ID = 1455933702692667412
ROLE_AUTORISE_ID = 1455947238340558939
SALON_LOG_ID = 1455951537380655338

# ======================
# INTENTS
# ======================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # essentiel pour récupérer les rôles correctement

bot = commands.Bot(command_prefix="!", intents=intents)

# ======================
# BASE DE DONNÉES
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
    image_url TEXT
)
""")
db.commit()

def generer_numero_bon():
    cursor.execute("SELECT COUNT(*) FROM bons")
    count = cursor.fetchone()[0] + 1
    annee = datetime.now().year
    return f"BON-{annee}-{count:04d}"

# ======================
# LOGGING
# ======================
async def log_action(bot, message):
    salon = bot.get_channel(SALON_LOG_ID)
    if salon:
        await salon.send(message)

# ======================
# MODAL
# ======================
class BonModal(discord.ui.Modal, title="Bon d'achat"):
    prenom = discord.ui.TextInput(label="Prénom")
    nom = discord.ui.TextInput(label="Nom")
    telephone = discord.ui.TextInput(label="Numéro de téléphone")
    valeur = discord.ui.TextInput(label="Valeur du bon")

    async def on_submit(self, interaction: discord.Interaction):
        date_now = datetime.now().strftime("%d/%m/%Y à %H:%M")
        numero = generer_numero_bon()

        await interaction.response.send_message(
            f"🧾 **Bon {numero} créé**\n"
            "📸 Merci d’envoyer maintenant la photo de la facture.",
            ephemeral=True
        )

        def check(msg):
            return (
                msg.author == interaction.user
                and msg.attachments
                and msg.channel == interaction.channel
            )

        try:
            msg = await bot.wait_for("message", check=check, timeout=120)
            image = msg.attachments[0]

            cursor.execute("""
            INSERT INTO bons VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                numero,
                self.prenom.value,
                self.nom.value,
                self.telephone.value,
                self.valeur.value,
                date_now,
                str(interaction.user),
                image.url
            ))
            db.commit()

            salon = bot.get_channel(SALON_BON_ID)

            embed = discord.Embed(
                title="🎟️ Nouveau bon d'achat",
                color=discord.Color.green()
            )
            embed.add_field(name="Numéro du bon", value=numero, inline=False)
            embed.add_field(name="Prénom", value=self.prenom.value, inline=True)
            embed.add_field(name="Nom", value=self.nom.value, inline=True)
            embed.add_field(name="Téléphone", value=self.telephone.value, inline=False)
            embed.add_field(name="Valeur", value=self.valeur.value, inline=False)
            embed.add_field(name="Date", value=date_now, inline=False)
            embed.set_footer(text=f"Créé par {interaction.user}")
            embed.set_image(url=image.url)

            await salon.send(embed=embed)

            await interaction.followup.send(
                f"✅ Bon **{numero}** envoyé avec succès.",
                ephemeral=True
            )

            # Logging
            await log_action(
                bot,
                f"🎟️ **Nouveau bon créé**\n"
                f"👤 Prénom : {self.prenom.value}\n"
                f"👤 Nom : {self.nom.value}\n"
                f"📞 Téléphone : `{self.telephone.value}`\n"
                f"📄 Numéro : `{numero}`\n"
                f"👤 Par : {interaction.user} ({interaction.user.id})\n"
                f"💰 Valeur : {self.valeur.value}\n"
                f"🕒 {date_now}"
            )

        except Exception:
            await interaction.followup.send(
                "❌ Temps écoulé, aucune image reçue.",
                ephemeral=True
            )

# ======================
# COMMANDE /bon
# ======================
@bot.tree.command(name="bon", description="Créer un bon de réduction")
async def bon(interaction: discord.Interaction):
    guild = bot.get_guild(GUILD_ID)
    member = guild.get_member(interaction.user.id)

    if not member:
        await interaction.response.send_message(
            "⚠️ Impossible de récupérer vos rôles.",
            ephemeral=True
        )
        return

    role = discord.utils.get(member.roles, id=ROLE_AUTORISE_ID)
    if not role:
        await interaction.response.send_message(
            "⛔ Vous n’avez pas la permission d’utiliser cette commande.",
            ephemeral=True
        )
        await log_action(
            bot,
            f"⛔ **Accès refusé**\n👤 {interaction.user} ({interaction.user.id})"
        )
        return

    # Si autorisé, on envoie le modal
    await interaction.response.send_modal(BonModal())

# ======================
# EVENT ON_READY
# ======================
@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user}")
    await bot.tree.sync()
    await log_action(
        bot,
        f"🟢 **Bot démarré**\n🕒 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )

bot.run(os.getenv('DISCORD_TOKEN'))