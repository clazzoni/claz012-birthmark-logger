import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app import config
from app.map_regions import MAP_REGIONS, is_valid_region
from app.models import Capture, Mark, MarkCreate, MarkPlacement, MarkUpdate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _format_dt(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def init_db() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS marks (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                body_region TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS captures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mark_id TEXT NOT NULL REFERENCES marks(id) ON DELETE CASCADE,
                captured_at TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_hash TEXT,
                imported_at TEXT NOT NULL,
                original_filename TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_captures_mark_id
                ON captures(mark_id);
            CREATE INDEX IF NOT EXISTS idx_captures_captured_at
                ON captures(captured_at);
            CREATE INDEX IF NOT EXISTS idx_captures_file_hash
                ON captures(file_hash);
            """
        )
        _migrate_marks(conn)


def _migrate_marks(conn: sqlite3.Connection) -> None:
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(marks)").fetchall()
    }
    if "map_region" not in columns:
        conn.execute("ALTER TABLE marks ADD COLUMN map_region TEXT")
    if "map_x" not in columns:
        conn.execute("ALTER TABLE marks ADD COLUMN map_x REAL")
    if "map_y" not in columns:
        conn.execute("ALTER TABLE marks ADD COLUMN map_y REAL")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_marks_map_region
            ON marks(map_region)
        """
    )


@contextmanager
def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _next_mark_id(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT id FROM marks WHERE id LIKE 'BM-%' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return "BM-001"
    num = int(row["id"].split("-")[1])
    return f"BM-{num + 1:03d}"


def _row_to_mark(row: sqlite3.Row) -> Mark:
    keys = row.keys()
    return Mark(
        id=row["id"],
        label=row["label"],
        body_region=row["body_region"],
        notes=row["notes"],
        created_at=_parse_dt(row["created_at"]),
        capture_count=row["capture_count"] or 0,
        last_capture_at=(
            _parse_dt(row["last_capture_at"]) if row["last_capture_at"] else None
        ),
        map_region=row["map_region"] if "map_region" in keys else None,
        map_x=row["map_x"] if "map_x" in keys else None,
        map_y=row["map_y"] if "map_y" in keys else None,
    )


def _row_to_capture(row: sqlite3.Row) -> Capture:
    return Capture(
        id=row["id"],
        mark_id=row["mark_id"],
        captured_at=_parse_dt(row["captured_at"]),
        file_path=row["file_path"],
        file_hash=row["file_hash"],
        imported_at=_parse_dt(row["imported_at"]),
        original_filename=row["original_filename"],
    )


def list_marks(
    search: str | None = None,
    unplaced_only: bool = False,
) -> list[Mark]:
    query = """
        SELECT m.*,
               COUNT(c.id) AS capture_count,
               MAX(c.captured_at) AS last_capture_at
        FROM marks m
        LEFT JOIN captures c ON c.mark_id = m.id
    """
    params: list[str | int] = []
    conditions: list[str] = []
    if search:
        conditions.append(
            "(m.label LIKE ? OR m.id LIKE ? OR m.body_region LIKE ?)"
        )
        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern])
    if unplaced_only:
        conditions.append(
            "(m.map_region IS NULL OR m.map_x IS NULL OR m.map_y IS NULL)"
        )
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " GROUP BY m.id ORDER BY m.id"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_mark(row) for row in rows]


def get_mark(mark_id: str) -> Mark | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT m.*,
                   COUNT(c.id) AS capture_count,
                   MAX(c.captured_at) AS last_capture_at
            FROM marks m
            LEFT JOIN captures c ON c.mark_id = m.id
            WHERE m.id = ?
            GROUP BY m.id
            """,
            (mark_id,),
        ).fetchone()
    return _row_to_mark(row) if row else None


def create_mark(data: MarkCreate) -> Mark:
    now = _utcnow()
    with get_connection() as conn:
        mark_id = _next_mark_id(conn)
        conn.execute(
            """
            INSERT INTO marks (id, label, body_region, notes, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (mark_id, data.label, data.body_region, data.notes, _format_dt(now)),
        )
    mark = get_mark(mark_id)
    assert mark is not None
    return mark


