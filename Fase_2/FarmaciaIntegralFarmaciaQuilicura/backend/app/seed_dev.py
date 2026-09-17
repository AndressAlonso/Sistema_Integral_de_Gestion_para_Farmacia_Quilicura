"""Fixtures locales E1-H1/E1-H2. No ejecutarlo sobre datos de producción."""

import argparse
import json
from getpass import getpass

from app.auth.security import password_hasher
from app.auth.users import LocalUserRepository
from app.config import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--upgrade-e1-h2",
        action="store_true",
        help="Agrega nombre/roles a los dos fixtures existentes, sin cambiar hashes ni IDs.",
    )
    args = parser.parse_args()
    settings = Settings()
    path = settings.users_file
    if args.upgrade_e1_h2:
        repository = LocalUserRepository(path)
        for email, name, role in (
            ("interno@farmacia.cl", "Administrador de desarrollo", "ADMINISTRADOR"),
            ("inactivo@farmacia.cl", "Usuario inactivo de desarrollo", "CAJERO"),
        ):
            user = repository.by_email(email)
            if user is not None:
                repository.update(
                    user.id, {"name": user.name or name, "roles": user.roles or [role]}
                )
        print("Fixtures E1-H2 actualizados; contraseñas y estados conservados.")
        return
    if path.exists():
        raise SystemExit("El archivo ya existe; no se sobrescribieron usuarios.")
    password = getpass("Contraseña de desarrollo (mínimo 12 caracteres): ")
    if len(password) < 12:
        raise SystemExit("Usa al menos 12 caracteres.")
    users = [
        {
            "id": 1,
            "name": "Administrador de desarrollo",
            "roles": ["ADMINISTRADOR"],
            "email": "interno@farmacia.cl",
            "password_hash": password_hasher.hash(password),
            "is_active": True,
        },
        {
            "id": 2,
            "name": "Usuario inactivo de desarrollo",
            "roles": ["CAJERO"],
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
