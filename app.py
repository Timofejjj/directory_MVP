#!/usr/bin/env python3

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, render_template

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "db" / "dicts.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
SEED_PATH = BASE_DIR / "db" / "seed.sql"

OPERATION_LABELS = {
    "INSERT": "Создание",
    "UPDATE": "Изменение",
    "DELETE": "Удаление",
}

CATALOGS = {
    "departments": {
        "label": "Отделы IT-компании",
        "table": "departments",
        "history_table": "departments_history",
        "columns": [
            {"key": "name", "label": "Название отдела", "type": "text", "sort": "text"},
            {
                "key": "description",
                "label": "Описание",
                "type": "textarea",
                "sort": "text",
            },
            {
                "key": "founded_date",
                "label": "Дата создания",
                "type": "date",
                "sort": "date",
            },
            {
                "key": "headcount",
                "label": "Численность",
                "type": "integer",
                "sort": "number",
            },
            {
                "key": "annual_budget",
                "label": "Годовой бюджет",
                "type": "decimal",
                "sort": "number",
            },
        ],
    },
    "projects": {
        "label": "Проекты",
        "table": "projects",
        "history_table": "projects_history",
        "columns": [
            {
                "key": "department_id",
                "label": "Отдел",
                "type": "select",
                "ref": "departments",
                "sort": "text",
                "display_key": "department_label",
            },
            {"key": "title", "label": "Название проекта", "type": "text", "sort": "text"},
            {
                "key": "summary",
                "label": "Описание",
                "type": "textarea",
                "sort": "text",
            },
            {
                "key": "start_date",
                "label": "Дата начала",
                "type": "date",
                "sort": "date",
            },
            {
                "key": "planned_end_date",
                "label": "Плановая дата завершения",
                "type": "date",
                "sort": "date",
            },
            {
                "key": "priority",
                "label": "Приоритет (1–5)",
                "type": "integer",
                "sort": "number",
                "min": 1,
                "max": 5,
            },
            {
                "key": "project_budget",
                "label": "Бюджет проекта",
                "type": "decimal",
                "sort": "number",
            },
        ],
    },
}

