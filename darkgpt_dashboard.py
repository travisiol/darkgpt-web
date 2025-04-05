from flask import Flask, render_template_string
import json
import os

# Fichiers de données
CREDITS_FILE = "darkgpt_credits.json"
PARRAINAGE_FILE = "darkgpt_parrainages.json"

app = Flask(__name__)

# --- Template HTML simplifié (tu pourras le styliser ensuite) ---
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>DarkGPT Dashboard</title>
    <style>
        body { font-family: Arial; background: #111; color: #eee; padding: 30px; }
        h1 { color: #c0392b; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #444; padding: 8px; text-align: left; }
        th { background: #222; }
        tr:nth-child(even) { background-color: #1e1e1e; }
    </style>
</head>
<body>
    <h1>🧠 DarkGPT Dashboard</h1>
    <p>Total utilisateurs : {{ total }}</p>
    <p>Utilisateurs premium : {{ premiums }}</p>
    <p>Utilisateurs gratuits : {{ gratuits }}</p>

    <table>
        <tr>
            <th>ID</th>
            <th>Premium</th>
            <th>Utilisations aujourd'hui</th>
            <th>Filleuls</th>
        </tr>
        {% for user_id, data in users.items() %}
        <tr>
            <td>{{ user_id }}</td>
            <td>{{ "✅" if data.premium else "❌" }}</td>
            <td>{{ data.daily_uses }}</td>
            <td>{{ parrainages.get(user_id, [])|length }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

# --- Fonctions sécurisées ---
def load_json_safe(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@app.route("/")
def dashboard():
    users = load_json_safe(CREDITS_FILE)
    parrainages = load_json_safe(PARRAINAGE_FILE)

    total = len(users)
    premiums = sum(1 for u in users.values() if u.get("premium"))
    gratuits = total - premiums

    return render_template_string(TEMPLATE,
        users=users,
        parrainages=parrainages,
        total=total,
        premiums=premiums,
        gratuits=gratuits
    )

if __name__ == "__main__":
    app.run(debug=True)
