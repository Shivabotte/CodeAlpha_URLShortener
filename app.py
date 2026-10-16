
from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
import string
import random

app = Flask(__name__)


def get_db_connection():
    conn = sqlite3.connect("urls.db")
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))


@app.route("/")
def home():
    return    render_template("index.html")


@app.route("/shorten", methods=["POST"])
def shorten_url():
    data = request.get_json(silent=True) or {}
    original_url = data.get("url", "").strip()

    if not original_url.startswith(("http://", "https://")):
        return jsonify({"error": "Please provide a valid HTTP or HTTPS URL"}), 400

    conn = get_db_connection()

    while True:
        short_code = generate_short_code()
        try:
            conn.execute(
                "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
                (short_code, original_url)
            )
            conn.commit()
            break
        except sqlite3.IntegrityError:
            continue

    conn.close()

    short_url = request.host_url + short_code
    return jsonify({
        "original_url": original_url,
        "short_url": short_url,
        "short_code": short_code
    }), 201


@app.route("/history", methods=["GET"])
def url_history():
    conn = get_db_connection()

    urls = conn.execute("""
        SELECT short_code, original_url
        FROM urls
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    history = []

    for url in urls:
        history.append({
            "original_url": url["original_url"],
            "short_url": request.host_url + url["short_code"],
            "short_code": url["short_code"]
        })

    return jsonify(history)

@app.route("/delete/<short_code>", methods=["DELETE"])
def delete_url(short_code):
    conn = get_db_connection()

    cursor = conn.execute(
        "DELETE FROM urls WHERE short_code = ?",
        (short_code,)
    )

    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        return jsonify({"error": "Short URL not found"}), 404

    return jsonify({
        "message": "URL deleted successfully",
        "short_code": short_code
    }), 200

@app.route("/<short_code>")
def redirect_url(short_code):
    conn = get_db_connection()
    url_data = conn.execute(
        "SELECT original_url FROM urls WHERE short_code = ?",
        (short_code,)
    ).fetchone()
    conn.close()

    if url_data is None:
        return jsonify({"error": "Short URL not found"}), 404

    return redirect(url_data["original_url"])


if __name__ == "__main__":
    create_table()
    app.run(debug=True)