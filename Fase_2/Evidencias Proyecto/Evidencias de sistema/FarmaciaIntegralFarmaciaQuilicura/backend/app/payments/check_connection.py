"""Comprueba la credencial de Mercado Pago sin crear pagos."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.payments.config import PaymentSettings


def main() -> None:
    settings = PaymentSettings()
    request = Request(
        "https://api.mercadopago.com/users/me",
        headers={
            "Authorization": (
                f"Bearer {settings.access_token.get_secret_value()}"
            ),
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=15) as response:
            account = json.load(response)
    except HTTPError as error:
        raise SystemExit(
            f"ERROR: Mercado Pago respondió HTTP {error.code}. "
            "Revisa la credencial configurada."
        ) from None
    except (URLError, TimeoutError):
        raise SystemExit(
            "ERROR: no se pudo conectar con Mercado Pago. "
            "Revisa la conexión a internet y vuelve a intentar."
        ) from None
    except (ValueError, UnicodeError):
        raise SystemExit(
            "ERROR: Mercado Pago devolvió una respuesta no válida."
        ) from None

    if not isinstance(account, dict) or not account.get("id"):
        raise SystemExit("ERROR: no se pudo identificar la cuenta.")

    site = account.get("site_id")
    is_test = "test_user" in (account.get("tags") or [])

    print("OK: Mercado Pago aceptó la credencial.")
    print(f"País de la cuenta: {site}")
    print(f"Cuenta identificada como prueba: {'Sí' if is_test else 'No'}")
    print("No se crearon pagos ni se modificaron pedidos.")


if __name__ == "__main__":
    main()