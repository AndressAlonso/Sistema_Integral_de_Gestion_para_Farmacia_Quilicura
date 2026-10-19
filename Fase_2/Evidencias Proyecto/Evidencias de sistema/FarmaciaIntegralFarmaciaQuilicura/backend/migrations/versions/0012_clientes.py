"""E6-H2: clientes y sesiones independientes del personal interno."""
import sqlalchemy as sa
from alembic import op

revision = "0012_clientes"
down_revision = "0011_evento_auditoria"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cliente",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("correo", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("correo", name="cliente_correo_key"),
        sa.CheckConstraint("btrim(nombre) <> ''", name="ck_cliente_nombre"),
        sa.CheckConstraint("correo = lower(btrim(correo)) AND correo <> ''", name="ck_cliente_correo_normalizado"),
        sa.CheckConstraint("password_hash LIKE '$argon2id$%'", name="ck_cliente_hash_argon2"),
    )
    op.create_table(
        "sesion_cliente",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("cliente_id", sa.Uuid(), sa.ForeignKey("cliente.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocada_en", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("token_hash", name="sesion_cliente_token_hash_key"),
        sa.CheckConstraint("expira_en > creada_en", name="ck_sesion_cliente_expiracion"),
        sa.CheckConstraint("revocada_en IS NULL OR revocada_en >= creada_en", name="ck_sesion_cliente_revocacion"),
    )
    op.create_index("ix_sesion_cliente_cliente_id", "sesion_cliente", ["cliente_id"], unique=False)


def downgrade():
    op.drop_table("sesion_cliente")
    op.drop_table("cliente")
