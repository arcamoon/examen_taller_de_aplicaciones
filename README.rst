Base Skeleton to start your application using Flask-AppBuilder
--------------------------------------------------------------

- Install it::

	pip install flask-appbuilder
	git clone https://github.com/dpgaspar/Flask-AppBuilder-Skeleton.git

- Run it::

    $ export FLASK_APP=app
    # Create an admin user
    $ flask fab create-admin
    # Run dev server
    $ flask run


That's it!!


/login-cliente/      200
/catalogo/           200
/cliente/            302 -> /login-cliente/
/cliente/reservas/   302 -> /login-cliente/
/panel/              302 -> /login/?next=/panel/
flask db check       No new upgrade operations detected.