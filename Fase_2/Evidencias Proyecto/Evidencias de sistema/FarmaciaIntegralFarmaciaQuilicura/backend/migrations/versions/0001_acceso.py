"""E1-H1: base de acceso del modelo de clases v2.

Incluye soporte de roles y sucursal; no completa E1-H2 a E1-H5.
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_acceso"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sucursal",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("codigo", sa.String(30), nullable=False, unique=True),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("direccion_local", sa.String(250), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.CheckConstraint("btrim(codigo) <> ''", name="ck_sucursal_codigo"),
        sa.CheckConstraint("btrim(nombre) <> ''", name="ck_sucursal_nombre"),
    )
    op.create_table(
        "rol",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("codigo", sa.String(60), nullable=False, unique=True),
        sa.Column("nombre", sa.String(100), nullable=False),
    )
    op.create_table(
        "permiso",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("codigo", sa.String(100), nullable=False, unique=True),
        sa.Column("descripcion", sa.String(250), nullable=False),
    )
    op.create_table(
        "usuario_interno",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("correo", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column(
            "sucursal_id",
            sa.Uuid(),
            sa.ForeignKey("sucursal.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.CheckConstraint("btrim(nombre) <> ''", name="ck_usuario_nombre"),
        sa.CheckConstraint("correo = lower(btrim(correo))", name="ck_usuario_correo_normalizado"),
    )
    op.create_index("ix_usuario_interno_sucursal_id", "usuario_interno", ["sucursal_id"])
    op.create_table(
        "usuario_rol",
        sa.Column(
            "usuario_id",
            sa.Uuid(),
            sa.ForeignKey("usuario_interno.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "rol_id", sa.Uuid(), sa.ForeignKey("rol.id", ondelete="RESTRICT"), primary_key=True
        ),
    )
    op.create_table(
        "rol_permiso",
        sa.Column(
            "rol_id", sa.Uuid(), sa.ForeignKey("rol.id", ondelete="RESTRICT"), primary_key=True
        ),
        sa.Column(
            "permiso_id",
            sa.Uuid(),
            sa.ForeignKey("permiso.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )
    op.create_table(
        "sesion_interna",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "usuario_id",
            sa.Uuid(),
            sa.ForeignKey("usuario_interno.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocada_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("expira_en > creada_en", name="ck_sesion_expiracion"),
        sa.CheckConstraint(
            "revocada_en IS NULL OR revocada_en >= creada_en", name="ck_sesion_revocacion"
        ),
    )
    op.create_index("ix_sesion_interna_usuario_id", "sesion_interna", ["usuario_id"])


def downgrade():
    op.drop_table("sesion_interna")
    op.drop_table("rol_permiso")
    op.drop_table("usuario_rol")
    op.drop_table("usuario_interno")
    op.drop_table("permiso")
    op.drop_table("rol")
    op.drop_table("sucursal")
