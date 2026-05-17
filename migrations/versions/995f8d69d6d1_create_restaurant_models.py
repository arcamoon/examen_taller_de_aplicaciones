"""crear tablas principales

Revision ID: 995f8d69d6d1
Revises:
Create Date: 2026-05-17 12:36:19.327507

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "995f8d69d6d1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "categoria_plato",
        sa.Column("id_categoria", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id_categoria"),
    )
    op.create_index(
        op.f("ix_categoria_plato_nombre"),
        "categoria_plato",
        ["nombre"],
        unique=True,
    )

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

    op.create_table(
        "plato",
        sa.Column("id_plato", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("precio_unitario", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("disponible", sa.Boolean(), nullable=False),
        sa.Column("imagen", sa.Text(), nullable=True),
        sa.Column("cantidad_disponible", sa.Integer(), nullable=False),
        sa.Column("id_categoria", sa.Integer(), nullable=False),
        sa.CheckConstraint("cantidad_disponible >= 0", name="ck_plato_cantidad"),
        sa.CheckConstraint("precio_unitario >= 0", name="ck_plato_precio"),
        sa.ForeignKeyConstraint(
            ["id_categoria"],
            ["categoria_plato.id_categoria"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id_plato"),
    )
    op.create_index("ix_plato_id_categoria", "plato", ["id_categoria"], unique=False)

    op.create_table(
        "reserva",
        sa.Column("id_reserva", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("fecha", sa.DateTime(), nullable=False),
        sa.Column("estado", sa.Integer(), nullable=False),
        sa.Column("cantidad_personas", sa.Integer(), nullable=False),
        sa.Column("total_reserva", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.CheckConstraint("cantidad_personas > 0", name="ck_reserva_cantidad_personas"),
        sa.CheckConstraint("estado IN (0, 1, 2, 3)", name="ck_reserva_estado"),
        sa.CheckConstraint("total_reserva >= 0", name="ck_reserva_total"),
        sa.ForeignKeyConstraint(["id_usuario"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id_reserva"),
    )
    op.create_index("ix_reserva_id_usuario", "reserva", ["id_usuario"], unique=False)

    op.create_table(
        "detalle_reserva",
        sa.Column("id_detalle", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("id_reserva", sa.Integer(), nullable=False),
        sa.Column("id_plato", sa.Integer(), nullable=False),
        sa.CheckConstraint("cantidad > 0", name="ck_detalle_reserva_cantidad"),
        sa.CheckConstraint("precio_unitario >= 0", name="ck_detalle_reserva_precio"),
        sa.CheckConstraint("subtotal >= 0", name="ck_detalle_reserva_subtotal"),
        sa.ForeignKeyConstraint(["id_plato"], ["plato.id_plato"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["id_reserva"],
            ["reserva.id_reserva"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id_detalle"),
    )
    op.create_index(
        "ix_detalle_reserva_id_plato",
        "detalle_reserva",
        ["id_plato"],
        unique=False,
    )
    op.create_index(
        "ix_detalle_reserva_id_reserva",
        "detalle_reserva",
        ["id_reserva"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_detalle_reserva_id_reserva", table_name="detalle_reserva")
    op.drop_index("ix_detalle_reserva_id_plato", table_name="detalle_reserva")
    op.drop_table("detalle_reserva")

    op.drop_index("ix_reserva_id_usuario", table_name="reserva")
    op.drop_table("reserva")

    op.drop_index("ix_plato_id_categoria", table_name="plato")
    op.drop_table("plato")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    postgresql.ENUM("cliente", "cajero", "admin", name="user_role").drop(
        op.get_bind(),
        checkfirst=True,
    )

    op.drop_index(op.f("ix_categoria_plato_nombre"), table_name="categoria_plato")
    op.drop_table("categoria_plato")
