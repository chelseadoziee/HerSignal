"""
Lightweight SQLite schema updates for existing HerSignal databases.

SQLAlchemy create_all() does not add new columns to existing tables; run these
after model changes when you need backward-compatible upgrades.
"""

from sqlalchemy import text


def ensure_insight_snapshot_test_type(db):
    """
    Add insight_snapshots.test_type if missing (baseline | retake).

    Safe to call on every app startup. No-op when the column already exists.
    """
    engine = db.engine
    dialect = engine.dialect.name
    if dialect != "sqlite":
        # Postgres/MySQL: prefer Alembic in larger deployments
        return

    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(insight_snapshots)")).fetchall()
        col_names = {r[1] for r in rows}
        if "test_type" in col_names:
            return
        conn.execute(
            text(
                "ALTER TABLE insight_snapshots ADD COLUMN test_type "
                "VARCHAR(16) NOT NULL DEFAULT 'baseline'"
            )
        )
        conn.commit()
