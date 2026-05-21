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
from flask_appbuilder import BaseView, ModelView, expose
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder.security.sqla.models import Role, User as AppBuilderUser
from flask_login import current_user, login_required, login_user
from markupsafe import Markup
from wtforms import DateTimeLocalField, FileField
from wtforms.validators import DataRequired

from app import appbuilder, db
from app.crypto import decrypt_id, encrypt_id
from app.models import CategoriaPlato, DetalleReserva, Plato, Reserva
from app.services.AiService import preguntar_ia

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


class AIView(BaseView):
    route_base = "/ai"

    @expose("/chat", methods=["GET", "POST"])
    def chat(self):
        respuesta = None
        mensaje = ""

        if request.method == "POST":
            mensaje = request.form.get("message")
            if mensaje:
                respuesta = preguntar_ia(mensaje)

        return self.render_template(
            "ai_chat.html", respuesta=respuesta, mensaje=mensaje
        )


appbuilder.add_view_no_menu(AIView, "IA Chat")

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


@current_app.route("/cliente/registrar_reserva/", methods=["GET", "POST"])
@login_required
def registrar_detalle_reserva():
    if "cliente" != current_user.roles[0].name:
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
        fecha = request.form.get("fecha_reserva")

        hora = request.form.get("hora_reserva")
        cantidad_personas = request.form.get("cantidad_personas")

        fecha_hora = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")

        # 🔥 crear reserva base
        reserva = Reserva(
            fecha=fecha_hora,
            cantidad_personas=cantidad_personas,
            total_reserva=Decimal("0.00"),
            estado="pendiente",
            id_usuario=current_user.id,
        )

        db.session.add(reserva)
        db.session.flush()  # 👈 necesario para obtener id_reserva

        total = Decimal("0.00")

        # =========================
        # DETALLES (dinámicos)
        # =========================

        # request.form trae:
        # platos = [1,2,3,...]
        platos_ids = request.form.getlist("platos")

        for id_plato in platos_ids:
            cantidad = request.form.get(f"cantidad_{id_plato}")

            plato = Plato.query.get(id_plato)

            if not plato:
                continue

            # 🚫 VALIDACIÓN STOCK (backend obligatorio)
            if int(cantidad) > plato.cantidad_disponible:
                db.session.rollback()
                return f"Stock insuficiente para {plato.nombre}", 400

            subtotal = Decimal(plato.precio_unitario) * int(cantidad)
            total += subtotal

            detalle = DetalleReserva(
                cantidad=int(cantidad),
                precio_unitario=plato.precio_unitario,
                subtotal=subtotal,
                id_reserva=reserva.id_reserva,
                id_plato=plato.id_plato,
            )

            db.session.add(detalle)

            # opcional: descontar stock
            plato.cantidad_disponible -= int(cantidad)

        # =========================
        # FINALIZAR RESERVA
        # =========================

        reserva.total_reserva = total

        db.session.commit()

        return redirect("/registrar_reserva/")
    else:
        abort(404)


@current_app.route("/cajero/registrar_reserva/", methods=["GET", "POST"])
@login_required
def registrar_detalle_reserva_cajero():
    if "cajero" != current_user.roles[0].name:
        return abort(401)

    if request.method == "GET":
        usuarios = (
            db.session.query(User).join(User.roles).filter(Role.name == "cliente").all()
        )
        platos = (
            Plato.query.filter(Plato.disponible.is_(True))
            .join(Plato.categoria)
            .order_by(CategoriaPlato.nombre.asc(), Plato.nombre.asc())
            .all()
        )

        return render_template(
            "registrar_reserva_cajero.html", platos=platos, usuarios=usuarios
        )
    elif request.method == "POST":
        id_usuario = request.form.get("id_usuario")
        fecha = request.form.get("fecha_reserva")

        hora = request.form.get("hora_reserva")
        cantidad_personas = request.form.get("cantidad_personas")

        fecha_hora = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")

        # 🔥 crear reserva base
        reserva = Reserva(
            fecha=fecha_hora,
            cantidad_personas=cantidad_personas,
            total_reserva=Decimal("0.00"),
            estado="pendiente",
            id_usuario=int(id_usuario),
        )

        db.session.add(reserva)
        db.session.flush()  # 👈 necesario para obtener id_reserva

        total = Decimal("0.00")

        # =========================
        # DETALLES (dinámicos)
        # =========================

        # request.form trae:
        # platos = [1,2,3,...]
        platos_ids = request.form.getlist("platos")

        for id_plato in platos_ids:
            cantidad = request.form.get(f"cantidad_{id_plato}")

            plato = Plato.query.get(id_plato)

            if not plato:
                continue

            # 🚫 VALIDACIÓN STOCK (backend obligatorio)
            if int(cantidad) > plato.cantidad_disponible:
                db.session.rollback()
                return f"Stock insuficiente para {plato.nombre}", 400

            subtotal = Decimal(plato.precio_unitario) * int(cantidad)
            total += subtotal

            detalle = DetalleReserva(
                cantidad=int(cantidad),
                precio_unitario=plato.precio_unitario,
                subtotal=subtotal,
                id_reserva=reserva.id_reserva,
                id_plato=plato.id_plato,
            )

            db.session.add(detalle)

            # opcional: descontar stock
            plato.cantidad_disponible -= int(cantidad)

        # =========================
        # FINALIZAR RESERVA
        # =========================

        reserva.total_reserva = total

        db.session.commit()

        return redirect("/registrar_reserva/")
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


