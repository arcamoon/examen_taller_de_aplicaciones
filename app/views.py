import base64
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_appbuilder import ModelView
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_login import current_user, login_required, login_user
from markupsafe import Markup
from wtforms import DateTimeLocalField, FileField
from wtforms.validators import DataRequired

from app import appbuilder, db
from app.crypto import decrypt_id, encrypt_id
from app.models import CategoriaPlato, DetalleReserva, Plato, Reserva

"""
    Create your Model based REST API::

    class MyModelApi(ModelRestApi):
        datamodel = SQLAInterface(MyModel)

    appbuilder.add_api(MyModelApi)


    Create your Views::


    class MyModelView(ModelView):
        datamodel = SQLAInterface(MyModel)


    Next, register your Views on create_app Flask factory::


    appbuilder.add_view(
        MyModelView,
        "My View",
        icon="fa-folder-open-o",
        category="My Category",
        category_icon='fa-envelope'
    )
"""

"""
    Application wide 404 error handler
"""


class CategoriaPlatoModelView(ModelView):
    datamodel = SQLAInterface(CategoriaPlato)

    list_title = "Categorias de platos"
    show_title = "Detalle de categoria"
    add_title = "Crear categoria"
    edit_title = "Editar categoria"

    list_columns = ["nombre", "descripcion"]
    show_columns = ["id_categoria", "nombre", "descripcion", "platos"]
    add_columns = ["nombre", "descripcion"]
    edit_columns = ["nombre", "descripcion"]
    search_columns = ["nombre", "descripcion"]
    order_columns = ["nombre"]


class PlatoModelView(ModelView):
    datamodel = SQLAInterface(Plato)

    list_title = "Platos"
    show_title = "Detalle de plato"
    add_title = "Crear plato"
    edit_title = "Editar plato"

    list_columns = [
        "imagen",
        "nombre",
        "categoria",
        "precio_unitario",
        "disponible",
        "cantidad_disponible",
    ]
    show_columns = [
        "id_plato",
        "nombre",
        "descripcion",
        "precio_unitario",
        "disponible",
        "imagen",
        "cantidad_disponible",
        "categoria",
    ]
    add_columns = [
        "nombre",
        "descripcion",
        "precio_unitario",
        "disponible",
        "imagen_archivo",
        "cantidad_disponible",
        "categoria",
    ]
    edit_columns = add_columns
    search_columns = ["nombre", "descripcion", "categoria"]
    order_columns = ["nombre", "precio_unitario", "cantidad_disponible"]
    add_form_extra_fields = {
        "imagen_archivo": FileField("Imagen"),
    }
    edit_form_extra_fields = {
        "imagen_archivo": FileField("Imagen"),
    }
    formatters_columns = {
        "imagen": lambda value: Markup(
            f'<img src="{value}" alt="plato" style="width:72px;height:54px;object-fit:cover;border-radius:6px;">'
        )
        if value
        else "",
    }

    def pre_add(self, item):
        self._store_uploaded_image(item)

    def pre_update(self, item):
        self._store_uploaded_image(item)

    @staticmethod
    def _store_uploaded_image(item):
        image_file = request.files.get("imagen_archivo")
        if not image_file or not image_file.filename:
            return

        if image_file.mimetype not in {"image/jpeg", "image/png", "image/webp"}:
            abort(400, "Solo se aceptan imagenes JPG, PNG o WEBP.")

        raw_image = image_file.read()
        item.imagen = (
            f"data:{image_file.mimetype};base64,"
            f"{base64.b64encode(raw_image).decode('utf-8')}"
        )


class DetalleReservaModelView(ModelView):
    datamodel = SQLAInterface(DetalleReserva)
    include_route_methods = {"list", "show"}


class ReservaModelView(ModelView):
    datamodel = SQLAInterface(Reserva)

    related_views = [DetalleReservaModelView]
    list_columns = [
        "fecha",
        "estado",
        "cantidad_personas",
        "total_reserva",
        "usuario",
    ]
    show_columns = [
        "id_reserva",
        "fecha",
        "estado",
        "cantidad_personas",
        "total_reserva",
        "usuario",
        "detalles",
    ]
    add_columns = [
        "fecha",
        "estado",
        "cantidad_personas",
        "total_reserva",
        "usuario",
    ]
    edit_columns = add_columns
    search_columns = ["estado", "usuario"]
    order_columns = ["fecha", "estado", "total_reserva"]
    add_form_extra_fields = {
        "fecha": DateTimeLocalField(
            "Fecha y hora",
            format="%Y-%m-%dT%H:%M",
            validators=[DataRequired()],
        ),
    }
    edit_form_extra_fields = add_form_extra_fields


