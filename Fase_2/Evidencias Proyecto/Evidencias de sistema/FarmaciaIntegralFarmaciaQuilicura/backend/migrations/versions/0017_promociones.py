"""E2-H3: tabla aditiva de promociones; no altera datos existentes."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0017_promociones"
down_revision = "0016_merge_e6_e8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("promocion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column("inicia_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("termina_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("producto_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("producto.id", ondelete="RESTRICT")),
        sa.Column("categoria_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categoria.id", ondelete="RESTRICT")),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("btrim(nombre) <> ''", name="ck_promocion_nombre"),
        sa.CheckConstraint("tipo IN ('PERCENT', 'FIXED_PRICE')", name="ck_promocion_tipo"),
        sa.CheckConstraint("valor >= 0 AND valor < 1000000000000 AND (tipo <> 'PERCENT' OR valor <= 100)", name="ck_promocion_valor"),
        sa.CheckConstraint("termina_en > inicia_en", name="ck_promocion_vigencia"),
        sa.CheckConstraint("(producto_id IS NULL) <> (categoria_id IS NULL)", name="ck_promocion_destino"))
    op.create_index("ix_promocion_producto_id", "promocion", ["producto_id"])
    op.create_index("ix_promocion_categoria_id", "promocion", ["categoria_id"])


def downgrade():
    # Operación explícita: elimina únicamente la tabla introducida por esta revisión.
    op.drop_index("ix_promocion_categoria_id", table_name="promocion")
    op.drop_index("ix_promocion_producto_id", table_name="promocion")
    op.drop_table("promocion")
