from flask import Flask, render_template_string
import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone

app = Flask(__name__)

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("TOKEN")
GUILD_ID = "1496930544808886312"

ARQUIVO_PONTOS = "ponto.json"
ARQUIVO_REGISTROS = "registros.json"

# =========================
# FUNÇÕES
# =========================
def carregar_json(arquivo):
    try:
        if os.path.exists(arquivo):
            with open(arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        return {}

    return {}

def request_discord(url):
    if not TOKEN:
        print("❌ TOKEN não encontrado. Configure a variável TOKEN no PowerShell.")
        return None

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bot {TOKEN}",
            "User-Agent": "PM-BOT"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"❌ Erro HTTP Discord: {e.code}")
        return None
    except Exception as e:
        print(f"❌ Erro ao conectar no Discord: {e}")
        return None

def buscar_membros():
    url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members?limit=1000"
    return request_discord(url) or []

def nome(membro):
    user = membro.get("user", {})
    return membro.get("nick") or user.get("global_name") or user.get("username") or "Sem nome"

def dias_no_servidor(membro):
    try:
        data = membro["joined_at"].replace("Z", "+00:00")
        return (datetime.now(timezone.utc) - datetime.fromisoformat(data)).days
    except:
        return 0

def montar_ranking():
    pontos = carregar_json(ARQUIVO_PONTOS)
    registros = carregar_json(ARQUIVO_REGISTROS)
    membros = buscar_membros()

    lista = []

    for membro in membros:
        user = membro.get("user", {})
        uid = user.get("id")

        if not uid:
            continue

        p = pontos.get(uid, 0)

        if isinstance(p, dict):
            p = p.get("pontos", 0)

        r = registros.get(uid, {})
        acoes = r.get("acoes", 0)
        multas = r.get("multas", 0)
        prisoes = r.get("prisoes", 0)

        lista.append({
            "nome": nome(membro),
            "id": uid,
            "pontos": p,
            "acoes": acoes,
            "multas": multas,
            "prisoes": prisoes,
            "dias": dias_no_servidor(membro)
        })

    return sorted(lista, key=lambda x: x["pontos"], reverse=True)

# =========================
# ROTA WEB
# =========================
@app.route("/")
def home():
    ranking = montar_ranking()

    html = """
    <html>
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="30">
        <title>Painel PM</title>

        <style>
            body {
                background: #0f172a;
                color: white;
                font-family: Arial, sans-serif;
                padding: 20px;
            }

            h1 {
                text-align: center;
                color: #38bdf8;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 25px;
                background: #1e293b;
                border-radius: 10px;
                overflow: hidden;
            }

            th {
                background: #0284c7;
                padding: 12px;
                text-align: left;
            }

            td {
                padding: 12px;
                border-bottom: 1px solid #334155;
            }

            tr:hover {
                background: #334155;
            }

            .top1 {
                color: gold;
                font-weight: bold;
            }

            .top2 {
                color: silver;
                font-weight: bold;
            }

            .top3 {
                color: #cd7f32;
                font-weight: bold;
            }
        </style>
    </head>

    <body>
        <h1>🚓 PAINEL PM</h1>

        <table>
            <tr>
                <th>#</th>
                <th>Nome</th>
                <th>ID Discord</th>
                <th>Pontos</th>
                <th>Ações</th>
                <th>Multas</th>
                <th>Prisões</th>
                <th>Dias no servidor</th>
            </tr>

            {% for i in ranking %}
            <tr>
                <td class="{% if loop.index == 1 %}top1{% elif loop.index == 2 %}top2{% elif loop.index == 3 %}top3{% endif %}">
                    {{ loop.index }}º
                </td>
                <td>{{ i.nome }}</td>
                <td>{{ i.id }}</td>
                <td>{{ i.pontos }}</td>
                <td>{{ i.acoes }}</td>
                <td>{{ i.multas }}</td>
                <td>{{ i.prisoes }}</td>
                <td>{{ i.dias }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """

    return render_template_string(html, ranking=ranking)

# =========================
# START
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)