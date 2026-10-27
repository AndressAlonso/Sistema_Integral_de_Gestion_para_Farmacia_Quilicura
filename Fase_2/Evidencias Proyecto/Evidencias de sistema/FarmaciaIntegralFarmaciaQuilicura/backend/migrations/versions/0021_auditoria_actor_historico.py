"""E9-H2: conservar identidad histórica sin impedir eliminar la cuenta."""
import sqlalchemy as sa
from alembic import op

revision = "0021_auditoria_actor_historico"
down_revision = "0020_preparacion_pedidos"
branch_labels = None
depends_on = None


def upgrade():
    # Solo durante esta migración transaccional; la protección se restaura antes del commit.
    op.execute("ALTER TABLE evento_auditoria DISABLE TRIGGER trg_auditoria_inmutable")
    op.execute("""UPDATE evento_auditoria e SET datos_cambio = e.datos_cambio ||
        jsonb_build_object('usuario_nombre', COALESCE(
            e.datos_cambio->>'usuario_nombre', e.datos_cambio->>'user_name', u.nombre),
            'nombre_recuperado_en_migracion', NOT (e.datos_cambio ? 'usuario_nombre' OR e.datos_cambio ? 'user_name'))
        FROM usuario_interno u WHERE e.usuario_id = u.id
        AND NOT (e.datos_cambio ? 'usuario_nombre')""")
    op.execute("ALTER TABLE evento_auditoria ENABLE TRIGGER trg_auditoria_inmutable")
    for fk in sa.inspect(op.get_bind()).get_foreign_keys("evento_auditoria"):
        if fk["constrained_columns"] == ["usuario_id"]:
            op.drop_constraint(fk["name"], "evento_auditoria", type_="foreignkey")


def downgrade():
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM evento_auditoria e LEFT JOIN usuario_interno u
            ON e.usuario_id = u.id WHERE e.usuario_id IS NOT NULL AND u.id IS NULL) THEN
            RAISE EXCEPTION 'No se puede revertir: existen responsables históricos eliminados.';
        END IF;
    END $$""")
    op.create_foreign_key("evento_auditoria_usuario_id_fkey", "evento_auditoria",
                         "usuario_interno", ["usuario_id"], ["id"], ondelete="RESTRICT")
