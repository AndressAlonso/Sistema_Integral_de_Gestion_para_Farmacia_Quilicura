"""E2-H2: estructura para auditoría e historial de precios."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_evento_auditoria"
down_revision = "0010_ajustes_inventario"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "evento_auditoria",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "secuencia",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column(
            "ocurrido_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("origen_actor", sa.String(40), nullable=False),
        sa.Column("accion", sa.String(100), nullable=False),
        sa.Column("referencia_historica", sa.Text(), nullable=False),
        sa.Column("datos_cambio", postgresql.JSONB(), nullable=False),
        sa.Column(
            "usuario_id",
            sa.Uuid(),
            sa.ForeignKey("usuario_interno.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "sucursal_id",
            sa.Uuid(),
            sa.ForeignKey("sucursal.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "producto_id",
            sa.Uuid(),
            sa.ForeignKey("producto.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "secuencia",
            name="uq_evento_auditoria_secuencia",
        ),
        sa.CheckConstraint(
            "btrim(origen_actor) <> ''",
            name="ck_auditoria_origen",
        ),
        sa.CheckConstraint(
            "btrim(accion) <> ''",
            name="ck_auditoria_accion",
        ),
        sa.CheckConstraint(
            "btrim(referencia_historica) <> ''",
            name="ck_auditoria_referencia",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(datos_cambio) = 'object'",
            name="ck_auditoria_datos_objeto",
        ),
    )

    op.create_index(
        "ix_auditoria_producto_secuencia",
        "evento_auditoria",
        ["producto_id", "secuencia"],
    )
    op.create_index(
        "ix_auditoria_usuario",
        "evento_auditoria",
        ["usuario_id"],
    )
    op.create_index(
        "ix_auditoria_sucursal",
        "evento_auditoria",
        ["sucursal_id"],
    )

    op.execute("""
        CREATE FUNCTION sigfq_auditoria_inmutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Los eventos de auditoria no se pueden modificar ni borrar.'
                USING ERRCODE = '55000';
        END;
        $$;
    """)

    op.execute("""
        CREATE TRIGGER trg_auditoria_inmutable
        BEFORE UPDATE OR DELETE ON evento_auditoria
        FOR EACH ROW EXECUTE FUNCTION sigfq_auditoria_inmutable();
    """)

    op.execute("""
        CREATE TRIGGER trg_auditoria_no_truncate
        BEFORE TRUNCATE ON evento_auditoria
        FOR EACH STATEMENT EXECUTE FUNCTION sigfq_auditoria_inmutable();
    """)


def downgrade():
    op.drop_table("evento_auditoria")
    op.execute("DROP FUNCTION sigfq_auditoria_inmutable()")