@current_app.route("/reportes/")
@login_required
def reportes():
    roles = {role.name for role in current_user.roles}
    if "Admin" not in roles:
        abort(403)

    from sqlalchemy import func

    # --- ESTADÍSTICAS GENERALES (Conteos y Sumatorias) ---

    # Total de reservas (conteo)
    total_reservas = db.session.query(func.count(Reserva.id_reserva)).scalar() or 0

    # Total de ingresos (sumatoria)
    total_ingresos = db.session.query(func.sum(Reserva.total_reserva)).scalar() or 0

    # Total de clientes únicos (conteo distinct)
    total_clientes = (
        db.session.query(func.count(func.distinct(Reserva.id_usuario))).scalar() or 0
    )

    # Total de platos vendidos (sumatoria de cantidades)
    total_platos_vendidos = (
        db.session.query(func.sum(DetalleReserva.cantidad)).scalar() or 0
    )

    stats = {
        "total_reservas": int(total_reservas),
        "total_ingresos": str(total_ingresos),
        "total_clientes": int(total_clientes),
        "total_platos_vendidos": int(total_platos_vendidos),
    }

    # --- AGRUPACIÓN POR ESTADO (para gráfica de barras) ---
    resultados_estado = (
        db.session.query(Reserva.estado, func.count(Reserva.id_reserva))
        .group_by(Reserva.estado)
        .all()
    )
    datos_estados = [
        {"estado": estado, "cantidad": cantidad}
        for estado, cantidad in resultados_estado
    ]

    # --- AGRUPACIÓN POR CATEGORÍA CON SUMAS (para gráfica de pastel y tabla) ---
    resultados_categoria = (
        db.session.query(
            CategoriaPlato.nombre,
            func.sum(DetalleReserva.cantidad).label("cantidad_vendida"),
            func.sum(DetalleReserva.subtotal).label("ingresos_totales"),
        )
        .join(Plato, Plato.id_categoria == CategoriaPlato.id_categoria)
        .join(DetalleReserva, DetalleReserva.id_plato == Plato.id_plato)
        .group_by(CategoriaPlato.id_categoria, CategoriaPlato.nombre)
        .order_by(func.sum(DetalleReserva.subtotal).desc())
        .all()
    )

    datos_categorias = [
        {"nombre": nombre, "ingresos": float(ingresos) if ingresos else 0}
        for nombre, _, ingresos in resultados_categoria
    ]

    stats_por_categoria = [
        {
            "nombre": nombre,
            "cantidad_vendida": int(cantidad_vendida) if cantidad_vendida else 0,
            "ingresos_totales": str(ingresos_totales) if ingresos_totales else "0.00",
            "promedio": str(ingresos_totales / cantidad_vendida)
            if cantidad_vendida and ingresos_totales
            else "0.00",
        }
        for nombre, cantidad_vendida, ingresos_totales in resultados_categoria
    ]

    # --- AGRUPACIÓN POR FECHA (últimos 30 días) - Para gráfica de líneas ---
    from datetime import timedelta

    fecha_inicio = datetime.now() - timedelta(days=30)

    resultados_fecha = (
        db.session.query(
            func.date(Reserva.fecha).label("fecha"),
            func.count(Reserva.id_reserva).label("cantidad"),
        )
        .filter(Reserva.fecha >= fecha_inicio)
        .group_by(func.date(Reserva.fecha))
        .order_by(func.date(Reserva.fecha).asc())
        .all()
    )

    datos_linea_tiempo = [
        {"fecha": fecha.strftime("%Y-%m-%d") if fecha else "", "cantidad": cantidad}
        for fecha, cantidad in resultados_fecha
    ]

    # --- ANÁLISIS DE TENDENCIAS Y COMPORTAMIENTO ---
    
    # Horarios con mayor actividad (por hora del día)
    resultados_horas = (
        db.session.query(
            func.extract('hour', Reserva.fecha).label('hora'),
            func.count(Reserva.id_reserva).label('cantidad')
        )
        .group_by(func.extract('hour', Reserva.fecha))
        .order_by(func.count(Reserva.id_reserva).desc())
        .limit(5)
        .all()
    )
    
    horas_pico = [
        {"hora": int(hora), "cantidad": int(cantidad)}
        for hora, cantidad in resultados_horas
    ]
    
    # Clientes más frecuentes
    resultados_clientes = (
        db.session.query(
            AppBuilderUser.username,
            AppBuilderUser.first_name,
            AppBuilderUser.last_name,
            func.count(Reserva.id_reserva).label('total_reservas')
        )
        .join(Reserva, Reserva.id_usuario == AppBuilderUser.id)
        .group_by(AppBuilderUser.id, AppBuilderUser.username, 
                  AppBuilderUser.first_name, AppBuilderUser.last_name)
        .order_by(func.count(Reserva.id_reserva).desc())
        .limit(5)
        .all()
    )
    
    clientes_frecuentes = [
        {
            "username": username,
            "nombre": f"{first_name or ''} {last_name or ''}".strip() or username,
            "total_reservas": int(total)
        }
        for username, first_name, last_name, total in resultados_clientes
    ]
    
    # Tendencia de ventas (comparativa últimos 15 días vs 15 anteriores)
    fecha_corte = datetime.now() - timedelta(days=15)
    fecha_inicio_anterior = datetime.now() - timedelta(days=30)
    
    ventas_ultimos_15 = (
        db.session.query(func.sum(Reserva.total_reserva))
        .filter(Reserva.fecha >= fecha_corte)
        .scalar() or 0
    )
    
    ventas_15_anteriores = (
        db.session.query(func.sum(Reserva.total_reserva))
        .filter(Reserva.fecha >= fecha_inicio_anterior, Reserva.fecha < fecha_corte)
        .scalar() or 0
    )
    
    tendencia_ventas = {
        "periodo_actual": str(ventas_ultimos_15),
        "periodo_anterior": str(ventas_15_anteriores),
        "crecimiento": float(((ventas_ultimos_15 - ventas_15_anteriores) / ventas_15_anteriores * 100) if ventas_15_anteriores > 0 else 0)
    }
    
    # Platos más vendidos (top 5)
    resultados_platos = (
        db.session.query(
            Plato.nombre,
            func.sum(DetalleReserva.cantidad).label('cantidad_vendida')
        )
        .join(DetalleReserva, DetalleReserva.id_plato == Plato.id_plato)
        .group_by(Plato.id_plato, Plato.nombre)
        .order_by(func.sum(DetalleReserva.cantidad).desc())
        .limit(5)
        .all()
    )
    
    platos_mas_vendidos = [
        {"nombre": nombre, "cantidad": int(cantidad)}
        for nombre, cantidad in resultados_platos
    ]

    # --- GENERAR ANÁLISIS CON IA ---
    
    # Contexto para Reporte 1 - Análisis General
    contexto_reporte_1 = {
        "metricas_generales": stats,
        "reservas_por_estado": datos_estados,
        "ingresos_por_categoria": datos_categorias,
        "platos_mas_vendidos": platos_mas_vendidos,
        "tendencia_ventas": tendencia_ventas
    }
    
    # Contexto para Reporte 2 - Tendencias y Comportamiento
    contexto_reporte_2 = {
        "horas_pico": horas_pico,
        "clientes_frecuentes": clientes_frecuentes,
        "tendencia_ventas": tendencia_ventas,
        "evolucion_diaria": datos_linea_tiempo,
        "categorias_rendimiento": stats_por_categoria
    }
    
    analisis_ia_general = None
    analisis_ia_tendencias = None
    
    try:
        # Generar análisis general con IA
        prompt_general = """
Realiza un ANÁLISIS GENERAL DEL SISTEMA basado en las métricas proporcionadas. Incluye:

1. Resumen ejecutivo del estado actual del negocio
2. Interpretación de las métricas principales (ventas, reservas, clientes)
3. Identificación de los productos/servicios más exitosos
4. Evaluación del rendimiento general
5. Recomendaciones clave para mejorar el negocio

Sé específico con los datos proporcionados y proporciona insights accionables.
"""
        analisis_ia_general = preguntar_ia(prompt_general, contexto_reporte_1)
        
        # Generar análisis de tendencias con IA
        prompt_tendencias = """
Realiza un ANÁLISIS DE TENDENCIAS Y COMPORTAMIENTO basado en los datos proporcionados. Incluye:

1. Patrones temporales identificados (horarios pico, días con mayor actividad)
2. Perfil de clientes más frecuentes y su comportamiento
3. Tendencia de ventas (crecimiento o disminución)
4. Servicios/productos con mejor y peor rendimiento
5. Proyecciones o recomendaciones basadas en las tendencias observadas

Proporciona un análisis detallado que ayude a tomar decisiones estratégicas.
"""
        analisis_ia_tendencias = preguntar_ia(prompt_tendencias, contexto_reporte_2)
        
    except Exception as e:
        # Si falla la IA, continuar sin el análisis
        current_app.logger.error(f"Error generando análisis con IA: {str(e)}")
        analisis_ia_general = "No se pudo generar el análisis automático en este momento."
        analisis_ia_tendencias = "No se pudo generar el análisis de tendencias en este momento."

    return render_template(
        "reportes.html",
        stats=stats,
        datos_estados=datos_estados,
        datos_categorias=datos_categorias,
        datos_linea_tiempo=datos_linea_tiempo,
        stats_por_categoria=stats_por_categoria,
        horas_pico=horas_pico,
        clientes_frecuentes=clientes_frecuentes,
        tendencia_ventas=tendencia_ventas,
        platos_mas_vendidos=platos_mas_vendidos,
        analisis_ia_general=analisis_ia_general,
        analisis_ia_tendencias=analisis_ia_tendencias,
        appbuilder=appbuilder,
    )


