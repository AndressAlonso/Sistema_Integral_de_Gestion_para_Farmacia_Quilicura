"""E8-H1: registro de lecturas del escáner vinculadas al POS."""

import sqlalchemy as sa
from alembic import op

revision = "0015_lectura_scanner"
down_revision = "0014_vinculacion_scanner"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "lectura_scanner",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "secuencia",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column(
            "vinculacion_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "codigo",
            sa.String(128),
            nullable=False,
        ),
        sa.Column(
            "producto_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "resultado",
            sa.String(20),
            nullable=False,
        ),
        sa.Column(
            "creada_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "recibida_pos_en",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "secuencia",
            name="uq_lectura_scanner_secuencia",
        ),
        sa.ForeignKeyConstraint(
            ["vinculacion_id"],
            ["vinculacion_scanner.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["producto_id"],
            ["producto.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "btrim(codigo) <> '' AND codigo = btrim(codigo)",
            name="ck_lectura_scanner_codigo",
        ),
        sa.CheckConstraint(
            "resultado IN ('FOUND', 'NOT_FOUND', 'INACTIVE')",
            name="ck_lectura_scanner_resultado",
        ),
        sa.CheckConstraint(
            "(resultado = 'NOT_FOUND' AND producto_id IS NULL) OR "
            "(resultado IN ('FOUND', 'INACTIVE') "
            "AND producto_id IS NOT NULL)",
            name="ck_lectura_scanner_producto",
        ),
        sa.CheckConstraint(
            "recibida_pos_en IS NULL OR recibida_pos_en >= creada_en",
            name="ck_lectura_scanner_recepcion",
        ),
    )

    op.create_index(
        "ix_lectura_scanner_vinculacion_secuencia",
        "lectura_scanner",
        ["vinculacion_id", "secuencia"],
    )
    op.create_index(
        "ix_lectura_scanner_producto",
        "lectura_scanner",
        ["producto_id"],
    )


def downgrade():
    op.drop_index(
        "ix_lectura_scanner_producto",
        table_name="lectura_scanner",
    )
    op.drop_index(
        "ix_lectura_scanner_vinculacion_secuencia",
        table_name="lectura_scanner",
    )
    op.drop_table("lectura_scanner")