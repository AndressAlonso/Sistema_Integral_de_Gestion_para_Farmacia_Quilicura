"""E5-H1/H3/H4/H5: sesiones de caja y ventas transaccionales."""

from alembic import op

revision = "0012_pos_caja"
down_revision = "0011_evento_auditoria"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE TABLE sesion_caja (\n\tid UUID NOT NULL, \n\tusuario_id UUID NOT NULL, \n\tsucursal_id UUID NOT NULL, \n\tapertura_en TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tmonto_inicial NUMERIC(14, 2) NOT NULL, \n\tcierre_en TIMESTAMP WITH TIME ZONE, \n\tefectivo_contado NUMERIC(14, 2), \n\tresumen_cierre JSONB, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_caja_monto CHECK (monto_inicial >= 0), \n\tCONSTRAINT ck_caja_cierre CHECK ((cierre_en IS NULL AND efectivo_contado IS NULL AND resumen_cierre IS NULL) OR (cierre_en >= apertura_en AND efectivo_contado >= 0 AND resumen_cierre IS NOT NULL)), \n\tFOREIGN KEY(usuario_id) REFERENCES usuario_interno (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(sucursal_id) REFERENCES sucursal (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_caja_abierta_usuario_sucursal ON sesion_caja (usuario_id, sucursal_id) WHERE cierre_en IS NULL"
    )
    op.execute(
        "CREATE TABLE venta (\n\tid UUID NOT NULL, \n\tsolicitud_hash VARCHAR(64) NOT NULL, \n\tsesion_caja_id UUID NOT NULL, \n\tusuario_id UUID NOT NULL, \n\tsucursal_id UUID NOT NULL, \n\tfecha TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tmedio_pago VARCHAR(20) NOT NULL, \n\tsubtotal NUMERIC(14, 2) NOT NULL, \n\tdescuento NUMERIC(14, 2) NOT NULL, \n\ttotal NUMERIC(14, 2) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_venta_pago CHECK (medio_pago IN ('EFECTIVO','DEBITO','CREDITO','TRANSFERENCIA')), \n\tCONSTRAINT ck_venta_totales CHECK (subtotal >= 0 AND descuento >= 0 AND total >= 0 AND total = subtotal - descuento), \n\tFOREIGN KEY(sesion_caja_id) REFERENCES sesion_caja (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(usuario_id) REFERENCES usuario_interno (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(sucursal_id) REFERENCES sucursal (id) ON DELETE RESTRICT\n)"
    )
    op.execute("CREATE INDEX ix_venta_sesion_caja_id ON venta (sesion_caja_id)")
    op.execute("CREATE INDEX ix_venta_sucursal_id ON venta (sucursal_id)")
    op.execute(
        "CREATE TABLE venta_detalle (\n\tid UUID NOT NULL, \n\tventa_id UUID NOT NULL, \n\tproducto_id UUID NOT NULL, \n\tnombre VARCHAR(150) NOT NULL, \n\tsku VARCHAR(64) NOT NULL, \n\tcantidad INTEGER NOT NULL, \n\tprecio_base NUMERIC(14, 2) NOT NULL, \n\tprecio_final NUMERIC(14, 2) NOT NULL, \n\tpromocion JSONB, \n\ttotal NUMERIC(14, 2) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_venta_producto UNIQUE (venta_id, producto_id), \n\tCONSTRAINT ck_venta_detalle CHECK (cantidad > 0 AND precio_base >= 0 AND precio_final >= 0 AND precio_final <= precio_base AND total = precio_final * cantidad), \n\tFOREIGN KEY(venta_id) REFERENCES venta (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(producto_id) REFERENCES producto (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE TABLE venta_lote (\n\tid UUID NOT NULL, \n\tventa_detalle_id UUID NOT NULL, \n\tlote_id UUID NOT NULL, \n\tcantidad INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_venta_detalle_lote UNIQUE (venta_detalle_id, lote_id), \n\tCONSTRAINT ck_venta_lote_cantidad CHECK (cantidad > 0), \n\tFOREIGN KEY(venta_detalle_id) REFERENCES venta_detalle (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(lote_id) REFERENCES lote_inventario (id) ON DELETE RESTRICT\n)"
    )


def downgrade():
    op.drop_table("venta_lote")
    op.drop_table("venta_detalle")
    op.drop_table("venta")
    op.drop_table("sesion_caja")