@current_app.route("/reporte-general/")
@login_required
def reporte_general():
    roles = {role.name for role in current_user.roles}
    if "Admin" not in roles:
        abort(403)

    from sqlalchemy import func

    # --- ESTADÍSTICAS GENERALES (Conteos y Sumatorias) ---

    # Total de reservas (conteo)
    total_reservas = db.session.query(func.count(Reserva.id_reserva)).scalar() or 0

    # Total de ingresos (sumatoria)
    total_ingresos = db.session.query(func.sum(Reserva.total_reserva)).scalar() or 0

    # Total de clientes únicos (conteo distinct)
    total_clientes = (
        db.session.query(func.count(func.distinct(Reserva.id_usuario))).scalar() or 0
    )

    # Total de platos vendidos (sumatoria de cantidades)
    total_platos_vendidos = (
        db.session.query(func.sum(DetalleReserva.cantidad)).scalar() or 0
    )

    stats = {
        "total_reservas": int(total_reservas),
        "total_ingresos": str(total_ingresos),
        "total_clientes": int(total_clientes),
        "total_platos_vendidos": int(total_platos_vendidos),
    }

    # --- AGRUPACIÓN POR ESTADO (para gráfica de barras) ---
    resultados_estado = (
        db.session.query(Reserva.estado, func.count(Reserva.id_reserva))
        .group_by(Reserva.estado)
        .all()
    )
    datos_estados = [
        {"estado": estado, "cantidad": cantidad}
        for estado, cantidad in resultados_estado
    ]

    # --- AGRUPACIÓN POR CATEGORÍA CON SUMAS (para gráfica de pastel y tabla) ---
    resultados_categoria = (
        db.session.query(
            CategoriaPlato.nombre,
            func.sum(DetalleReserva.cantidad).label("cantidad_vendida"),
            func.sum(DetalleReserva.subtotal).label("ingresos_totales"),
        )
        .join(Plato, Plato.id_categoria == CategoriaPlato.id_categoria)
        .join(DetalleReserva, DetalleReserva.id_plato == Plato.id_plato)
        .group_by(CategoriaPlato.id_categoria, CategoriaPlato.nombre)
        .order_by(func.sum(DetalleReserva.subtotal).desc())
        .all()
    )

    datos_categorias = [
        {"nombre": nombre, "ingresos": float(ingresos) if ingresos else 0}
        for nombre, _, ingresos in resultados_categoria
    ]

    stats_por_categoria = [
        {
            "nombre": nombre,
            "cantidad_vendida": int(cantidad_vendida) if cantidad_vendida else 0,
            "ingresos_totales": str(ingresos_totales) if ingresos_totales else "0.00",
            "promedio": str(ingresos_totales / cantidad_vendida)
            if cantidad_vendida and ingresos_totales
            else "0.00",
        }
        for nombre, cantidad_vendida, ingresos_totales in resultados_categoria
    ]

    # --- Platos más vendidos (top 5) ---
    resultados_platos = (
        db.session.query(
            Plato.nombre,
            func.sum(DetalleReserva.cantidad).label('cantidad_vendida')
        )
        .join(DetalleReserva, DetalleReserva.id_plato == Plato.id_plato)
        .group_by(Plato.id_plato, Plato.nombre)
        .order_by(func.sum(DetalleReserva.cantidad).desc())
        .limit(5)
        .all()
    )
    
    platos_mas_vendidos = [
        {"nombre": nombre, "cantidad": int(cantidad)}
        for nombre, cantidad in resultados_platos
    ]

    # --- Tendencia de ventas (comparativa últimos 15 días vs 15 anteriores) ---
    from datetime import timedelta
    fecha_corte = datetime.now() - timedelta(days=15)
    fecha_inicio_anterior = datetime.now() - timedelta(days=30)
    
    ventas_ultimos_15 = (
        db.session.query(func.sum(Reserva.total_reserva))
        .filter(Reserva.fecha >= fecha_corte)
        .scalar() or 0
    )
    
    ventas_15_anteriores = (
        db.session.query(func.sum(Reserva.total_reserva))
        .filter(Reserva.fecha >= fecha_inicio_anterior, Reserva.fecha < fecha_corte)
        .scalar() or 0
    )
    
    tendencia_ventas = {
        "periodo_actual": str(ventas_ultimos_15),
        "periodo_anterior": str(ventas_15_anteriores),
        "crecimiento": float(((ventas_ultimos_15 - ventas_15_anteriores) / ventas_15_anteriores * 100) if ventas_15_anteriores > 0 else 0)
    }

    # --- GENERAR ANÁLISIS CON IA ---
    contexto_reporte_1 = {
        "metricas_generales": stats,
        "reservas_por_estado": datos_estados,
        "ingresos_por_categoria": datos_categorias,
        "platos_mas_vendidos": platos_mas_vendidos,
        "tendencia_ventas": tendencia_ventas
    }
    
    analisis_ia_general = None
    
    try:
        prompt_general = """
Realiza un ANÁLISIS GENERAL DEL SISTEMA basado en las métricas proporcionadas. Incluye:

1. Resumen ejecutivo del estado actual del negocio
2. Interpretación de las métricas principales (ventas, reservas, clientes)
3. Identificación de los productos/servicios más exitosos
4. Evaluación del rendimiento general
5. Recomendaciones clave para mejorar el negocio

Sé específico con los datos proporcionados y proporciona insights accionables.
"""
        analisis_ia_general = preguntar_ia(prompt_general, contexto_reporte_1)
        
    except Exception as e:
        current_app.logger.error(f"Error generando análisis con IA: {str(e)}")
        analisis_ia_general = "No se pudo generar el análisis automático en este momento."

    return render_template(
        "reporte_general.html",
        stats=stats,
        datos_estados=datos_estados,
        datos_categorias=datos_categorias,
        stats_por_categoria=stats_por_categoria,
        platos_mas_vendidos=platos_mas_vendidos,
        tendencia_ventas=tendencia_ventas,
        analisis_ia_general=analisis_ia_general,
        appbuilder=appbuilder,
    )