appbuilder.add_view(
    CategoriaPlatoModelView,
    "Categorias",
    icon="fa-tags",
    category="Restaurante",
    category_icon="fa-cutlery",
)
appbuilder.add_view(
    PlatoModelView,
    "Platos",
    icon="fa-cutlery",
    category="Restaurante",
)

appbuilder.add_view(
    ReservaModelView,
    "Reservas",
    icon="fa-calendar",
    category="Reservaciones",
)

appbuilder.add_view(
    DetalleReservaModelView,
    "Detalles de reserva",
    icon="fa-list",
    category="Reservaciones",
)


def _current_role_names():
    return {role.name for role in getattr(current_user, "roles", [])}


def _is_cliente():
    return current_user.is_authenticated and "cliente" in _current_role_names()


def _require_cliente():
    if not current_user.is_authenticated:
        return redirect(url_for("login_cliente"))
    if not _is_cliente():
        abort(403)
    return None


def _catalogo_response():
    categorias = (
        CategoriaPlato.query.join(CategoriaPlato.platos)
        .filter(Plato.disponible.is_(True))
        .order_by(CategoriaPlato.nombre.asc(), Plato.nombre.asc())
        .all()
    )

    for categoria in categorias:
        for plato in categoria.platos:
            plato.public_id = encrypt_id(plato.id_plato)

    return render_template("catalogo.html", categorias=categorias)


@current_app.before_request
def block_cliente_from_appbuilder_panel():
    if not _is_cliente():
        return None

    allowed_prefixes = (
        "/cliente/",
        "/catalogo/",
        "/api/catalogo/",
        "/static/",
        "/logout/",
    )
    allowed_paths = {
        "/cliente",
        "/catalogo",
        "/login-cliente/",
        "/login-personal/",
    }

    if request.path in allowed_paths or request.path.startswith(allowed_prefixes):
        return None

    return redirect(url_for("cliente"))


@current_app.route("/panel/")
def panel():
    if not current_user.is_authenticated:
        return redirect(url_for("AuthDBView.login", next=url_for("panel")))

    roles = _current_role_names()
    if roles.intersection({"Admin", "admin", "cajero"}):
        return redirect(url_for("ReservaModelView.list"))
    if "cliente" in roles:
        return redirect(url_for("cliente"))
    abort(403)


@current_app.route("/cliente/")
@login_required
def cliente():
    if "cliente" not in _current_role_names():
        abort(403)
    return _catalogo_response()


def cliente():
    required_response = _require_cliente()
    if required_response:
        return required_response
    return _catalogo_response()


@current_app.route("/cliente/reservas/")
def cliente_reservas():
    required_response = _require_cliente()
    if required_response:
        return required_response

    reservas = (
        Reserva.query.filter_by(id_usuario=current_user.id)
        .order_by(Reserva.fecha.desc())
        .all()
    )

    for reserva in reservas:
        reserva.public_id = encrypt_id(reserva.id_reserva)

    return render_template("cliente_reservas.html", reservas=reservas)


@current_app.post("/cliente/reservas/<plato_id>/crear/")
def cliente_crear_reserva(plato_id):
    required_response = _require_cliente()
    if required_response:
        return required_response

    try:
        id_plato = decrypt_id(plato_id)
        fecha = datetime.strptime(request.form["fecha"], "%Y-%m-%dT%H:%M")
        cantidad_personas = int(request.form["cantidad_personas"])
        cantidad = int(request.form["cantidad"])
    except (KeyError, TypeError, ValueError):
        flash("Los datos de la reserva no son validos.", "danger")
        return redirect(url_for("catalogo_detalle", plato_id=plato_id))

    if cantidad_personas <= 0 or cantidad <= 0:
        flash("La cantidad debe ser mayor a cero.", "danger")
        return redirect(url_for("catalogo_detalle", plato_id=plato_id))

    plato = Plato.query.filter_by(id_plato=id_plato, disponible=True).first_or_404()
    if plato.cantidad_disponible < cantidad:
        flash("No hay suficiente disponibilidad para ese plato.", "warning")
        return redirect(url_for("catalogo_detalle", plato_id=plato_id))

    try:
        precio_unitario = Decimal(plato.precio_unitario)
        subtotal = precio_unitario * Decimal(cantidad)
    except (InvalidOperation, TypeError):
        flash("El precio del plato no es valido.", "danger")
        return redirect(url_for("catalogo_detalle", plato_id=plato_id))

    reserva = Reserva(
        fecha=fecha,
        estado="pendiente",
        cantidad_personas=cantidad_personas,
        total_reserva=subtotal,
        id_usuario=current_user.id,
    )
    reserva.detalles.append(
        DetalleReserva(
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            subtotal=subtotal,
            id_plato=plato.id_plato,
        )
    )

    db.session.add(reserva)
    db.session.commit()

    flash("Reserva creada en estado pendiente.", "success")
    return redirect(url_for("cliente_reservas"))