def update_mark(mark_id: str, data: MarkUpdate) -> Mark | None:
    with get_connection() as conn:
        result = conn.execute(
            """
            UPDATE marks
            SET label = ?, body_region = ?, notes = ?
            WHERE id = ?
            """,
            (data.label, data.body_region, data.notes, mark_id),
        )
        if result.rowcount == 0:
            return None
    return get_mark(mark_id)


def list_marks_by_region(region: str) -> list[Mark]:
    if not is_valid_region(region):
        return []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT m.*,
                   COUNT(c.id) AS capture_count,
                   MAX(c.captured_at) AS last_capture_at
            FROM marks m
            LEFT JOIN captures c ON c.mark_id = m.id
            WHERE m.map_region = ?
              AND m.map_x IS NOT NULL
              AND m.map_y IS NOT NULL
            GROUP BY m.id
            ORDER BY m.label
            """,
            (region,),
        ).fetchall()
    return [_row_to_mark(row) for row in rows]


def count_marks_by_region() -> dict[str, int]:
    counts = {region: 0 for region in MAP_REGIONS}
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT map_region, COUNT(*) AS count
            FROM marks
            WHERE map_region IS NOT NULL
              AND map_x IS NOT NULL
              AND map_y IS NOT NULL
            GROUP BY map_region
            """
        ).fetchall()
    for row in rows:
        if row["map_region"] in counts:
            counts[row["map_region"]] = row["count"]
    return counts


def update_mark_placement(mark_id: str, placement: MarkPlacement) -> Mark | None:
    if not is_valid_region(placement.map_region):
        return None
    with get_connection() as conn:
        result = conn.execute(
            """
            UPDATE marks
            SET map_region = ?, map_x = ?, map_y = ?
            WHERE id = ?
            """,
            (
                placement.map_region,
                placement.map_x,
                placement.map_y,
                mark_id,
            ),
        )
        if result.rowcount == 0:
            return None
    return get_mark(mark_id)


def clear_mark_placement(mark_id: str) -> Mark | None:
    with get_connection() as conn:
        result = conn.execute(
            """
            UPDATE marks
            SET map_region = NULL, map_x = NULL, map_y = NULL
            WHERE id = ?
            """,
            (mark_id,),
        )
        if result.rowcount == 0:
            return None
    return get_mark(mark_id)


def delete_mark(mark_id: str) -> bool:
    with get_connection() as conn:
        result = conn.execute("DELETE FROM marks WHERE id = ?", (mark_id,))
        return result.rowcount > 0


def list_captures(mark_id: str) -> list[Capture]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM captures
            WHERE mark_id = ?
            ORDER BY captured_at ASC, id ASC
            """,
            (mark_id,),
        ).fetchall()
    return [_row_to_capture(row) for row in rows]


def get_capture(capture_id: int) -> Capture | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM captures WHERE id = ?",
            (capture_id,),
        ).fetchone()
    return _row_to_capture(row) if row else None


def delete_capture(capture_id: int) -> Capture | None:
    capture = get_capture(capture_id)
    if capture is None:
        return None
    with get_connection() as conn:
        conn.execute("DELETE FROM captures WHERE id = ?", (capture_id,))
    return capture


def capture_hash_exists(mark_id: str, file_hash: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM captures
            WHERE mark_id = ? AND file_hash = ?
            LIMIT 1
            """,
            (mark_id, file_hash),
        ).fetchone()
    return row is not None


def insert_capture(
    mark_id: str,
    captured_at: datetime,
    file_path: str,
    file_hash: str,
    original_filename: str,
) -> Capture:
    now = _utcnow()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO captures
                (mark_id, captured_at, file_path, file_hash, imported_at, original_filename)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                mark_id,
                _format_dt(captured_at),
                file_path,
                file_hash,
                _format_dt(now),
                original_filename,
            ),
        )
        capture_id = cursor.lastrowid
    capture = get_capture(capture_id)
    assert capture is not None
    return capture
