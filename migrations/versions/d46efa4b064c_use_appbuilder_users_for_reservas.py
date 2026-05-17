"""use appbuilder users for reservas

Revision ID: d46efa4b064c
Revises: 995f8d69d6d1
Create Date: 2026-05-17 17:20:50.426768

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "d46efa4b064c"
down_revision = "995f8d69d6d1"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()

    users_count = connection.execute(sa.text("select count(*) from users")).scalar()
    reservas_count = connection.execute(sa.text("select count(*) from reserva")).scalar()
    if users_count or reservas_count:
        raise RuntimeError(
            "La migracion a ab_user necesita una estrategia de datos: "
            "existen registros en users o reserva."
        )

    with op.batch_alter_table("reserva", schema=None) as batch_op:
        batch_op.drop_constraint("reserva_id_usuario_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "reserva_id_usuario_ab_user_fkey",
            "ab_user",
            ["id_usuario"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_email"))
        batch_op.drop_index(batch_op.f("ix_users_username"))

    op.drop_table("users")
    postgresql.ENUM("cliente", "cajero", "admin", name="user_role").drop(
        op.get_bind(),
        checkfirst=True,
    )


def downgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("cliente", "cajero", "admin", name="user_role"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    with op.batch_alter_table("reserva", schema=None) as batch_op:
        batch_op.drop_constraint(
            "reserva_id_usuario_ab_user_fkey",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "reserva_id_usuario_fkey",
            "users",
            ["id_usuario"],
            ["id"],
            ondelete="CASCADE",
        )
