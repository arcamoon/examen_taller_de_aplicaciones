"""use estado reserva enum

Revision ID: f2a10d4c7b8e
Revises: d46efa4b064c
Create Date: 2026-05-17 17:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "f2a10d4c7b8e"
down_revision = "d46efa4b064c"
branch_labels = None
depends_on = None


estado_reserva = postgresql.ENUM(
    "pendiente",
    "aprobado",
    "completado",
    "cancelado",
    name="estado_reserva",
)


def upgrade():
    bind = op.get_bind()
    estado_reserva.create(bind, checkfirst=True)

    with op.batch_alter_table("reserva", schema=None) as batch_op:
        batch_op.drop_constraint("ck_reserva_estado", type_="check")

    op.execute(
        """
        ALTER TABLE reserva
        ALTER COLUMN estado TYPE estado_reserva
        USING (
            CASE estado
                WHEN 0 THEN 'pendiente'
                WHEN 1 THEN 'aprobado'
                WHEN 2 THEN 'completado'
                WHEN 3 THEN 'cancelado'
                ELSE 'pendiente'
            END
        )::estado_reserva
        """
    )
    op.execute("ALTER TABLE reserva ALTER COLUMN estado SET DEFAULT 'pendiente'")


def downgrade():
    op.execute("ALTER TABLE reserva ALTER COLUMN estado DROP DEFAULT")
    op.execute(
        """
        ALTER TABLE reserva
        ALTER COLUMN estado TYPE integer
        USING (
            CASE estado::text
                WHEN 'pendiente' THEN 0
                WHEN 'aprobado' THEN 1
                WHEN 'completado' THEN 2
                WHEN 'cancelado' THEN 3
                ELSE 0
            END
        )
        """
    )

    with op.batch_alter_table("reserva", schema=None) as batch_op:
        batch_op.create_check_constraint(
            "ck_reserva_estado",
            "estado IN (0, 1, 2, 3)",
        )

    estado_reserva.drop(op.get_bind(), checkfirst=True)
