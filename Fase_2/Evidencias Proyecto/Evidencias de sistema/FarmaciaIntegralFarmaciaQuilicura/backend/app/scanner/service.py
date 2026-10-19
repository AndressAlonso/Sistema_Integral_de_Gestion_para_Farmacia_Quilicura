"""E8-H1: generación, consumo y consulta de vinculaciones del escáner."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from uuid import uuid4

from sqlalchemy import select, text

from app.auth.sessions import SessionRepository
from app.models import (
    CodigoBarra,
    LecturaScanner,
    Producto,
    SesionCaja,
    SesionInterna,
    Sucursal,
    VinculacionScanner,
)


class ScannerError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class ScannerService:
    def __init__(self, factory):
        self.factory = factory

    @staticmethod
    def _authorize(actor):
        required = {"pos.operar", "caja.operar"}
        if not actor.is_active or not required.issubset(actor.permissions):
            raise ScannerError(
                403,
                "No tienes permiso para vincular el escáner al POS.",
            )

    @staticmethod
    def _session(db, actor, token, now):
        session = db.scalar(
            select(SesionInterna).where(
                SesionInterna.token_hash == SessionRepository.token_hash(token),
                SesionInterna.usuario_id == actor.id,
                SesionInterna.revocada_en.is_(None),
                SesionInterna.expira_en > now,
            )
        )
        if session is None:
            raise ScannerError(401, "La sesión no es válida o expiró.")
        return session

    @staticmethod
    def _session_active(session, user_id, now):
        return (
            session is not None
            and session.usuario_id == user_id
            and session.revocada_en is None
            and session.expira_en > now
        )

    @staticmethod
    def _branch_active(db, branch_id):
        branch = db.get(Sucursal, branch_id)
        return branch is not None and branch.activa

    @staticmethod
    def _cash_matches(cash, link):
        return (
            cash is not None
            and cash.cierre_en is None
            and cash.usuario_id == link.usuario_id
            and cash.sucursal_id == link.sucursal_id
        )

    def _state(self, db, link, now):
        if link.revocada_en is not None:
            return "REVOKED"

        if link.expira_en <= now:
            return "EXPIRED"

        web = db.get(SesionInterna, link.sesion_web_id)
        cash = db.get(SesionCaja, link.sesion_caja_id)

        if (
            not self._session_active(web, link.usuario_id, now)
            or not self._cash_matches(cash, link)
            or not self._branch_active(db, link.sucursal_id)
        ):
            return "DISCONNECTED"

        if link.vinculada_en is None:
            return "EXPIRED" if link.qr_expira_en <= now else "PENDING"

        mobile = db.get(SesionInterna, link.sesion_movil_id)
        if not self._session_active(mobile, link.usuario_id, now):
            return "DISCONNECTED"

        return "LINKED"

    @staticmethod
    def _response(link, state):
        return {
            "id": link.id,
            "state": state,
            "cash_id": link.sesion_caja_id,
            "branch_id": link.sucursal_id,
            "qr_expires_at": link.qr_expira_en,
            "expires_at": link.expira_en,
            "linked_at": link.vinculada_en,
        }

    def create(self, actor, token):
        self._authorize(actor)

        with self.factory.begin() as db:
            now = datetime.now(timezone.utc)
            web = self._session(db, actor, token, now)

            if not self._branch_active(db, actor.branch_id):
                raise ScannerError(403, "La sucursal no está activa.")

            cash = db.scalar(
                select(SesionCaja)
                .where(
                    SesionCaja.usuario_id == actor.id,
                    SesionCaja.sucursal_id == actor.branch_id,
                    SesionCaja.cierre_en.is_(None),
                )
                .with_for_update()
            )
            if cash is None:
                raise ScannerError(
                    409,
                    "Abre tu caja antes de vincular el teléfono.",
                )

            now = datetime.now(timezone.utc)
            if web.expira_en <= now:
                raise ScannerError(401, "La sesión no es válida o expiró.")

            code = token_urlsafe(32)

            link = VinculacionScanner(
                id=uuid4(),
                usuario_id=actor.id,
                sucursal_id=actor.branch_id,
                sesion_caja_id=cash.id,
                sesion_web_id=web.id,
                codigo_hash=sha256(code.encode()).hexdigest(),
                creada_en=now,
                qr_expira_en=min(
                    now + timedelta(minutes=2),
                    web.expira_en,
                ),
                expira_en=web.expira_en,
            )
            db.add(link)
            db.flush()

            result = self._response(link, "PENDING")
            result["pairing_code"] = code
            return result

    def claim(self, actor, token, code):
        self._authorize(actor)

        with self.factory.begin() as db:
            # El bloqueo impide que dos teléfonos consuman el mismo QR.
            link = db.scalar(
                select(VinculacionScanner)
                .where(
                    VinculacionScanner.codigo_hash
                    == sha256(code.encode()).hexdigest()
                )
                .with_for_update()
            )

            if (
                link is None
                or link.usuario_id != actor.id
                or link.sucursal_id != actor.branch_id
            ):
                raise ScannerError(
                    404,
                    "El código no es válido para esta cuenta y sucursal.",
                )

            # Comparte el bloqueo de caja con las operaciones del POS.
            db.scalar(
                select(SesionCaja)
                .where(SesionCaja.id == link.sesion_caja_id)
                .with_for_update()
            )

            now = datetime.now(timezone.utc)
            mobile = self._session(db, actor, token, now)

            if mobile.id == link.sesion_web_id:
                raise ScannerError(
                    409,
                    "Vincula desde la sesión de la aplicación móvil.",
                )

            if self._state(db, link, now) != "PENDING":
                raise ScannerError(
                    409,
                    "El código venció, ya fue utilizado o la conexión terminó.",
                )

            link.sesion_movil_id = mobile.id
            link.vinculada_en = now

            # La conexión tampoco puede sobrevivir a la sesión móvil.
            link.expira_en = min(link.expira_en, mobile.expira_en)
            link.qr_expira_en = min(link.qr_expira_en, link.expira_en)

            db.flush()
            return self._response(link, "LINKED")

    def _owned_link(self, db, actor, token, link_id, now):
        session = self._session(db, actor, token, now)

        link = db.scalar(
            select(VinculacionScanner)
            .where(VinculacionScanner.id == link_id)
            .with_for_update()
        )

        if (
            link is None
            or link.usuario_id != actor.id
            or link.sucursal_id != actor.branch_id
            or session.id not in (link.sesion_web_id, link.sesion_movil_id)
        ):
            raise ScannerError(404, "No se encontró la vinculación.")

        return link

    def status(self, actor, token, link_id):
        self._authorize(actor)

        with self.factory.begin() as db:
            now = datetime.now(timezone.utc)
            link = self._owned_link(db, actor, token, link_id, now)
            return self._response(
                link,
                self._state(db, link, datetime.now(timezone.utc)),
            )

    def revoke(self, actor, token, link_id):
        self._authorize(actor)

        with self.factory.begin() as db:
            now = datetime.now(timezone.utc)
            link = self._owned_link(db, actor, token, link_id, now)

            if link.revocada_en is None:
                link.revocada_en = datetime.now(timezone.utc)

            db.flush()
            return self._response(link, "REVOKED")
        
    @staticmethod
    def _read_response(read):
        return {
            "id": read.id,
            "sequence": read.secuencia,
            "link_id": read.vinculacion_id,
            "code": read.codigo,
            "product_id": read.producto_id,
            "result": read.resultado,
            "created_at": read.creada_en,
            "received_at": read.recibida_pos_en,
        }

    def submit_read(self, actor, token, link_id, request_id, code):
        self._authorize(actor)

        with self.factory.begin() as db:
            now = datetime.now(timezone.utc)
            link = self._owned_link(db, actor, token, link_id, now)

            session = self._session(db, actor, token, now)
            if session.id != link.sesion_movil_id:
                raise ScannerError(
                    403,
                    "Solo la sesión móvil vinculada puede enviar lecturas.",
                )

            # Se coordina con el cierre de caja y las operaciones del POS.
            db.scalar(
                select(SesionCaja)
                .where(SesionCaja.id == link.sesion_caja_id)
                .with_for_update()
            )

            # Serializa el mismo UUID incluso si llega por otra vinculación.
            db.execute(
                text(
                    "SELECT pg_advisory_xact_lock("
                    "hashtextextended(:key, 0))"
                ),
                {"key": f"scanner-read:{request_id}"},
            )

            now = datetime.now(timezone.utc)
            if self._state(db, link, now) != "LINKED":
                raise ScannerError(
                    409,
                    "La vinculación terminó. Vincula nuevamente el teléfono.",
                )

            previous = db.get(LecturaScanner, request_id)
            if previous is not None:
                if (
                    previous.vinculacion_id != link.id
                    or previous.codigo != code
                ):
                    raise ScannerError(
                        409,
                        "El identificador de lectura ya se usó "
                        "con otros datos.",
                    )

                return self._read_response(previous)

            product = db.scalar(
                select(Producto)
                .join(CodigoBarra, CodigoBarra.producto_id == Producto.id)
                .where(CodigoBarra.valor == code)
            )

            if product is None:
                result = "NOT_FOUND"
            elif not product.activo:
                result = "INACTIVE"
            else:
                result = "FOUND"

            read = LecturaScanner(
                id=request_id,
                vinculacion_id=link.id,
                codigo=code,
                producto_id=product.id if product is not None else None,
                resultado=result,
                creada_en=now,
            )
            db.add(read)
            db.flush()

            return self._read_response(read)

    def _web_link(self, db, actor, token, link_id):
        now = datetime.now(timezone.utc)
        link = self._owned_link(db, actor, token, link_id, now)
        session = self._session(db, actor, token, now)

        if session.id != link.sesion_web_id:
            raise ScannerError(
                403,
                "Solo la sesión POS vinculada puede recibir lecturas.",
            )

        db.scalar(
            select(SesionCaja)
            .where(SesionCaja.id == link.sesion_caja_id)
            .with_for_update()
        )

        if self._state(db, link, datetime.now(timezone.utc)) != "LINKED":
            raise ScannerError(409, "La vinculación no está activa.")

        return link

    def pending_reads(self, actor, token, link_id):
        self._authorize(actor)

        with self.factory.begin() as db:
            link = self._web_link(db, actor, token, link_id)

            reads = db.scalars(
                select(LecturaScanner)
                .where(
                    LecturaScanner.vinculacion_id == link.id,
                    LecturaScanner.recibida_pos_en.is_(None),
                )
                .order_by(LecturaScanner.secuencia)
                .limit(50)
            )

            return [self._read_response(read) for read in reads]

    def acknowledge_read(self, actor, token, link_id, read_id):
        self._authorize(actor)

        with self.factory.begin() as db:
            link = self._web_link(db, actor, token, link_id)
            read = db.get(LecturaScanner, read_id)

            if read is None or read.vinculacion_id != link.id:
                raise ScannerError(404, "No se encontró la lectura.")

            if read.recibida_pos_en is None:
                read.recibida_pos_en = datetime.now(timezone.utc)
                db.flush()

            return self._read_response(read)