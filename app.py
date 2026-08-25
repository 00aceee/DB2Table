import os
import sqlite3
import json
import csv
import io
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "db-visualizer-secret-2024"
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {".db", ".sqlite", ".sqlite3", ".s3db", ".sl3"}


def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def get_db_info(db_path):
    """Extract all tables, columns, and row counts from a SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    db_info = {"tables": {}}

    for table in tables:
        # Get column info
        cursor.execute(f'PRAGMA table_info("{table}")')
        columns = []
        for col in cursor.fetchall():
            columns.append({
                "cid": col[0],
                "name": col[1],
                "type": col[2] or "TEXT",
                "notnull": bool(col[3]),
                "default": col[4],
                "pk": bool(col[5]),
            })

        # Get row count
        cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
        row_count = cursor.fetchone()[0]

        # Get foreign keys
        cursor.execute(f'PRAGMA foreign_key_list("{table}")')
        fk_rows = cursor.fetchall()
        foreign_keys = []
        for fk in fk_rows:
            foreign_keys.append({
                "from": fk[3],
                "to_table": fk[2],
                "to_col": fk[4],
            })

        db_info["tables"][table] = {
            "columns": columns,
            "row_count": row_count,
            "foreign_keys": foreign_keys,
        }

    # Get DB file size
    db_info["file_size"] = os.path.getsize(db_path)
    db_info["table_count"] = len(tables)
    conn.close()
    return db_info


def get_table_data(db_path, table, page=1, page_size=50, search="", sort_col=None, sort_dir="asc"):
    """Fetch paginated rows from a table."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get columns
    cursor.execute(f'PRAGMA table_info("{table}")')
    columns = [col[1] for col in cursor.fetchall()]

    offset = (page - 1) * page_size

    # Build search WHERE clause
    where = ""
    params = []
    if search:
        conditions = [f'CAST("{col}" AS TEXT) LIKE ?' for col in columns]
        where = "WHERE " + " OR ".join(conditions)
        params = [f"%{search}%"] * len(columns)

    # Count total
    cursor.execute(f'SELECT COUNT(*) FROM "{table}" {where}', params)
    total = cursor.fetchone()[0]

    # Sort
    order = ""
    if sort_col and sort_col in columns:
        direction = "DESC" if sort_dir == "desc" else "ASC"
        order = f'ORDER BY "{sort_col}" {direction}'

    # Fetch rows
    cursor.execute(
        f'SELECT * FROM "{table}" {where} {order} LIMIT ? OFFSET ?',
        params + [page_size, offset],
    )
    rows = cursor.fetchall()
    data = [dict(row) for row in rows]

    conn.close()
    return {
        "columns": columns,
        "rows": data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


def run_custom_query(db_path, sql):
    """Run a read-only SQL query."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        # Safety: only allow SELECT statements
        stripped = sql.strip().upper()
        if not stripped.startswith("SELECT") and not stripped.startswith("PRAGMA"):
            return {"error": "Only SELECT and PRAGMA queries are allowed."}

        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchmany(500)  # limit results
        if rows:
            columns = list(rows[0].keys())
            data = [dict(row) for row in rows]
        else:
            columns = []
            data = []
        return {"columns": columns, "rows": data, "count": len(data)}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(f.filename):
        return jsonify({"error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    filename = secure_filename(f.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    f.save(path)

    try:
        info = get_db_info(path)
        info["filename"] = filename
        info["path"] = path
        return jsonify({"success": True, "db": info})
    except Exception as e:
        return jsonify({"error": f"Failed to read database: {str(e)}"}), 400


@app.route("/table-data", methods=["POST"])
def table_data():
    data = request.json
    db_path = data.get("path")
    table = data.get("table")
    page = int(data.get("page", 1))
    page_size = int(data.get("page_size", 50))
    search = data.get("search", "")
    sort_col = data.get("sort_col")
    sort_dir = data.get("sort_dir", "asc")

    if not db_path or not os.path.exists(db_path):
        return jsonify({"error": "Database file not found"}), 404

    try:
        result = get_table_data(db_path, table, page, page_size, search, sort_col, sort_dir)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/query", methods=["POST"])
def query():
    data = request.json
    db_path = data.get("path")
    sql = data.get("sql", "")

    if not db_path or not os.path.exists(db_path):
        return jsonify({"error": "Database file not found"}), 404

    result = run_custom_query(db_path, sql)
    return jsonify(result)


@app.route("/export-csv", methods=["POST"])
def export_csv():
    data = request.json
    db_path = data.get("path")
    table = data.get("table")

    if not db_path or not os.path.exists(db_path):
        return jsonify({"error": "Database not found"}), 404

    result = get_table_data(db_path, table, page=1, page_size=100000)
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=result["columns"])
    writer.writeheader()
    writer.writerows(result["rows"])
    
    return jsonify({"csv": output.getvalue(), "filename": f"{table}.csv"})


if __name__ == "__main__":
    print("🗄️  DB Visualizer running at http://localhost:5000")
    app.run(debug=True, port=5000)