from flask import Flask, request, jsonify, render_template_string, Response
from functools import wraps
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)

# ---- Render Environment Vars ----
DATABASE_URL = os.environ.get("DATABASE_URL", "")
ADMIN_USER = os.environ.get("ADMIN_USER", "")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "")

# ---- DB helpers ----
def get_conn():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL no está configurada en Render (Environment Variables).")

    # connect_timeout evita que el arranque se quede colgado si hay problemas
    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require",
        connect_timeout=5
    )

def ensure_table():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS installations (
          id TEXT PRIMARY KEY,
          name TEXT,
          desired_state TEXT DEFAULT 'ALLOW',
          last_seen TIMEST_
