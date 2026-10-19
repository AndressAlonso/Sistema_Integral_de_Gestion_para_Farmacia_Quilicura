from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy import select, update

from app.customers.models import Cliente, SesionCliente


class CustomerSessionRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    @staticmethod
    def token_hash(token):
        return sha256(token.encode()).hexdigest()

    def register(self, token, customer_id, expires):
        with self.session_factory.begin() as db:
            row = db.scalar(select(Cliente).where(Cliente.id == customer_id).with_for_update())
            if row is None or not row.activo:
                return False
            db.add(SesionCliente(cliente_id=customer_id, token_hash=self.token_hash(token),
                                creada_en=datetime.now(timezone.utc), expira_en=expires))
        return True

    def active(self, token, customer_id):
        with self.session_factory() as db:
            return db.scalar(select(SesionCliente.id).where(
                SesionCliente.cliente_id == customer_id,
                SesionCliente.token_hash == self.token_hash(token),
                SesionCliente.revocada_en.is_(None),
                SesionCliente.expira_en > datetime.now(timezone.utc),
            )) is not None

    def revoke(self, token):
        with self.session_factory.begin() as db:
            db.execute(update(SesionCliente).where(
                SesionCliente.token_hash == self.token_hash(token), SesionCliente.revocada_en.is_(None),
            ).values(revocada_en=datetime.now(timezone.utc)))
