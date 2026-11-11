"""Run the suite in a disposable local PostgreSQL database (E7-H1/H5/H6)."""

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.config import database_url


def main():
    url = database_url()
    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("Solo se permiten instancias PostgreSQL locales.")
    name = f"sigfq_test_{uuid4().hex}"
    admin = create_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT",
        hide_parameters=True,
    )
    env = dict(os.environ, DB_NAME=name, SIGFQ_TEST_ROLLBACK="1", SIGFQ_TEST_ISOLATED="1")
    created = False
    try:
        with admin.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
        created = True
        print(f"Base temporal creada: {name}", flush=True)
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND, env=env, check=True,
        )
        return subprocess.run(
            [sys.executable, "-m", "pytest", *sys.argv[1:]],
            cwd=BACKEND, env=env, check=False,
        ).returncode
    finally:
        if created:
            # Only the random database created by this invocation is removed.
            with admin.connect() as connection:
                connection.exec_driver_sql(f'DROP DATABASE "{name}" WITH (FORCE)')
            print(f"Base temporal eliminada: {name}", flush=True)
        admin.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
