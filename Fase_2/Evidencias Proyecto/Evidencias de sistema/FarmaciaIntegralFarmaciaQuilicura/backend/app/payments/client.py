"""Cliente HTTP de Mercado Pago. No confirma pedidos ni reintenta cobros."""

import json
import re
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID

from app.payments.config import PaymentSettings


class MercadoPagoError(Exception):
    """Fallo del proveedor sin exponer credenciales ni datos personales."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class MercadoPagoClient:
    def __init__(self, settings: PaymentSettings):
        self.settings = settings
        self.opener = build_opener(NoRedirect())

    def create_preference(self, payload: dict) -> dict:
        request = Request(
            "https://api.mercadopago.com/checkout/preferences",
            data=json.dumps(payload, allow_nan=False).encode("utf-8"),
            headers={
                "Authorization": (
                    f"Bearer {self.settings.access_token.get_secret_value()}"
                ),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with self.opener.open(request, timeout=15) as response:
                result = json.load(response)
        except HTTPError as error:
            raise MercadoPagoError(
                f"Mercado Pago respondió HTTP {error.code}."
            ) from None
        except (URLError, TimeoutError, OSError):
            raise MercadoPagoError(
                "No se pudo confirmar la respuesta de Mercado Pago."
            ) from None
        except (ValueError, UnicodeError):
            raise MercadoPagoError(
                "Mercado Pago devolvió una respuesta no válida."
            ) from None

        if not isinstance(result, dict) or not all(
            isinstance(result.get(key), str) and result[key].strip()
            for key in ("id", "init_point")
        ):
            raise MercadoPagoError("La respuesta no contiene el enlace de pago.")
        return {"id": result["id"], "init_point": result["init_point"]}

    def _get(self, path: str) -> dict:
        request = Request(
            "https://api.mercadopago.com" + path,
            headers={
                "Authorization": f"Bearer {self.settings.access_token.get_secret_value()}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with self.opener.open(request, timeout=5) as response:
                result = json.load(response, parse_float=Decimal)
        except HTTPError as error:
            raise MercadoPagoError(
                f"Mercado Pago respondió HTTP {error.code}."
            ) from None
        except (URLError, TimeoutError, OSError, ValueError, UnicodeError):
            raise MercadoPagoError(
                "No se pudo verificar el pago con Mercado Pago."
            ) from None
        if not isinstance(result, dict):
            raise MercadoPagoError("La respuesta del proveedor no es válida.")
        return result

    def get_account(self) -> dict:
        return self._get("/users/me")

    def get_payment(self, payment_id: str) -> dict:
        if not re.fullmatch(r"[0-9]{1,30}", payment_id):
            raise MercadoPagoError("El identificador del pago no es válido.")
        return self._get("/v1/payments/" + payment_id)

    def get_merchant_order(self, merchant_order_id: str) -> dict:
        if not re.fullmatch(r"[0-9]{1,30}", merchant_order_id):
            raise MercadoPagoError("El identificador de la orden no es válido.")
        return self._get("/merchant_orders/" + merchant_order_id)

    def search_payments(self, order_id: UUID) -> list[dict]:
        reference = str(UUID(str(order_id)))
        results = []
        identities = set()
        for offset in range(0, 500, 50):
            query = urlencode(
                {
                    "external_reference": reference,
                    "limit": 50,
                    "offset": offset,
                    "sort": "id",
                    "criteria": "asc",
                }
            )
            page = self._get("/v1/payments/search?" + query)
            paging = page.get("paging")
            rows = page.get("results")
            if not isinstance(paging, dict) or not isinstance(rows, list):
                raise MercadoPagoError("La búsqueda de pagos está incompleta.")
            total = paging.get("total")
            if type(total) is not int or total < 0 or paging.get("offset") != offset:
                raise MercadoPagoError("La paginación de pagos no es válida.")
            for row in rows:
                if (
                    not isinstance(row, dict)
                    or row.get("external_reference") != reference
                ):
                    raise MercadoPagoError("La búsqueda no corresponde al pedido.")
                identity = str(row.get("id", ""))
                if not re.fullmatch(r"[0-9]{1,30}", identity) or identity in identities:
                    raise MercadoPagoError("La búsqueda de pagos es ambigua.")
                identities.add(identity)
                results.append(row)
            if len(results) >= total:
                if len(results) != total:
                    raise MercadoPagoError("La búsqueda cambió durante la consulta.")
                return results
            if len(rows) != 50:
                raise MercadoPagoError("La búsqueda de pagos está incompleta.")
        raise MercadoPagoError("Hay demasiados pagos para conciliar automáticamente.")
