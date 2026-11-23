"""E4-H5: clasificar motivos sin alterar el historial existente."""
import sqlalchemy as sa
from alembic import op

revision = "0025_motivo_ajuste"
down_revision = "0024_codigo_manual_retiro"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("ajuste_inventario", sa.Column("tipo_motivo", sa.String(20), nullable=True))
    op.create_check_constraint("ck_ajuste_tipo_motivo", "ajuste_inventario", "tipo_motivo IS NULL OR tipo_motivo IN ('CONTEO','DANADO','VENCIMIENTO','OTRO')")

def downgrade():
    op.drop_constraint("ck_ajuste_tipo_motivo", "ajuste_inventario", type_="check")
    op.drop_column("ajuste_inventario", "tipo_motivo")