@current_app.route("/catalogo/")
def catalogo():
    return _catalogo_response()


@current_app.route("/login-cliente/", methods=["GET", "POST"])
def login_cliente():
    if current_user.is_authenticated:
        if _is_cliente():
            return redirect(url_for("cliente"))
        return redirect(url_for("panel"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = appbuilder.sm.auth_user_db(username, password)

        if not user or "cliente" not in {role.name for role in user.roles}:
            flash("Credenciales invalidas para cliente.", "danger")
            return render_template("cliente_login.html")

        login_user(user)
        return redirect(url_for("cliente"))

    return render_template("cliente_login.html")


@current_app.route("/login-personal/")
def login_personal():
    return redirect(url_for("AuthDBView.login", next=url_for("panel")))


@current_app.route("/catalogo/<plato_id>/")
def catalogo_detalle(plato_id):
    try:
        id_plato = decrypt_id(plato_id)
    except Exception:
        abort(404)

    plato = Plato.query.filter_by(id_plato=id_plato, disponible=True).first_or_404()
    return render_template(
        "catalogo_detalle.html",
        plato=plato,
        plato_public_id=plato_id,
        puede_reservar=_is_cliente(),
    )


@current_app.route("/registrar_reserva/")
@login_required
def registrar_detalle_reserva():
    if "cajero" == current_user.roles[0].name:
        return abort(401)

    if request.method == "GET":
        platos = (
            Plato.query.filter(Plato.disponible.is_(True))
            .join(Plato.categoria)
            .order_by(CategoriaPlato.nombre.asc(), Plato.nombre.asc())
            .all()
        )

        return render_template("registrar_reserva.html", platos=platos)
    elif request.method == "POST":
        return render_template("registrar_reserva.html")
    else:
        abort(404)


@current_app.get("/api/catalogo/categorias/")
def api_catalogo_categorias():
    categorias = CategoriaPlato.query.order_by(CategoriaPlato.nombre.asc()).all()
    return jsonify(
        [
            {
                "id": encrypt_id(categoria.id_categoria),
                "nombre": categoria.nombre,
                "descripcion": categoria.descripcion,
            }
            for categoria in categorias
        ]
    )


@current_app.get("/api/catalogo/platos/")
def api_catalogo_platos():
    platos = (
        Plato.query.filter(Plato.disponible.is_(True))
        .join(Plato.categoria)
        .order_by(CategoriaPlato.nombre.asc(), Plato.nombre.asc())
        .all()
    )
    return jsonify([_serialize_plato(plato) for plato in platos])


@current_app.get("/api/catalogo/platos/<plato_id>/")
def api_catalogo_plato_detalle(plato_id):
    try:
        id_plato = decrypt_id(plato_id)
    except Exception:
        abort(404)

    plato = Plato.query.filter_by(id_plato=id_plato, disponible=True).first_or_404()
    return jsonify(_serialize_plato(plato))


def _serialize_plato(plato):
    return {
        "id": encrypt_id(plato.id_plato),
        "nombre": plato.nombre,
        "descripcion": plato.descripcion,
        "precio_unitario": str(plato.precio_unitario),
        "disponible": plato.disponible,
        "imagen": plato.imagen,
        "cantidad_disponible": plato.cantidad_disponible,
        "categoria": {
            "id": encrypt_id(plato.categoria.id_categoria),
            "nombre": plato.categoria.nombre,
        },
    }


@current_app.errorhandler(404)
def page_not_found(e):
    return (
        render_template(
            "404.html", base_template=appbuilder.base_template, appbuilder=appbuilder
        ),
        404,
    )
