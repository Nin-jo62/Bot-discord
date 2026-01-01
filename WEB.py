from flask import Flask, render_template_string, abort
import sqlite3

app = Flask(__name__)
DB = "bons.db"

HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Bon d'achat</title>
<style>
body {
    background: #0f172a;
    color: white;
    font-family: Arial;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
}
.card {
    background: linear-gradient(135deg, #1e3a8a, #020617);
    border-radius: 16px;
    padding: 30px;
    width: 420px;
    box-shadow: 0 0 30px black;
}
.value {
    font-size: 48px;
    color: gold;
    text-align: right;
}
.status {
    margin-top: 10px;
    font-weight: bold;
}
.ok { color: #22c55e; }
.wait { color: #eab308; }
.used { color: #ef4444; }
</style>
</head>
<body>
<div class="card">
    <h2>🎟️ Bon d'achat</h2>
    <p><b>Numéro :</b> {{numero}}</p>
    <p><b>Client :</b> {{prenom}} {{nom}}</p>
    <div class="value">{{valeur}}€</div>
    <p><b>Date :</b> {{date}}</p>
    <p class="status {{css}}">Statut : {{statut}}</p>
</div>
</body>
</html>
"""

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

    if not row:
        abort(404)

    prenom, nom, valeur, date, statut = row

    css = {
        "EN_ATTENTE": "wait",
        "UTILISÉ": "used",
        "VALIDÉ": "ok"
    }.get(statut, "wait")

    return render_template_string(
        HTML,
        numero=numero,
        prenom=prenom,
        nom=nom,
        valeur=valeur,
        date=date,
        statut=statut,
        css=css
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
