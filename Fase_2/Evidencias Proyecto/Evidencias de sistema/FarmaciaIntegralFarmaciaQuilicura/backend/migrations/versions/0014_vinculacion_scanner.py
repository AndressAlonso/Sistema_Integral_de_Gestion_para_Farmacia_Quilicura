"""E8-H1: vinculación temporal del móvil con una pantalla POS."""

import sqlalchemy as sa
from alembic import op

revision = "0014_vinculacion_scanner"
down_revision = "0013_reversas_venta"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vinculacion_scanner",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("sucursal_id", sa.Uuid(), nullable=False),
        sa.Column("sesion_caja_id", sa.Uuid(), nullable=False),
        sa.Column("sesion_web_id", sa.Uuid(), nullable=False),
        sa.Column("sesion_movil_id", sa.Uuid(), nullable=True),
        sa.Column("codigo_hash", sa.String(64), nullable=False),
        sa.Column(
            "creada_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "qr_expira_en",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "expira_en",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "vinculada_en",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "revocada_en",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario_interno.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sucursal_id"],
            ["sucursal.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sesion_caja_id"],
            ["sesion_caja.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sesion_web_id"],
            ["sesion_interna.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sesion_movil_id"],
            ["sesion_interna.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "codigo_hash",
            name="uq_scanner_codigo_hash",
        ),
        sa.CheckConstraint(
            "qr_expira_en > creada_en AND expira_en >= qr_expira_en",
            name="ck_scanner_expiracion",
        ),
        sa.CheckConstraint(
            "(vinculada_en IS NULL AND sesion_movil_id IS NULL) OR "
            "(vinculada_en IS NOT NULL AND sesion_movil_id IS NOT NULL "
            "AND vinculada_en >= creada_en AND vinculada_en < qr_expira_en)",
            name="ck_scanner_vinculacion",
        ),
        sa.CheckConstraint(
            "revocada_en IS NULL OR revocada_en >= creada_en",
            name="ck_scanner_revocacion",
        ),
        sa.CheckConstraint(
            "sesion_movil_id IS NULL OR sesion_movil_id <> sesion_web_id",
            name="ck_scanner_sesiones_distintas",
        ),
    )

    op.create_index(
        "ix_scanner_caja",
        "vinculacion_scanner",
        ["sesion_caja_id"],
    )
    op.create_index(
        "ix_scanner_sesion_web",
        "vinculacion_scanner",
        ["sesion_web_id"],
    )
    op.create_index(
        "ix_scanner_sesion_movil",
        "vinculacion_scanner",
        ["sesion_movil_id"],
    )


def downgrade():
    op.drop_index(
        "ix_scanner_sesion_movil",
        table_name="vinculacion_scanner",
    )
    op.drop_index(
        "ix_scanner_sesion_web",
        table_name="vinculacion_scanner",
    )
    op.drop_index(
        "ix_scanner_caja",
        table_name="vinculacion_scanner",
    )
    op.drop_table("vinculacion_scanner")