app = Flask(__name__)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(c["name"] == column for c in cols)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def migrate_db(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "departments") and not _table_has_column(
        conn, "departments", "is_active"
    ):
        conn.execute(
            "ALTER TABLE departments ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
        )

    if _table_exists(conn, "projects") and not _table_has_column(
        conn, "projects", "is_active"
    ):
        conn.execute(
            "ALTER TABLE projects ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
        )

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS departments_history (
          history_id    INTEGER PRIMARY KEY AUTOINCREMENT,
          record_id     INTEGER NOT NULL,
          operation     TEXT    NOT NULL,
          changed_at    TEXT    NOT NULL,
          name          TEXT    NOT NULL,
          description   TEXT    NOT NULL,
          founded_date  TEXT    NOT NULL,
          headcount     INTEGER NOT NULL,
          annual_budget NUMERIC(12,2) NOT NULL,
          is_active     INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS projects_history (
          history_id       INTEGER PRIMARY KEY AUTOINCREMENT,
          record_id        INTEGER NOT NULL,
          operation        TEXT    NOT NULL,
          changed_at       TEXT    NOT NULL,
          department_id    INTEGER NOT NULL,
          title            TEXT    NOT NULL,
          summary          TEXT    NOT NULL,
          start_date       TEXT    NOT NULL,
          planned_end_date TEXT    NOT NULL,
          priority         INTEGER NOT NULL,
          project_budget   NUMERIC(12,2) NOT NULL,
          is_active        INTEGER NOT NULL
        );
        """
    )
    conn.commit()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    try:
        if not DB_PATH.exists() or not _table_exists(conn, "departments"):
            if DB_PATH.exists():
                DB_PATH.unlink()
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            conn.executescript(SEED_PATH.read_text(encoding="utf-8"))
            conn.commit()
        migrate_db(conn)
    finally:
        conn.close()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def department_option_label(row: sqlite3.Row) -> str:
    name = row["name"]
    desc = (row["description"] or "").strip()
    if desc:
        short = desc if len(desc) <= 60 else desc[:57] + "..."
        return f"{name} — {short}"
    return name


def fetch_department_options(conn: sqlite3.Connection, active_only: bool = True) -> list[dict]:
    where = "WHERE is_active = 1" if active_only else ""
    rows = conn.execute(
        f"SELECT id, name, description FROM departments {where} ORDER BY name, id"
    ).fetchall()
    return [
        {"id": row["id"], "label": department_option_label(row)} for row in rows
    ]


def fetch_department_labels(conn: sqlite3.Connection) -> dict[int, str]:
    rows = conn.execute(
        "SELECT id, name, description, is_active FROM departments ORDER BY id"
    ).fetchall()
    labels = {}
    for row in rows:
        label = department_option_label(row)
        if not row["is_active"]:
            label += " (архив)"
        labels[row["id"]] = label
    return labels


def next_id(conn: sqlite3.Connection, table: str) -> int:
    row = conn.execute(
        f"SELECT COALESCE(MAX(id), 0) + 1 AS nid FROM {table}"
    ).fetchone()
    return int(row["nid"])


def iso_to_display(iso: str | None) -> str:
    if not iso:
        return ""
    parts = iso.split("-")
    if len(parts) != 3:
        return iso
    y, m, d = parts
    return f"{d}.{m}.{y}"


def display_to_iso(display: str) -> str | None:
    display = (display or "").strip()
    if not display:
        return None
    if "-" in display and len(display) == 10:
        return display
    parts = display.split(".")
    if len(parts) != 3:
        return None
    d, m, y = parts
    if len(d) != 2 or len(m) != 2 or len(y) != 4:
        return None
    return f"{y}-{m}-{d}"


def row_to_api(row: sqlite3.Row, catalog_key: str, dept_labels: dict[int, str]) -> dict:
    data = dict(row)
    data.pop("is_active", None)
    if catalog_key == "projects":
        dept_id = data.get("department_id")
        data["department_label"] = dept_labels.get(dept_id, "—")
    for col in CATALOGS[catalog_key]["columns"]:
        if col.get("type") == "date":
            data[col["key"]] = iso_to_display(data.get(col["key"]))
    return data


def write_history(
    conn: sqlite3.Connection, catalog_key: str, row: sqlite3.Row, operation: str
) -> None:
    catalog = CATALOGS[catalog_key]
    hist = catalog["history_table"]
    ts = now_iso()
    record_id = row["id"]

    if catalog_key == "departments":
        conn.execute(
            f"""
            INSERT INTO {hist}
              (record_id, operation, changed_at, name, description,
               founded_date, headcount, annual_budget, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                operation,
                ts,
                row["name"],
                row["description"],
                row["founded_date"],
                row["headcount"],
                row["annual_budget"],
                row["is_active"],
            ),
        )
    else:
        conn.execute(
            f"""
            INSERT INTO {hist}
              (record_id, operation, changed_at, department_id, title, summary,
               start_date, planned_end_date, priority, project_budget, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                operation,
                ts,
                row["department_id"],
                row["title"],
                row["summary"],
                row["start_date"],
                row["planned_end_date"],
                row["priority"],
                row["project_budget"],
                row["is_active"],
            ),
        )


def department_reference_count(conn: sqlite3.Connection, dept_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM projects WHERE department_id = ?",
        (dept_id,),
    ).fetchone()
    return int(row["cnt"])


def fetch_active_row(
    conn: sqlite3.Connection, catalog_key: str, record_id: int
) -> sqlite3.Row | None:
    table = CATALOGS[catalog_key]["table"]
    return conn.execute(
        f"SELECT * FROM {table} WHERE id = ? AND is_active = 1", (record_id,)
    ).fetchone()


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/catalogs")
def list_catalogs():
    return jsonify(
        [{"key": k, "label": v["label"]} for k, v in CATALOGS.items()]
    )


@app.get("/api/catalogs/<catalog_key>/meta")
def catalog_meta(catalog_key: str):
    if catalog_key not in CATALOGS:
        return jsonify({"error": "Справочник не найден"}), 404
    meta = {
        "key": catalog_key,
        "label": CATALOGS[catalog_key]["label"],
        "columns": CATALOGS[catalog_key]["columns"],
    }
    if catalog_key == "projects":
        with get_db() as conn:
            meta["selectOptions"] = {
                "department_id": fetch_department_options(conn, active_only=True),
            }
    return jsonify(meta)


@app.get("/api/catalogs/<catalog_key>/records")
def list_records(catalog_key: str):
    if catalog_key not in CATALOGS:
        return jsonify({"error": "Справочник не найден"}), 404

    table = CATALOGS[catalog_key]["table"]
    with get_db() as conn:
        dept_options = fetch_department_options(conn, active_only=True)
        dept_labels = fetch_department_labels(conn)

        if catalog_key == "projects":
            sql = """
                SELECT p.*
                FROM projects p
                WHERE p.is_active = 1
                ORDER BY p.id
            """
            rows = conn.execute(sql).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE is_active = 1 ORDER BY id"
            ).fetchall()

        records = [row_to_api(r, catalog_key, dept_labels) for r in rows]

    return jsonify(
        {
            "columns": CATALOGS[catalog_key]["columns"],
            "records": records,
            "selectOptions": (
                {"department_id": dept_options} if catalog_key == "projects" else {}
            ),
        }
    )


@app.get("/api/select-options/departments")
def department_select_options():
    with get_db() as conn:
        return jsonify(fetch_department_options(conn, active_only=True))


def validate_record(
    catalog_key: str, payload: dict, is_update: bool
) -> tuple[dict | None, str | None]:
    catalog = CATALOGS[catalog_key]
    cleaned: dict = {}

    for col in catalog["columns"]:
        key = col["key"]
        raw = payload.get(key)
        ctype = col["type"]

        if ctype == "select":
            if raw is None or raw == "":
                return None, f"Поле «{col['label']}» обязательно"
            try:
                cleaned[key] = int(raw)
            except (TypeError, ValueError):
                return None, f"Некорректное значение в «{col['label']}»"
            if catalog_key == "projects":
                with get_db() as conn:
                    dept = conn.execute(
                        "SELECT 1 FROM departments WHERE id = ? AND is_active = 1",
                        (cleaned[key],),
                    ).fetchone()
                    if not dept:
                        return None, "Выбранный отдел недоступен (снят с учёта)"
            continue

        if ctype == "text":
            val = (raw or "").strip()
            if not val:
                return None, f"Поле «{col['label']}» обязательно"
            cleaned[key] = val
            continue

        if ctype == "textarea":
            cleaned[key] = (raw or "").strip()
            continue

        if ctype == "date":
            iso = display_to_iso(str(raw or ""))
            if not iso:
                return None, f"Укажите корректную дату в «{col['label']}» (ДД.ММ.ГГГГ)"
            cleaned[key] = iso
            continue

        if ctype == "integer":
            if raw is None or raw == "":
                return None, f"Поле «{col['label']}» обязательно"
            try:
                val = int(raw)
            except (TypeError, ValueError):
                return None, f"«{col['label']}» должно быть целым числом"
            min_v = col.get("min")
            max_v = col.get("max")
            if min_v is not None and val < min_v:
                return None, f"«{col['label']}»: минимум {min_v}"
            if max_v is not None and val > max_v:
                return None, f"«{col['label']}»: максимум {max_v}"
            cleaned[key] = val
            continue

        if ctype == "decimal":
            if raw is None or raw == "":
                return None, f"Поле «{col['label']}» обязательно"
            try:
                val = float(str(raw).replace(",", "."))
            except ValueError:
                return None, f"«{col['label']}» должно быть числом"
            if val < 0:
                return None, f"«{col['label']}» не может быть отрицательным"
            cleaned[key] = round(val, 2)
            continue

    return cleaned, None


@app.post("/api/catalogs/<catalog_key>/records")
def create_record(catalog_key: str):
    if catalog_key not in CATALOGS:
        return jsonify({"error": "Справочник не найден"}), 404

    cleaned, err = validate_record(
        catalog_key, request.get_json(silent=True) or {}, False
    )
    if err:
        return jsonify({"error": err}), 400

    table = CATALOGS[catalog_key]["table"]
    with get_db() as conn:
        new_id = next_id(conn, table)
        cols = list(cleaned.keys())
        placeholders = ", ".join("?" * len(cols))
        col_names = ", ".join(cols)
        values = [cleaned[c] for c in cols]
        conn.execute(
            f"INSERT INTO {table} (id, {col_names}, is_active) VALUES (?, {placeholders}, 1)",
            [new_id, *values],
        )
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (new_id,)).fetchone()
        write_history(conn, catalog_key, row, "INSERT")
        conn.commit()

    return jsonify({"ok": True})


@app.put("/api/catalogs/<catalog_key>/records/<int:record_id>")
def update_record(catalog_key: str, record_id: int):
    if catalog_key not in CATALOGS:
        return jsonify({"error": "Справочник не найден"}), 404

    cleaned, err = validate_record(
        catalog_key, request.get_json(silent=True) or {}, True
    )
    if err:
        return jsonify({"error": err}), 400

    table = CATALOGS[catalog_key]["table"]
    with get_db() as conn:
        old = fetch_active_row(conn, catalog_key, record_id)
        if not old:
            return jsonify({"error": "Запись не найдена"}), 404

        write_history(conn, catalog_key, old, "UPDATE")

        if catalog_key == "departments" and department_reference_count(
            conn, record_id
        ) > 0:
            conn.execute(
                "UPDATE departments SET is_active = 0 WHERE id = ?", (record_id,)
            )
            new_id = next_id(conn, table)
            cols = list(cleaned.keys())
            placeholders = ", ".join("?" * len(cols))
            col_names = ", ".join(cols)
            values = [cleaned[c] for c in cols]
            conn.execute(
                f"INSERT INTO {table} (id, {col_names}, is_active) VALUES (?, {placeholders}, 1)",
                [new_id, *values],
            )
        else:
            sets = ", ".join(f"{k} = ?" for k in cleaned)
            values = [cleaned[k] for k in cleaned]
            conn.execute(
                f"UPDATE {table} SET {sets} WHERE id = ?",
                [*values, record_id],
            )

        conn.commit()

    return jsonify({"ok": True})


@app.delete("/api/catalogs/<catalog_key>/records/<int:record_id>")
def delete_record(catalog_key: str, record_id: int):
    if catalog_key not in CATALOGS:
        return jsonify({"error": "Справочник не найден"}), 404

    table = CATALOGS[catalog_key]["table"]
    with get_db() as conn:
        row = fetch_active_row(conn, catalog_key, record_id)
        if not row:
            return jsonify({"error": "Запись не найдена"}), 404

        write_history(conn, catalog_key, row, "DELETE")
        conn.execute(
            f"UPDATE {table} SET is_active = 0 WHERE id = ?", (record_id,)
        )
        conn.commit()

    return jsonify({"ok": True})


@app.get("/api/catalogs/<catalog_key>/records/<int:record_id>")
def get_record(catalog_key: str, record_id: int):
    if catalog_key not in CATALOGS:
        return jsonify({"error": "Справочник не найден"}), 404

    with get_db() as conn:
        dept_labels = fetch_department_labels(conn)
        row = fetch_active_row(conn, catalog_key, record_id)
        if not row:
            return jsonify({"error": "Запись не найдена"}), 404
        data = row_to_api(row, catalog_key, dept_labels)
        if catalog_key == "projects":
            data["department_id"] = row["department_id"]

    return jsonify(data)


@app.get("/api/catalogs/<catalog_key>/records/<int:record_id>/history")
def record_history(catalog_key: str, record_id: int):
    if catalog_key not in CATALOGS:
        return jsonify({"error": "Справочник не найден"}), 404

    hist_table = CATALOGS[catalog_key]["history_table"]
    with get_db() as conn:
        dept_labels = fetch_department_labels(conn)
        rows = conn.execute(
            f"""
            SELECT * FROM {hist_table}
            WHERE record_id = ?
            ORDER BY changed_at DESC, history_id DESC
            """,
            (record_id,),
        ).fetchall()

        entries = []
        for row in rows:
            item = {
                "changed_at": row["changed_at"],
                "operation": row["operation"],
                "operation_label": OPERATION_LABELS.get(row["operation"], row["operation"]),
            }
            for col in CATALOGS[catalog_key]["columns"]:
                key = col["key"]
                if catalog_key == "projects" and key == "department_id":
                    item["department_label"] = dept_labels.get(
                        row["department_id"], "—"
                    )
                elif col.get("type") == "date":
                    item[key] = iso_to_display(row[key])
                else:
                    item[key] = row[key]
            entries.append(item)

    return jsonify({"entries": entries})


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
