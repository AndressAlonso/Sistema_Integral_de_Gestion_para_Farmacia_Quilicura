from fastapi import HTTPException

from app.auth.security import dummy_hash, password_hasher, verify_password
from app.auth.state import LoginLimited
from app.customers.repository import DuplicateCustomerEmail
from app.customers.schemas import PublicCustomer


def public_customer(row):
    return PublicCustomer(id=row.id, name=row.nombre, email=row.correo)


def register_customer(data, repository):
    try:
        return public_customer(repository.create(
            data.name, str(data.email), password_hasher.hash(data.password.get_secret_value()),
        ))
    except DuplicateCustomerEmail:
        raise HTTPException(409, "No se pudo registrar una cuenta con ese correo.") from None


def limited(seconds):
    raise HTTPException(429, "Demasiados intentos. Intenta nuevamente más tarde.",
                        headers={"Retry-After": str(seconds)})


def verify_customer_login(data, request):
    email = str(data.email)
    ip = request.client.host if request.client else "unknown"
    state = request.app.state.customer_auth
    try:
        ticket = state.begin_login(email, ip)
    except LoginLimited as exc:
        limited(exc.seconds)
    row = request.app.state.customers.by_email(email)
    valid = verify_password(data.password.get_secret_value(), row.password_hash if row else dummy_hash)
    success = valid and row is not None and row.activo
    wait = state.finish_login(email, ip, ticket, success)
    if not success:
        if wait:
            limited(wait)
        raise HTTPException(401, "Correo o contraseña incorrectos.")
    return row
