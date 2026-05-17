from flask import Flask
from flask_appbuilder import AppBuilder
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from app.services.RoleService import RoleService


db = SQLAlchemy()
appbuilder = AppBuilder()
migrate = Migrate()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object("config")

    with app.app_context():
        # Vinculamos la base de datos a la app
        db.init_app(app)
        migrate.init_app(app, db)

        from app import models  # noqa: F401

        # Inicializamos FAB pasándole la app y la sesión de SQLAlchemy
        appbuilder.init_app(app, db.session)

        from app import views  # noqa: F401

        # Creación y configuracion de roles
        role_service = RoleService()
        role_service.init_custom_roles(appbuilder)
        role_service.configure_custom_roles(appbuilder)
        # Aquí abajo continúan tus registros de vistas/APIs...
        # ...
    return app


app = create_app()
