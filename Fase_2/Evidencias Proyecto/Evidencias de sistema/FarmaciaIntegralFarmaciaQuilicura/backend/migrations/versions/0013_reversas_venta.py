"""E5-H6: reversas vinculadas a venta y caja del reembolso."""

from alembic import op

revision = "0013_reversas_venta"
down_revision = "0012_pos_caja"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE TABLE reversa_venta (\n\tid UUID NOT NULL, \n\tsolicitud_hash VARCHAR(64) NOT NULL, \n\tventa_id UUID NOT NULL, \n\tusuario_id UUID NOT NULL, \n\tsesion_caja_id UUID NOT NULL, \n\tfecha TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\ttipo VARCHAR(20) NOT NULL, \n\tmotivo VARCHAR(250) NOT NULL, \n\timporte NUMERIC(14, 2) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_reversa_tipo CHECK (tipo IN ('ANULACION','DEVOLUCION')), \n\tCONSTRAINT ck_reversa_datos CHECK (btrim(motivo) <> '' AND importe >= 0), \n\tFOREIGN KEY(venta_id) REFERENCES venta (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(usuario_id) REFERENCES usuario_interno (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(sesion_caja_id) REFERENCES sesion_caja (id) ON DELETE RESTRICT\n)"
    )
    op.execute(
        "CREATE INDEX ix_reversa_venta_sesion_caja_id ON reversa_venta (sesion_caja_id)"
    )
    op.execute("CREATE INDEX ix_reversa_venta_venta_id ON reversa_venta (venta_id)")
    op.execute(
        "CREATE TABLE reversa_venta_detalle (\n\tid UUID NOT NULL, \n\treversa_id UUID NOT NULL, \n\tventa_lote_id UUID NOT NULL, \n\tcantidad INTEGER NOT NULL, \n\treintegrar_stock BOOLEAN NOT NULL, \n\tmotivo_condicion VARCHAR(250) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_reversa_lote UNIQUE (reversa_id, venta_lote_id), \n\tCONSTRAINT ck_reversa_detalle CHECK (cantidad > 0 AND btrim(motivo_condicion) <> ''), \n\tFOREIGN KEY(reversa_id) REFERENCES reversa_venta (id) ON DELETE RESTRICT, \n\tFOREIGN KEY(venta_lote_id) REFERENCES venta_lote (id) ON DELETE RESTRICT\n)"
    )


def downgrade():
    op.drop_table("reversa_venta_detalle")
    op.drop_table("reversa_venta")
