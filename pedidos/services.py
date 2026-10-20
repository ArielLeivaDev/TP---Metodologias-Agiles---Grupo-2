"""Lógica del catálogo público y de los pedidos para retiro (HU-13).

Igual que el carrito del POS, el pedido que arma un cliente desde afuera vive
en la sesión del navegador (`request.session["pedido"]`) como una lista de
{"producto_id": ..., "cantidad": ...}. Recién se persiste un `Pedido` cuando
el cliente confirma: así no quedan pedidos basura si solo estaba mirando.
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction

from ventas.models import Producto

from .models import ItemPedido, Pedido

CLAVE_PEDIDO = "pedido"
MAX_UNIDADES_POR_ITEM = 99  # techo sensato para un pedido de kiosco


class ErrorPedido(Exception):
    """Error de negocio del pedido. El mensaje es para mostrar al cliente."""


# ========== CARRITO DEL PEDIDO (sesión) ==========


def leer_pedido(request):
    """Carrito crudo del pedido (lista de dicts), nunca None."""
    return request.session.get(CLAVE_PEDIDO, [])


def guardar_pedido(request, carrito):
    request.session[CLAVE_PEDIDO] = carrito
    request.session.modified = True


def vaciar_pedido(request):
    request.session.pop(CLAVE_PEDIDO, None)
    request.session.modified = True


def items_del_pedido(request):
    """Hidrata el carrito de la sesión con los productos actuales de la BD.

    Devuelve lista de dicts: producto, cantidad, subtotal. Los productos
    dados de baja o eliminados se descartan silenciosamente.
    """
    carrito = leer_pedido(request)
    if not carrito:
        return []

    productos = {
        p.pk: p
        for p in Producto.objects.filter(
            pk__in=[fila["producto_id"] for fila in carrito], activo=True
        )
    }

    items = []
    carrito_limpio = []
    for fila in carrito:
        producto = productos.get(fila.get("producto_id"))
        if producto is None:
            continue
        cantidad = max(int(fila.get("cantidad", 0)), 0)
        if cantidad <= 0:
            continue
        items.append(
            {
                "producto": producto,
                "cantidad": cantidad,
                "subtotal": producto.precio * cantidad,
            }
        )
        carrito_limpio.append({"producto_id": producto.pk, "cantidad": cantidad})

    if carrito_limpio != carrito:
        guardar_pedido(request, carrito_limpio)
    return items


def total_del_pedido(items):
    return sum((item["subtotal"] for item in items), Decimal("0.00"))


def _cantidad_valida(valor):
    try:
        cantidad = int(valor)
    except (TypeError, ValueError):
        raise ErrorPedido("La cantidad tiene que ser un número entero.")
    if cantidad < 1:
        raise ErrorPedido("La cantidad mínima es 1.")
    if cantidad > MAX_UNIDADES_POR_ITEM:
        raise ErrorPedido(
            f"Por pedido podés llevar hasta {MAX_UNIDADES_POR_ITEM} unidades "
            "de un mismo producto. Para más, escribinos por WhatsApp."
        )
    return cantidad


def agregar_al_pedido(request, producto, cantidad=1):
    """Suma (o crea) una línea del carrito del pedido.

    Valida contra el stock *al momento de armar*, pero el descuento real
    recién ocurre en el cobro del POS: acá solo se avisa.
    """
    cantidad = _cantidad_valida(cantidad)
    carrito = leer_pedido(request)
    for fila in carrito:
        if fila["producto_id"] == producto.pk:
            nueva = fila["cantidad"] + cantidad
            if nueva > MAX_UNIDADES_POR_ITEM:
                raise ErrorPedido(
                    f"No podés pedir más de {MAX_UNIDADES_POR_ITEM} unidades "
                    "de un mismo producto."
                )
            fila["cantidad"] = nueva
            guardar_pedido(request, carrito)
            return
    carrito.append({"producto_id": producto.pk, "cantidad": cantidad})
    guardar_pedido(request, carrito)


def quitar_del_pedido(request, producto_id):
    carrito = [
        fila for fila in leer_pedido(request) if fila["producto_id"] != producto_id
    ]
    guardar_pedido(request, carrito)


def buscar_producto_publico(producto_id):
    """Producto activo por id, o None. Nunca expone el stock exacto."""
    return Producto.objects.filter(pk=producto_id, activo=True).first()


# ========== ALTA DEL PEDIDO ==========


@transaction.atomic
def crear_pedido(request, nombre_cliente, telefono="", comentario=""):
    """Persiste el pedido de la sesión y lo vacía.

    Devuelve el `Pedido` creado. Lanza `ErrorPedido` si no hay nada que pedir
    o si falta el nombre. El total queda congelado con los precios actuales.
    """
    nombre_cliente = (nombre_cliente or "").strip()
    if not nombre_cliente:
        raise ErrorPedido("Necesitamos tu nombre para preparar el pedido.")

    items = items_del_pedido(request)
    if not items:
        raise ErrorPedido("Todavía no agregaste ningún producto al pedido.")

    total = total_del_pedido(items)
    pedido = Pedido.objects.create(
        nombre_cliente=nombre_cliente[:120],
        telefono=(telefono or "").strip()[:30],
        comentario=(comentario or "").strip(),
        total=total,
    )
    ItemPedido.objects.bulk_create(
        [
            ItemPedido(
                pedido=pedido,
                producto=item["producto"],
                nombre_producto=item["producto"].nombre,
                cantidad=item["cantidad"],
                precio_unitario=item["producto"].precio,
            )
            for item in items
        ]
    )
    vaciar_pedido(request)
    return pedido


def texto_para_whatsapp(pedido):
    """Arma el mensaje que el navegador le manda al WhatsApp del kiosco.

    Usa el mismo formato de pesos que la UI (`$1.500`) y evita decimales de
    más, para que el kiosquero lea lo mismo que ve el cliente en pantalla.
    """
    from ventas.services import formatear_monto

    lineas = [f"¡Hola! Quiero hacer este pedido (Pedido #{pedido.pk}):", ""]
    for detalle in pedido.detalles.all():
        lineas.append(
            f"- {detalle.nombre_producto} x{detalle.cantidad} "
            f"→ {formatear_monto(detalle.subtotal())}"
        )
    lineas.append("")
    lineas.append(f"Total: {formatear_monto(pedido.total)}")
    lineas.append(f"A nombre de: {pedido.nombre_cliente}")
    if pedido.comentario:
        lineas.append(f"Comentario: {pedido.comentario}")
    lineas.append("")
    lineas.append("Lo retiro por el local. ¡Gracias!")
    return "\n".join(lineas)
