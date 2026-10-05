"""E2-H1: referencia opcional a la imagen principal del producto."""

import sqlalchemy as sa
from alembic import op

revision = "0003_producto_imagen"
down_revision = "0002_catalogo"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("producto", sa.Column("image_key", sa.String(40), nullable=True))


def downgrade():
    op.drop_column("producto", "image_key")
