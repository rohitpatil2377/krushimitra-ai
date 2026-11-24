"""Create the pgvector extension + all tables. Dev convenience (use Alembic for real migrations).

Run (with Postgres up):  python -m scripts.init_db
"""
from sqlalchemy import text

import app.models  # noqa: F401  (registers all models on Base.metadata)
from app.core.db import Base, engine


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    print("✅ pgvector extension ensured + tables created.")


if __name__ == "__main__":
    main()
