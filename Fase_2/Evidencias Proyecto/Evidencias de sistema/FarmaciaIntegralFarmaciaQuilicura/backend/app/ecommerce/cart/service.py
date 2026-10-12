from decimal import Decimal

from app.ecommerce.cart.schemas import CartLine, CartResponse
from app.ecommerce.schemas import PublicBranch


class CartService:
    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def available(inventory, lots, reserved, today):
        known = sum(reserved.get(lot.id, 0) for lot in lots)
        # Los lotes activos representan el stock físico, incluso si están vencidos.
        if (inventory.stock_fisico < 0 or inventory.stock_reservado < 0
                or inventory.stock_reservado > inventory.stock_fisico
                or sum(lot.cantidad for lot in lots if lot.activo) != inventory.stock_fisico
                or known > inventory.stock_reservado
                or any(lot.cantidad < 0 or reserved.get(lot.id, 0) > lot.cantidad
                       or (reserved.get(lot.id, 0) and not lot.activo) for lot in lots)):
            return None
        fresh_free = sum(lot.cantidad - reserved.get(lot.id, 0) for lot in lots
                         if lot.activo and lot.fecha_vencimiento > today)
        unallocated = inventory.stock_reservado - known
        return max(0, min(inventory.stock_fisico - inventory.stock_reservado, fresh_free - unallocated))

    def validate(self, data):
        today, branches, products, inventories, lots, reservations = self.repository.snapshot([i.product_id for i in data.items])
        branch = next((b for b in branches if b.id == data.pickup_branch_id), None)
        issues = []
        if not data.items:
            issues.append("El carrito está vacío.")
        if branch is None:
            issues.append("Selecciona una sucursal activa para retiro.")
        products = {p.id: p for p in products}
        lines = []
        for item in data.items:
            line = CartLine(product_id=item.product_id, quantity=item.quantity)
            product = products.get(item.product_id)
            if product is None or not product.activo or not product.publicado_online:
                line.issues.append("El producto ya no está disponible para venta online.")
            elif product.requiere_receta:
                line.name = product.nombre
                line.issues.append("Requiere receta. Compra presencial.")
            else:
                line.name = product.nombre
                line.unit_price = product.precio_actual
                line.subtotal = product.precio_actual * item.quantity
                stocks = {}
                for inventory in inventories:
                    if inventory.producto_id == product.id:
                        value = self.available(inventory, [lot for lot in lots if lot.inventario_sucursal_id == inventory.id], reservations, today)
                        if value is None:
                            line.issues.append("No pudimos confirmar la disponibilidad de este producto. Intenta más tarde.")
                            break
                        stocks[inventory.sucursal_id] = value
                if not line.issues:
                    line.global_available = sum(stocks.values())
                    line.local_available = stocks.get(branch.id, 0) if branch else None
                    if item.quantity > line.global_available:
                        line.issues.append("La disponibilidad global es insuficiente para esta cantidad.")
                    line.requires_transfer = bool(branch and item.quantity > line.local_available and not line.issues)
                    line.valid = not line.issues
            lines.append(line)
        valid = bool(lines) and branch is not None and all(line.valid for line in lines)
        return CartResponse(valid=valid, pickup_branch=PublicBranch(id=branch.id, name=branch.nombre, address=branch.direccion_local) if branch else None,
                            items=lines, total=sum((line.subtotal for line in lines), Decimal(0)) if valid else None, issues=issues)
