import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from werkzeug.security import check_password_hash, generate_password_hash


class Database:
    def __init__(self, path: str = "data/records.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    certificate_id TEXT UNIQUE NOT NULL,
                    student_name TEXT NOT NULL,
                    srn TEXT NOT NULL,
                    course TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    marks INTEGER NOT NULL,
                    original_marks INTEGER NOT NULL,
                    block_index INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    certificate_id TEXT NOT NULL,
                    previous_marks INTEGER NOT NULL,
                    new_marks INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    block_index INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(records)").fetchall()}
            if "original_marks" not in columns:
                conn.execute("ALTER TABLE records ADD COLUMN original_marks INTEGER")
                conn.execute("UPDATE records SET original_marks = marks WHERE original_marks IS NULL")

            row = conn.execute(
                "SELECT password FROM admins WHERE username = ?", ("admin",)
            ).fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO admins(username, password) VALUES (?, ?)",
                    ("admin", generate_password_hash("admin123")),
                )
            elif not row[0].startswith(("scrypt:", "pbkdf2:")):
                conn.execute(
                    "UPDATE admins SET password = ? WHERE username = ?",
                    (generate_password_hash(row[0]), "admin"),
                )

    def authenticate(self, username: str, password: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT password FROM admins WHERE username = ?", (username,)
            ).fetchone()
            return bool(row and check_password_hash(row[0], password))

    def add_record(self, record: Dict[str, Any]) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """INSERT INTO records
                (certificate_id, student_name, srn, course, subject, marks, original_marks, block_index, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record["certificate_id"],
                    record["student_name"],
                    record["srn"],
                    record["course"],
                    record["subject"],
                    record["marks"],
                    record.get("original_marks", record["marks"]),
                    record["block_index"],
                    record["created_at"],
                ),
            )
            return cursor.lastrowid

    def get_record(self, certificate_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM records WHERE certificate_id = ?", (certificate_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_records(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM records ORDER BY id DESC").fetchall()
            return [dict(row) for row in rows]

    def update_marks(self, certificate_id: str, marks: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE records SET marks = ? WHERE certificate_id = ?",
                (marks, certificate_id),
            )

    def add_correction(self, correction: Dict[str, Any]) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """INSERT INTO corrections
                (certificate_id, previous_marks, new_marks, reason, block_index, created_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    correction["certificate_id"],
                    correction["previous_marks"],
                    correction["new_marks"],
                    correction["reason"],
                    correction["block_index"],
                    correction["created_at"],
                ),
            )
            return cursor.lastrowid

    def list_corrections(self, certificate_id: str) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM corrections WHERE certificate_id = ? ORDER BY id ASC",
                (certificate_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_all_corrections(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM corrections ORDER BY id ASC").fetchall()
            return [dict(row) for row in rows]
