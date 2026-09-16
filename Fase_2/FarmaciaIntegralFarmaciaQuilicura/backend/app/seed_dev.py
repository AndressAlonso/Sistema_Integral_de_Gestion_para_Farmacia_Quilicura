"""Crea exclusivamente fixtures locales para probar E1-H1; no es un CRUD."""

import json
from getpass import getpass

from app.auth.security import password_hasher
from app.config import Settings


def main():
    settings = Settings()
    path = settings.users_file
    if path.exists():
        raise SystemExit("El archivo ya existe; no se sobrescribieron usuarios.")
    password = getpass("Contraseña de desarrollo (mínimo 12 caracteres): ")
    if len(password) < 12:
        raise SystemExit("Usa al menos 12 caracteres.")
    users = [
        {
            "id": 1,
            "email": "interno@farmacia.cl",
            "password_hash": password_hasher.hash(password),
            "is_active": True,
        },
        {
            "id": 2,
            "email": "inactivo@farmacia.cl",
            "password_hash": password_hasher.hash(password),
            "is_active": False,
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as file:
        json.dump(users, file, indent=2)
    print("Usuarios locales creados: interno@farmacia.cl e inactivo@farmacia.cl.")


if __name__ == "__main__":
    main()