@current_app.route("/reporte-tendencias/")
@login_required
def reporte_tendencias():
    roles = {role.name for role in current_user.roles}
    if "Admin" not in roles:
        abort(403)

    from sqlalchemy import func
    from datetime import timedelta

    # --- Horarios con mayor actividad (por hora del día) ---
    resultados_horas = (
        db.session.query(
            func.extract('hour', Reserva.fecha).label('hora'),
            func.count(Reserva.id_reserva).label('cantidad')
        )
        .group_by(func.extract('hour', Reserva.fecha))
        .order_by(func.count(Reserva.id_reserva).desc())
        .limit(5)
        .all()
    )
    
    horas_pico = [
        {"hora": int(hora), "cantidad": int(cantidad)}
        for hora, cantidad in resultados_horas
    ]
    
    # --- Clientes más frecuentes ---
    resultados_clientes = (
        db.session.query(
            AppBuilderUser.username,
            AppBuilderUser.first_name,
            AppBuilderUser.last_name,
            func.count(Reserva.id_reserva).label('total_reservas')
        )
        .join(Reserva, Reserva.id_usuario == AppBuilderUser.id)
        .group_by(AppBuilderUser.id, AppBuilderUser.username, 
                  AppBuilderUser.first_name, AppBuilderUser.last_name)
        .order_by(func.count(Reserva.id_reserva).desc())
        .limit(5)
        .all()
    )
    
    clientes_frecuentes = [
        {
            "username": username,
            "nombre": f"{first_name or ''} {last_name or ''}".strip() or username,
            "total_reservas": int(total)
        }
        for username, first_name, last_name, total in resultados_clientes
    ]
    
    # --- Tendencia de ventas (comparativa últimos 15 días vs 15 anteriores) ---
    fecha_corte = datetime.now() - timedelta(days=15)
    fecha_inicio_anterior = datetime.now() - timedelta(days=30)
    
    ventas_ultimos_15 = (
        db.session.query(func.sum(Reserva.total_reserva))
        .filter(Reserva.fecha >= fecha_corte)
        .scalar() or 0
    )
    
    ventas_15_anteriores = (
        db.session.query(func.sum(Reserva.total_reserva))
        .filter(Reserva.fecha >= fecha_inicio_anterior, Reserva.fecha < fecha_corte)
        .scalar() or 0
    )
    
    tendencia_ventas = {
        "periodo_actual": str(ventas_ultimos_15),
        "periodo_anterior": str(ventas_15_anteriores),
        "crecimiento": float(((ventas_ultimos_15 - ventas_15_anteriores) / ventas_15_anteriores * 100) if ventas_15_anteriores > 0 else 0)
    }
    
    # --- Evolución diaria (últimos 30 días) ---
    fecha_inicio = datetime.now() - timedelta(days=30)
    
    resultados_fecha = (
        db.session.query(
            func.date(Reserva.fecha).label("fecha"),
            func.count(Reserva.id_reserva).label("cantidad"),
        )
        .filter(Reserva.fecha >= fecha_inicio)
        .group_by(func.date(Reserva.fecha))
        .order_by(func.date(Reserva.fecha).asc())
        .all()
    )

    datos_linea_tiempo = [
        {"fecha": fecha.strftime("%Y-%m-%d") if fecha else "", "cantidad": cantidad}
        for fecha, cantidad in resultados_fecha
    ]
    
    # --- Rendimiento por categoría ---
    resultados_categoria = (
        db.session.query(
            CategoriaPlato.nombre,
            func.sum(DetalleReserva.cantidad).label("cantidad_vendida"),
            func.sum(DetalleReserva.subtotal).label("ingresos_totales"),
        )
        .join(Plato, Plato.id_categoria == CategoriaPlato.id_categoria)
        .join(DetalleReserva, DetalleReserva.id_plato == Plato.id_plato)
        .group_by(CategoriaPlato.id_categoria, CategoriaPlato.nombre)
        .order_by(func.sum(DetalleReserva.subtotal).desc())
        .all()
    )

    stats_por_categoria = [
        {
            "nombre": nombre,
            "cantidad_vendida": int(cantidad_vendida) if cantidad_vendida else 0,
            "ingresos_totales": str(ingresos_totales) if ingresos_totales else "0.00",
            "promedio": str(ingresos_totales / cantidad_vendida)
            if cantidad_vendida and ingresos_totales
            else "0.00",
        }
        for nombre, cantidad_vendida, ingresos_totales in resultados_categoria
    ]

    # --- GENERAR ANÁLISIS CON IA ---
    contexto_reporte_2 = {
        "horas_pico": horas_pico,
        "clientes_frecuentes": clientes_frecuentes,
        "tendencia_ventas": tendencia_ventas,
        "evolucion_diaria": datos_linea_tiempo,
        "categorias_rendimiento": stats_por_categoria
    }
    
    analisis_ia_tendencias = None
    
    try:
        prompt_tendencias = """
Realiza un ANÁLISIS DE TENDENCIAS Y COMPORTAMIENTO basado en los datos proporcionados. Incluye:

1. Patrones temporales identificados (horarios pico, días con mayor actividad)
2. Perfil de clientes más frecuentes y su comportamiento
3. Tendencia de ventas (crecimiento o disminución)
4. Servicios/productos con mejor y peor rendimiento
5. Proyecciones o recomendaciones basadas en las tendencias observadas

Proporciona un análisis detallado que ayude a tomar decisiones estratégicas.
"""
        analisis_ia_tendencias = preguntar_ia(prompt_tendencias, contexto_reporte_2)
        
    except Exception as e:
        current_app.logger.error(f"Error generando análisis con IA: {str(e)}")
        analisis_ia_tendencias = "No se pudo generar el análisis de tendencias en este momento."

    return render_template(
        "reporte_tendencias.html",
        horas_pico=horas_pico,
        clientes_frecuentes=clientes_frecuentes,
        tendencia_ventas=tendencia_ventas,
        datos_linea_tiempo=datos_linea_tiempo,
        stats_por_categoria=stats_por_categoria,
        analisis_ia_tendencias=analisis_ia_tendencias,
        appbuilder=appbuilder,
    )

