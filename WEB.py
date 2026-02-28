from flask import Flask, request, redirect, abort, send_from_directory, render_template_string
import sqlite3

# ======================
# CONFIG
# ======================
DB = "bons.db"

app = Flask(__name__, static_folder="site", static_url_path="")

# ======================
# PAGE ACCUEIL (FORMULAIRE)
# ======================
@app.route("/")
def home():
    return send_from_directory("site", "index.html")

# ======================
# VERIFICATION DU BON
# ======================
@app.route("/verify", methods=["POST"])
def verify():
    numero = request.form.get("numero")

    if not numero:
        abort(400)

    db = sqlite3.connect(DB)
    cursor = db.cursor()

    cursor.execute(
        "SELECT 1 FROM bons WHERE numero = ?",
        (numero.strip(),)
    )
    exists = cursor.fetchone()
    db.close()

    if not exists:
        return """
        <h2 style="color:red;text-align:center;margin-top:50px;">
            ❌ Bon introuvable
        </h2>
        <p style="text-align:center;">
            <a href="/">Retour</a>
        </p>
        """, 404

    return redirect(f"/bon/{numero.strip()}")

# ======================
# AFFICHAGE DU BON
# ======================
@app.route("/bon/<numero>")
def bon(numero):
    db = sqlite3.connect(DB)
    cursor = db.cursor()

    cursor.execute("""
        SELECT prenom, nom, valeur, date, statut
        FROM bons
        WHERE numero = ?
    """, (numero,))
    row = cursor.fetchone()
    db.close()

    if not row:
        abort(404)

    prenom, nom, valeur, date, statut = row

    css = {
        "EN_ATTENTE": "wait",
        "UTILISÉ": "used",
        "VALIDÉ": "valid"
    }.get(statut, "wait")

    HTML = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Legendary Motorsport – Bon</title>

    <style>
    body {
        margin: 0;
        min-height: 100vh;
        background: radial-gradient(circle at top, #1a0000, #000 70%);
        font-family: Arial, sans-serif;
        display: flex;
        justify-content: center;
        align-items: center;
        color: white;
    }

    .card {
        width: 100%;
        max-width: 420px;
        background: linear-gradient(145deg, #0a0a0a, #000);
        border-radius: 20px;
        padding: 25px;
        border: 1px solid rgba(255, 100, 0, 0.4);
        box-shadow: 0 0 25px rgba(255, 80, 0, 0.6);
        text-align: center;
    }

    h1 {
        color: #ffae00;
        margin-bottom: 0;
        letter-spacing: 2px;
    }

    h2 {
        margin-top: 5px;
        color: #ff3b00;
        font-size: 14px;
    }

    .value {
        font-size: 52px;
        color: #ffcc00;
        margin: 20px 0;
        font-weight: bold;
    }

    .info {
        font-size: 14px;
        margin: 6px 0;
    }

    .info span {
        color: #ff6a00;
    }

    .status {
        margin-top: 18px;
        padding: 12px;
        border-radius: 10px;
        font-weight: bold;
    }

    .wait {
        background: rgba(255, 180, 0, 0.15);
        color: #ffcc00;
    }

    .used {
        background: rgba(255, 0, 0, 0.2);
        color: #ff4d4d;
    }

    .valid {
        background: rgba(0, 255, 100, 0.15);
        color: #00ff9d;
    }

    .footer {
        margin-top: 15px;
        font-size: 11px;
        opacity: 0.6;
    }
    </style>
    </head>

    <body>
        <div class="card">
            <h1>LEGENDARY</h1>
            <h2>MOTORSPORT</h2>

            <div class="value">{{valeur}}€</div>

            <div class="info"><span>Client :</span> {{prenom}} {{nom}}</div>
            <div class="info"><span>Bon n° :</span> {{numero}}</div>
            <div class="info"><span>Date :</span> {{date}}</div>

            <div class="status {{css}}">
                {{statut}}
            </div>

            <div class="footer">
                Bon valable uniquement chez Legendary Motorsport
            </div>
        </div>
    </body>
    </html>
    """

    return render_template_string(
        HTML,
        prenom=prenom,
        nom=nom,
        valeur=valeur,
        date=date,
        statut=statut,
        numero=numero,
        css=css
    )

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
