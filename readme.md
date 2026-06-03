# 🗄️ DB Visualizer

A sleek web-based database viewer for SQLite files. Browse tables, search rows, sort columns, run SQL queries, and export to CSV — all from your browser.

## Features

- **📊 Data View** — Browse table rows with pagination, search, and column sorting
- **🏗 Schema View** — See all tables with column types, primary keys, and constraints
- **⚡ SQL Editor** — Run custom SELECT queries with Ctrl+Enter
- **⬇ CSV Export** — Export any table to CSV in one click
- **🖱 Drag & Drop** — Drop a `.db` file anywhere on the screen to open it

## Supported Formats

| Extension  | Format           |
| ---------- | ---------------- |
| `.db`      | SQLite Database  |
| `.sqlite`  | SQLite Database  |
| `.sqlite3` | SQLite3 Database |
| `.s3db`    | SQLite3 Database |
| `.sl3`     | SQLite Database  |

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. (Optional) Generate a sample database to try

```bash
python create_sample_db.py
```

### 3. Run the app

```bash
python app.py
```

### 4. Open your browser

Visit: **http://localhost:5000**

Then drag-and-drop a `.db` file, or click **Open Database** in the sidebar.

## Usage Tips

- **Search**: Type in the search box to filter rows across all columns
- **Sort**: Click any column header to sort ascending/descending
- **SQL Query**: Use the SQL tab for custom queries (SELECT only, max 500 rows returned)
- **Keyboard shortcut**: `Ctrl+Enter` (or `Cmd+Enter`) to run SQL queries

## Project Structure

```
db-visualizer/
├── app.py                 # Flask backend
├── create_sample_db.py    # Generate a test database
├── requirements.txt       # Python dependencies
├── uploads/               # Uploaded DB files (auto-created)
└── templates/
    └── index.html         # Full frontend UI
```
