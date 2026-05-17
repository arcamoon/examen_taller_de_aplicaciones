class RoleService:
    permisos_cajero = [
        ("can_list", "CategoriaPlatoModelView"),
        ("can_show", "CategoriaPlatoModelView"),
        ("can_list", "PlatoModelView"),
        ("can_show", "PlatoModelView"),
        ("menu_access", "Categorias"),  # Permiso para ver el botón en el menú
        ("menu_access", "Platos"),
        ("menu_access", "Restaurante"),  # Permiso para ver el menú padre
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

        cajero = sm.find_role("cajero")
        # 3. Buscar los permisos en la base de datos y asociarlos al rol
        for perm_name, view_name in self.permisos_cajero:
            permission_view = sm.find_permission_view_menu(perm_name, view_name)
            if permission_view and permission_view not in cajero.permissions:
                sm.add_permission_role(cajero, permission_view)
