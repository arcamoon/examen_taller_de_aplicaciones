from flask import Flask
from flask_appbuilder import AppBuilder
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
appbuilder = AppBuilder()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object("config")

    with app.app_context():
        # Vinculamos la base de datos a la app
        db.init_app(app)

        # Inicializamos FAB pasándole la app y la sesión de SQLAlchemy
        appbuilder.init_app(app, db.session)

        db.create_all()

        # Aquí abajo continúan tus registros de vistas/APIs...
        # ...

    return app
