from flask import Flask, request, jsonify, render_template_string, Response
from functools import wraps
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
ADMIN_USER = os.environ.get("ADMIN_USER", "")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "")

def get_conn():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL no está configurada en Render (Environment Variables).")
    return psycopg2.connect(DATABASE_URL, sslmode="require", connect_timeout=5)

def ensure_table():
    conn = get_conn()
    cur = conn.cursor()
    sql = (
        "CREATE TABLE IF NOT EXISTS installations ("
        "id TEXT PRIMARY KEY, "
        "name TEXT, "
        "desired_state TEXT DEFAULT 'ALLOW', "
        "last_seen TIMESTAMP"
        ");"
    )
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not ADMIN_USER or not ADMIN_PASS:
            return Response(
                "Panel bloqueado: configura ADMIN_USER y ADMIN_PASS en Render (Environment).",
                500
            )
        auth = request.authorization
        if not auth or auth.username != ADMIN_USER or auth.password != ADMIN_PASS:
            return Response(
                "Acceso restringido",
                401,
                {"WWW-Authenticate": 'Basic realm="Firesoft Licencias Panel"'}
            )
        return f(*args, **kwargs)
    return decorated

@app.route("/")
@require_auth
def index():
    ensure_table()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, desired_state, last_seen FROM installations ORDER BY last_seen DESC NULLS LAST")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    html = """
    <h1>Panel Licencias Firesoft</h1>
    <table border=1 cellpadding=6 cellspacing=0>
      <tr><th>ID</th><th>Equipo</th><th>Estado</th><th>Último contacto (UTC)</th><th>Acción</th></tr>
      {% for r in rows %}
      <tr>
        <td>{{r[0]}}</td>
        <td>{{r[1]}}</td>
        <td><b>{{r[2]}}</b></td>
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

@app.route("/set/<id>/<state>")
@require_auth
def set_state(id, state):
    ensure_table()
    state = state.upper()
    if state not in ("ALLOW", "DENY"):
        return "Estado inválido", 400

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE installations SET desired_state=%s WHERE id=%s", (state, id))
    conn.commit()
    cur.close()
    conn.close()
    return "OK ✅ <a href='/'>volver</a>"

@app.route("/api/checkin", methods=["POST"])
def checkin():
    ensure_table()
    data = request.get_json(force=True, silent=True) or {}
    installation_id = data.get("installationId")
    if not installation_id:
        return jsonify({"error": "installationId requerido"}), 400

    now = datetime.utcnow()

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO installations (id, name, desired_state, last_seen) "
        "VALUES (%s, %s, 'ALLOW', %s) "
        "ON CONFLICT (id) DO UPDATE SET last_seen=%s "
        "RETURNING desired_state",
        (installation_id, installation_id, now, now)
    )
    desired_state = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"desiredState": desired_state, "leaseDays": 7})

@app.route("/health")
def health():
    return "OK", 200
