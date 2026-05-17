from app import db
from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index
from sqlalchemy.orm import relationship


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), nullable=False, unique=True, index=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(
        Enum("cliente", "cajero", "admin", name="user_role"),
        nullable=False,
        default="cliente",
    )
    active = db.Column(db.Boolean, nullable=False, default=True)

    reservas = relationship(
        "Reserva",
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return self.username


class Reserva(db.Model):
    __tablename__ = "reserva"
    __table_args__ = (
        CheckConstraint("cantidad_personas > 0", name="ck_reserva_cantidad_personas"),
        CheckConstraint("total_reserva >= 0", name="ck_reserva_total"),
        Index("ix_reserva_id_usuario", "id_usuario"),
    )

    id_reserva = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fecha = db.Column(db.DateTime, nullable=False)
    estado = db.Column(
        Enum("pendiente", "aprobado", "completado", "cancelado", name="estado_reserva"),
        nullable=False,
        default="pendiente",
    )
    cantidad_personas = db.Column(db.Integer, nullable=False)
    total_reserva = db.Column(db.Numeric(10, 2), nullable=False)
    id_usuario = db.Column(
        db.Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    usuario = relationship("User", back_populates="reservas")
    detalles = relationship(
        "DetalleReserva",
        back_populates="reserva",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"Reserva #{self.id_reserva}"


class DetalleReserva(db.Model):
    __tablename__ = "detalle_reserva"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_detalle_reserva_cantidad"),
        CheckConstraint("precio_unitario >= 0", name="ck_detalle_reserva_precio"),
        CheckConstraint("subtotal >= 0", name="ck_detalle_reserva_subtotal"),
        Index("ix_detalle_reserva_id_reserva", "id_reserva"),
        Index("ix_detalle_reserva_id_plato", "id_plato"),
    )

    id_detalle = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    id_reserva = db.Column(
        db.Integer,
        ForeignKey("reserva.id_reserva", ondelete="CASCADE"),
        nullable=False,
    )
    id_plato = db.Column(
        db.Integer,
        ForeignKey("plato.id_plato", ondelete="RESTRICT"),
        nullable=False,
    )

    reserva = relationship("Reserva", back_populates="detalles")
    plato = relationship("Plato", back_populates="detalles")

    def __repr__(self) -> str:
        return f"Detalle #{self.id_detalle}"


class Plato(db.Model):
    __tablename__ = "plato"
    __table_args__ = (
        CheckConstraint("precio_unitario >= 0", name="ck_plato_precio"),
        CheckConstraint("cantidad_disponible >= 0", name="ck_plato_cantidad"),
        Index("ix_plato_id_categoria", "id_categoria"),
    )

    id_plato = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    disponible = db.Column(db.Boolean, nullable=False, default=True)
    imagen = db.Column(db.Text)
    cantidad_disponible = db.Column(db.Integer, nullable=False, default=0)
    id_categoria = db.Column(
        db.Integer,
        ForeignKey("categoria_plato.id_categoria", ondelete="RESTRICT"),
        nullable=False,
    )

    categoria = relationship("CategoriaPlato", back_populates="platos")
    detalles = relationship("DetalleReserva", back_populates="plato")

    def __repr__(self) -> str:
        return self.nombre


class CategoriaPlato(db.Model):
    __tablename__ = "categoria_plato"

    id_categoria = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(120), nullable=False, unique=True, index=True)
    descripcion = db.Column(db.Text)

    platos = relationship("Plato", back_populates="categoria")

    def __repr__(self) -> str:
        return self.nombre
