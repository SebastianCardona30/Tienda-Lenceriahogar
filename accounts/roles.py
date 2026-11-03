"""Definición y configuración de roles para el panel de administración.

Tres roles para el personal del negocio:
- Administradora: control total del catálogo, pedidos, inventario, promociones,
  configuración y usuarios.
- Empleado: gestión operativa diaria: despachar y cambiar estado de pedidos,
  revisar inventario, registrar movimientos y órdenes de compra, verificar pagos.
  No puede borrar pedidos, ni modificar configuraciones del negocio, ni tocar usuarios.
- Solo lectura: puede consultar todos los registros (pedidos, clientes, stock,
  catálogo, métricas), sin permisos de edición ni borrado.
"""
from django.contrib.auth.models import Group, Permission
from django.db.models import Q

ROL_ADMINISTRADORA = "Administradora"
ROL_EMPLEADO = "Empleado"
ROL_SOLO_LECTURA = "Solo lectura"

ROLES_VALIDOS = (ROL_ADMINISTRADORA, ROL_EMPLEADO, ROL_SOLO_LECTURA)

# Apps principales de la tienda
APPS_TIENDA = (
    "catalog",
    "orders",
    "inventory",
    "payments",
    "shipping",
    "promotions",
    "core",
    "accounts",
)


def _obtener_permisos(*args, **kwargs):
    return Permission.objects.filter(*args, **kwargs)


def configurar_roles():
    """Crea o actualiza los 3 grupos y les asigna sus permisos correspondientes.

    Es idempotente: se puede ejecutar en cada migración o despliegue sin riesgo.
    """
    # 1. Grupo Administradora: todos los permisos de las apps del negocio y auth
    grupo_admin, _ = Group.objects.get_or_create(name=ROL_ADMINISTRADORA)
    permisos_admin = _obtener_permisos(
        content_type__app_label__in=APPS_TIENDA + ("auth", "admin")
    )
    grupo_admin.permissions.set(permisos_admin)

    # 2. Grupo Empleado: pedidos, inventario, pagos y consulta de catálogo/envíos
    grupo_empleado, _ = Group.objects.get_or_create(name=ROL_EMPLEADO)
    permisos_empleado = _obtener_permisos(
        # Pedidos: ver y cambiar estado (sin eliminar)
        Q(content_type__app_label="orders", codename__in=(
            "view_pedido", "change_pedido", "view_itempedido",
            "view_historialpedido", "add_historialpedido"
        ))
        # Inventario: ver todo, registrar movimientos y gestionar órdenes de compra
        | Q(content_type__app_label="inventory", codename__in=(
            "view_movimientostock", "add_movimientostock",
            "view_ordencompra", "add_ordencompra", "change_ordencompra",
            "view_ordencompraitem", "add_ordencompraitem", "change_ordencompraitem",
        ))
        # Variantes de catálogo: ver y editar stock/precio
        | Q(content_type__app_label="catalog", codename__in=(
            "view_producto", "view_variante", "change_variante",
            "view_categoria", "view_proveedor", "view_combo",
            "view_resena", "change_resena", "view_busquedasinresultados"
        ))
        # Pagos: ver y verificar comprobantes
        | Q(content_type__app_label="payments", codename__in=(
            "view_pago", "change_pago"
        ))
        # Envíos y clientes: consulta
        | Q(content_type__app_label="shipping", codename__startswith="view_")
        | Q(content_type__app_label="accounts", codename__in=(
            "view_usuario", "view_direccion"
        ))
    )
    grupo_empleado.permissions.set(permisos_empleado)

    # 3. Grupo Solo lectura: únicamente permisos view_* en todas las apps
    grupo_lectura, _ = Group.objects.get_or_create(name=ROL_SOLO_LECTURA)
    permisos_lectura = _obtener_permisos(
        content_type__app_label__in=APPS_TIENDA,
        codename__startswith="view_",
    )
    grupo_lectura.permissions.set(permisos_lectura)

    return {
        ROL_ADMINISTRADORA: grupo_admin,
        ROL_EMPLEADO: grupo_empleado,
        ROL_SOLO_LECTURA: grupo_lectura,
    }


def asignar_rol(usuario, nombre_rol):
    """Asigna un rol específico al usuario, limpiando roles previos del panel.

    Asegura que el usuario tenga is_staff=True para poder acceder al admin.
    Si el rol es Administradora, no requiere ser superuser para operar con sus permisos.
    """
    if nombre_rol not in ROLES_VALIDOS:
        raise ValueError(
            f"Rol desconocido '{nombre_rol}'. Opciones válidas: {ROLES_VALIDOS}"
        )

    configurar_roles()
    grupos = Group.objects.filter(name__in=ROLES_VALIDOS)
    usuario.groups.remove(*grupos)

    grupo = Group.objects.get(name=nombre_rol)
    usuario.groups.add(grupo)
    if not usuario.is_staff:
        usuario.is_staff = True
        usuario.save(update_fields=["is_staff"])
    return grupo


def obtener_rol(usuario):
    """Devuelve el nombre del rol del usuario, o None si no tiene rol asignado."""
    if not usuario or not usuario.is_authenticated:
        return None
    if usuario.is_superuser:
        return ROL_ADMINISTRADORA
    grupo = usuario.groups.filter(name__in=ROLES_VALIDOS).first()
    return grupo.name if grupo else None


def es_administradora(usuario):
    if not usuario or not usuario.is_authenticated:
        return False
    return usuario.is_superuser or usuario.groups.filter(name=ROL_ADMINISTRADORA).exists()


def es_empleado(usuario):
    if not usuario or not usuario.is_authenticated:
        return False
    return usuario.groups.filter(name=ROL_EMPLEADO).exists()


def es_solo_lectura(usuario):
    if not usuario or not usuario.is_authenticated:
        return False
    return usuario.groups.filter(name=ROL_SOLO_LECTURA).exists()
