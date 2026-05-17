class RoleService:
    permisos_cajero = [
        ("can_list", "CategoriaPlatoModelView"),
        ("can_show", "CategoriaPlatoModelView"),
        ("can_list", "PlatoModelView"),
        ("can_show", "PlatoModelView"),
        ("can_list", "ReservaModelView"),
        ("can_show", "ReservaModelView"),
        ("can_edit", "ReservaModelView"),
        ("can_list", "DetalleReservaModelView"),
        ("can_show", "DetalleReservaModelView"),
        ("menu_access", "Categorias"),  # Permiso para ver el botón en el menú
        ("menu_access", "Platos"),
        ("menu_access", "Reservas"),
        ("menu_access", "Detalles de reserva"),
        ("menu_access", "Restaurante"),  # Permiso para ver el menú padre
        ("menu_access", "Reservaciones"),
    ]
    permisos_cliente = [
        ("can_list", "PlatoModelView"),
        ("can_show", "PlatoModelView"),
        ("menu_access", "Platos"),
        ("menu_access", "Restaurante"),  # Permiso para ver el menú padre
    ]

    def init_custom_roles(self, appbuilder):
        """Función para crear los roles extras si no existen en la BD."""
        sm = appbuilder.sm

        roles_to_created = ["cajero", "cliente"]

        for role_name in roles_to_created:
            role = sm.find_role(role_name)
            if not role:
                sm.add_role(role_name)

    def configure_custom_roles(self, appbuilder):
        sm = appbuilder.sm

        self._assign_permissions(sm, "cajero", self.permisos_cajero)
        self._assign_permissions(sm, "cliente", self.permisos_cliente)

    @staticmethod
    def _assign_permissions(sm, role_name, permissions):
        role = sm.find_role(role_name)
        if not role:
            return

        for perm_name, view_name in permissions:
            permission_view = sm.find_permission_view_menu(perm_name, view_name)
            if permission_view and permission_view not in role.permissions:
                sm.add_permission_role(role, permission_view)
