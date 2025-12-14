from flask import Flask, request, jsonify, render_template_string
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

@app.route("/")
def index():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, desired_state, last_seen FROM installations ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    html = """
    <h1>Panel Licencias Firesoft</h1>
    <table border=1 cellpadding=5>
      <tr><th>ID</th><th>Equipo</th><th>Estado</th><th>Último contacto</th><th>Acción</th></tr>
      {% for r in rows %}
      <tr>
        <td>{{r[0]}}</td>
        <td>{{r[1]}}</td>
        <td>{{r[2]}}</td>
        <td>{{r[3]}}</td>
        <td>
          <a href="/set/{{r[0]}}/ALLOW">ACTIVAR</a> |
          <a href="/set/{{r[0]}}/DENY">DESACTIVAR</a>
        </td>
      </tr>
      {% endfor %}
    </table>
    """
    return render_template_string(html, rows=rows)

@app.route("/api/checkin", methods=["POST"])
def checkin():
    data = request.json
    installation_id = data["installationId"]

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO installations (id, name, desired_state, last_seen)
        VALUES (%s, %s, 'ALLOW', %s)
        ON CONFLICT (id) DO UPDATE
        SET last_seen = %s
        RETURNING desired_state
    """, (installation_id, installation_id, datetime.utcnow(), datetime.utcnow()))

    state = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "desiredState": state,
        "leaseDays": 7
    })

@app.route("/set/<id>/<state>")
def set_state(id, state):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE installations SET desired_state=%s WHERE id=%s", (state, id))
    conn.commit()
    cur.close()
    conn.close()
    return "OK <a href='/'>volver</a>"
