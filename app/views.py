import base64

from flask import abort, current_app, jsonify, render_template, request
from flask_appbuilder import ModelView
from flask_appbuilder.models.sqla.interface import SQLAInterface
from markupsafe import Markup
from wtforms import FileField

from app import appbuilder
from app.crypto import decrypt_id, encrypt_id
from app.models import CategoriaPlato, Plato

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


@current_app.route("/catalogo/")
def catalogo():
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


@current_app.route("/catalogo/<plato_id>/")
def catalogo_detalle(plato_id):
    try:
        id_plato = decrypt_id(plato_id)
    except Exception:
        abort(404)

    plato = Plato.query.filter_by(id_plato=id_plato, disponible=True).first_or_404()
    return render_template("catalogo_detalle.html", plato=plato)


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
