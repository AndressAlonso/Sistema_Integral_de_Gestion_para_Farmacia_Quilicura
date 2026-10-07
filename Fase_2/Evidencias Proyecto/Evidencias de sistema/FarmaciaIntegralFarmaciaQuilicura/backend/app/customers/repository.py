from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.customers.models import Cliente
from app.customers.schemas import normalize_email


class DuplicateCustomerEmail(Exception):
    pass


class CustomerRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def by_email(self, email):
        with self.session_factory() as db:
            return db.scalar(select(Cliente).where(Cliente.correo == normalize_email(email)))

    def by_id(self, customer_id):
        with self.session_factory() as db:
            return db.get(Cliente, customer_id)

    def create(self, name, email, password_hash):
        try:
            with self.session_factory.begin() as db:
                row = Cliente(nombre=name, correo=normalize_email(email), password_hash=password_hash, activo=True)
                db.add(row)
                db.flush()
                return row
        except IntegrityError as exc:
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            if getattr(exc.orig, "sqlstate", None) == "23505" and constraint == "cliente_correo_key":
                raise DuplicateCustomerEmail from None
            raise