@current_app.route("/reporte-inteligente/")
@login_required
def reporte_inteligente():
    roles = {role.name for role in current_user.roles}
    if "Admin" not in roles:
        abort(403)

    from sqlalchemy import func
    from datetime import datetime, timedelta

    # =========================================================
    # PREDICCIÓN / RECOMENDACIÓN INTELIGENTE
    # =========================================================
    #
    # Este reporte implementa:
    #
    # 1. Predicción de demanda
    # 2. Recomendaciones automáticas
    # 3. Identificación de categorías débiles
    # 4. Sugerencias de mejora generadas por IA
    #
    # MODELO UTILIZADO:
    #
    # Se utiliza un modelo heurístico basado en:
    # - Tendencia histórica de ventas
    # - Promedio móvil de reservas
    # - Frecuencia de platos vendidos
    # - Comparación entre periodos
    #
    # Luego la IA interpreta esos datos y genera
    # recomendaciones inteligentes.
    #
    # =========================================================

    # ---------------------------------------------------------
    # RANGO DE FECHAS
    # ---------------------------------------------------------
    hoy = datetime.now()
    hace_7 = hoy - timedelta(days=7)
    hace_14 = hoy - timedelta(days=14)
    hace_30 = hoy - timedelta(days=30)

    # =========================================================
    # 1. PREDICCIÓN DE DEMANDA
    # =========================================================

    # Reservas últimos 7 días
    reservas_7_dias = (
        db.session.query(
            func.date(Reserva.fecha),
            func.count(Reserva.id_reserva)
        )
        .filter(Reserva.fecha >= hace_7)
        .group_by(func.date(Reserva.fecha))
        .all()
    )

    total_7_dias = sum(cantidad for _, cantidad in reservas_7_dias)

    promedio_diario = (
        total_7_dias / len(reservas_7_dias)
        if reservas_7_dias else 0
    )

    # Predicción simple próxima semana
    prediccion_proxima_semana = int(round(promedio_diario * 7))

    # =========================================================
    # 2. COMPARACIÓN DE CRECIMIENTO
    # =========================================================

    ventas_actuales = float(
        (
            db.session.query(func.sum(Reserva.total_reserva))
            .filter(Reserva.fecha >= hace_7)
            .scalar()
        ) or 0
    )

    ventas_anteriores = float(
        (
            db.session.query(func.sum(Reserva.total_reserva))
            .filter(
                Reserva.fecha >= hace_14,
                Reserva.fecha < hace_7
            )
            .scalar()
        ) or 0
    )

    crecimiento = (
        ((ventas_actuales - ventas_anteriores) / ventas_anteriores) * 100
        if ventas_anteriores > 0 else 0
    )

    # =========================================================
    # 3. PLATOS MÁS DEMANDADOS
    # =========================================================

    resultados_platos = (
        db.session.query(
            Plato.nombre,
            func.sum(DetalleReserva.cantidad).label("cantidad")
        )
        .join(
            DetalleReserva,
            DetalleReserva.id_plato == Plato.id_plato
        )
        .group_by(Plato.id_plato, Plato.nombre)
        .order_by(func.sum(DetalleReserva.cantidad).desc())
        .limit(5)
        .all()
    )

    platos_recomendados = [
        {
            "nombre": nombre,
            "cantidad": int(cantidad)
        }
        for nombre, cantidad in resultados_platos
    ]

    # =========================================================
    # 4. CATEGORÍAS CON BAJO RENDIMIENTO
    # =========================================================

    resultados_categorias = (
        db.session.query(
            CategoriaPlato.nombre,
            func.sum(DetalleReserva.subtotal).label("ingresos")
        )
        .join(
            Plato,
            Plato.id_categoria == CategoriaPlato.id_categoria
        )
        .join(
            DetalleReserva,
            DetalleReserva.id_plato == Plato.id_plato
        )
        .group_by(
            CategoriaPlato.id_categoria,
            CategoriaPlato.nombre
        )
        .order_by(func.sum(DetalleReserva.subtotal).asc())
        .all()
    )

    categorias_bajo_rendimiento = [
        {
            "nombre": nombre,
            "ingresos": float(ingresos or 0)
        }
        for nombre, ingresos in resultados_categorias[:3]
    ]

    # =========================================================
    # 5. HORARIOS MÁS DEMANDADOS
    # =========================================================

    resultados_horas = (
        db.session.query(
            func.extract("hour", Reserva.fecha).label("hora"),
            func.count(Reserva.id_reserva).label("cantidad")
        )
        .group_by(func.extract("hour", Reserva.fecha))
        .order_by(func.count(Reserva.id_reserva).desc())
        .limit(5)
        .all()
    )

    horas_pico = [
        {
            "hora": int(hora),
            "cantidad": int(cantidad)
        }
        for hora, cantidad in resultados_horas
    ]

    # =========================================================
    # 6. RESULTADO VISUAL
    # =========================================================

    datos_prediccion = {
        "promedio_diario": round(promedio_diario, 2),
        "prediccion_semana": prediccion_proxima_semana,
        "ventas_actuales": float(ventas_actuales),
        "ventas_anteriores": float(ventas_anteriores),
        "crecimiento": round(crecimiento, 2)
    }

    # =========================================================
    # 7. CONTEXTO PARA IA
    # =========================================================

    contexto_ia = {
        "prediccion_demanda": datos_prediccion,
        "platos_recomendados": platos_recomendados,
        "categorias_bajo_rendimiento": categorias_bajo_rendimiento,
        "horas_pico": horas_pico
    }

    # =========================================================
    # 8. GENERAR RECOMENDACIONES CON IA
    # =========================================================

    analisis_ia = None

    try:

        prompt_ia = """
Realiza un REPORTE INTELIGENTE DEL NEGOCIO basado en los datos entregados.

Debes incluir:

1. Predicción de demanda esperada
2. Interpretación del crecimiento o disminución de ventas
3. Productos más recomendados para promocionar
4. Categorías con bajo rendimiento y posibles causas
5. Horarios donde debería reforzarse atención o stock
6. Recomendaciones estratégicas accionables
7. Conclusión general del estado del negocio

El análisis debe ser claro, técnico y útil para toma de decisiones.
"""

        analisis_ia = preguntar_ia(
            prompt_ia,
            contexto_ia
        )

    except Exception as e:
        current_app.logger.error(
            f"Error generando reporte inteligente: {str(e)}"
        )

        analisis_ia = (
            "No se pudo generar el análisis inteligente."
        )

    # =========================================================
    # 9. RENDER
    # =========================================================

    return render_template(
        "reporte_inteligente.html",

        # Predicción
        datos_prediccion=datos_prediccion,

        # Recomendaciones
        platos_recomendados=platos_recomendados,

        # Riesgos
        categorias_bajo_rendimiento=categorias_bajo_rendimiento,

        # Horarios
        horas_pico=horas_pico,

        # IA
        analisis_ia=analisis_ia,

        # Modelo explicado
        modelo_utilizado="""
Modelo heurístico de predicción basado en:
- promedio móvil de reservas
- tendencia histórica de ventas
- frecuencia de productos vendidos
- análisis comparativo entre periodos
- interpretación mediante IA
""",

        appbuilder=appbuilder
    )

# Menú desplegable para Reportes
try:
    appbuilder.add_separator("Administración")
except Exception:
    pass 
    
appbuilder.add_link(
    "Reporte General",
    label="Reporte General",
    href="/reporte-general/",
    icon="fa-chart-pie",
    category="Administración",
)

appbuilder.add_link(
    "Tendencias y Comportamiento",
    label="Tendencias y Comportamiento",
    href="/reporte-tendencias/",
    icon="fa-line-chart",
    category="Administración",
)

appbuilder.add_link(
    'Reporte Inteligente',
    label='Reporte Inteligente',
    href='/reporte-inteligente/',
    icon='fa-robot',
    category='Administración'
)
