"""Presentación de correos y comprobantes, sin recursos externos ni datos sin escapar."""
from html import escape


def money(value):
    pattern = ",.0f" if value == value.to_integral_value() else ",.2f"
    return "$" + format(value, pattern).translate(str.maketrans({",": ".", ".": ","}))


def manual_label(code):
    return " ".join(code[index:index + 4] for index in range(0, len(code), 4))


def ready_email(order, number, title, manual):
    rows = "".join(
        f'<tr><td style="padding:14px 0;border-bottom:1px solid #ece8ef;color:#26354b">{escape(d.nombre)}'
        f'<br><span style="font-size:13px;color:#64748b">{d.cantidad} {"unidad" if d.cantidad == 1 else "unidades"}</span></td>'
        f'<td align="right" style="padding:14px 0;border-bottom:1px solid #ece8ef;white-space:nowrap;color:#26354b">{money(d.subtotal)}</td></tr>'
        for d in order.detalles)
    address = escape(order.sucursal.direccion_local or "")
    groups = " ".join(f'<span style="display:inline-block">{escape(part)}</span>' for part in manual_label(manual).split())
    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title></head>
<body style="margin:0;padding:0;background:#f5f4f8;font-family:Arial,Helvetica,sans-serif;color:#26354b">
<div style="display:none;max-height:0;overflow:hidden">Retira en {escape(order.sucursal.nombre)}. Tu QR y código de retiro están en este correo.</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f5f4f8"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;background:#ffffff;border:1px solid #e6e1eb;border-radius:16px;overflow:hidden">
<tr><td style="background:#702582;padding:24px;color:#ffffff"><p style="margin:0;font-size:20px;font-weight:bold">Farmacia Quilicura</p><p style="margin:6px 0 0;font-size:13px;color:#eee1f3">Tu salud, cerca de ti</p></td></tr>
<tr><td style="padding:28px 24px 12px"><span style="display:inline-block;background:#edf6e7;color:#3d681c;padding:7px 11px;border-radius:16px;font-size:12px;font-weight:bold">LISTO PARA RETIRO</span>
<h1 style="margin:18px 0 12px;font-size:28px;line-height:1.2;color:#26354b">{escape(title)}</h1>
<p style="margin:0 0 12px;line-height:1.6">Hola, {escape(order.nombre)}.</p><p style="margin:0;line-height:1.6;color:#526177">Ya preparamos tus productos. Presenta este QR o dicta el código de retiro al personal de la sucursal.</p></td></tr>
<tr><td style="padding:12px 24px"><table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f7f5fa;border-radius:12px"><tr><td style="padding:18px">
<p style="margin:0 0 6px;color:#64748b;font-size:12px">SUCURSAL DE RETIRO</p><p style="margin:0;color:#26354b;font-size:18px;font-weight:bold">{escape(order.sucursal.nombre)}</p><p style="margin:7px 0 0;color:#64748b;font-size:14px;line-height:1.5">{address}</p></td></tr></table></td></tr>
<tr><td style="padding:12px 24px"><table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #ded6e7;border-radius:12px"><tr><td align="center" style="padding:20px 12px">
<h2 style="margin:0 0 12px;font-size:18px;color:#702582">Tu acceso al retiro</h2>
<img src="cid:retiro-qr" width="200" height="200" alt="QR para retirar tu pedido" style="display:block;width:200px;max-width:100%;height:auto;border:0;margin:0 auto">
<p style="margin:16px 0 8px;color:#526177;font-size:14px">¿No puedes escanear? Usa este código:</p>
<p style="margin:0;font-family:Consolas,'Courier New',monospace;font-size:22px;font-weight:bold;line-height:1.6;color:#702582">{groups}</p>
<p style="margin:12px 0 0;font-size:12px;line-height:1.5;color:#64748b">El QR y el código corresponden al mismo retiro.<br>Compártelos únicamente con el personal al recibir tus productos.</p></td></tr></table></td></tr>
<tr><td style="padding:16px 24px 24px"><h2 style="margin:0 0 8px;font-size:18px">Resumen de tu compra</h2><table width="100%" cellspacing="0" cellpadding="0"><tbody>{rows}</tbody><tfoot><tr><td style="padding-top:18px;font-size:17px;font-weight:bold">Total pagado</td><td align="right" style="padding-top:18px;font-size:22px;font-weight:bold;color:#3d681c">{money(order.total)}</td></tr></tfoot></table>
<p style="margin:22px 0 0;font-size:12px;line-height:1.6;color:#64748b;overflow-wrap:anywhere;word-break:break-all">Pedido {escape(number)}</p></td></tr>
<tr><td style="background:#faf9fc;border-top:1px solid #ece8ef;padding:20px 24px"><p style="margin:0;font-size:13px;line-height:1.6;color:#526177">Adjuntamos tu comprobante interno sin validez tributaria y una copia del QR. Conserva este correo hasta retirar tu pedido.</p><p style="margin:10px 0 0;font-size:12px;color:#64748b">El QR y el código no vencen por el paso del tiempo y permiten un único retiro.</p></td></tr>
</table><p style="margin:16px 0 0;font-size:12px;color:#64748b">Farmacia Quilicura · Tienda online</p>
</td></tr></table></body></html>'''


def receipt_html(order, number, sale):
    rows = "".join(f"<tr><td>{escape(d.nombre)}</td><td>{d.cantidad}</td><td>{escape(d.promocion or 'Sin promoción')}</td><td>{money(d.subtotal)}</td></tr>" for d in order.detalles)
    return f"<!doctype html><html lang='es'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Comprobante</title><style>body{{font:15px Arial,sans-serif;color:#26354b;max-width:800px;margin:24px auto;padding:16px}}h1{{font-size:22px;color:#702582}}table{{width:100%;border-collapse:collapse}}td,th{{padding:12px 6px;border-bottom:1px solid #ddd;text-align:left}}p{{overflow-wrap:anywhere}}@media print{{body{{margin:0}}}}</style><h1>COMPROBANTE SIN VALIDEZ TRIBUTARIA</h1><p>{escape(number)}</p><p>Venta: {sale.id}</p><p>Sucursal: {escape(order.sucursal.nombre)}</p><p>Fecha de venta: {sale.fecha.isoformat()}</p><p>Canal: venta online · Medio de pago: Mercado Pago · Sin cajero presencial</p><table><tr><th>Producto</th><th>Unidades</th><th>Promoción</th><th>Subtotal</th></tr>{rows}</table><p><strong>Total: {money(order.total)}</strong></p></html>"
