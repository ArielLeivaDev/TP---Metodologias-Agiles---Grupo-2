"""Modelos de la integración externa (HU-13): catálogo público por WhatsApp.

El pedido que arma un cliente desde el catálogo público (sin login) queda
registrado acá: el kiosquero lo ve en su panel y lo prepara para el retiro.
El envío del mensaje a WhatsApp es del lado del navegador (`wa.me`), así que
el pedido se guarda *además* del mensaje: sirve como comanda interna y para
no perder el pedido si el cliente cierra el chat.
"""
from decimal import Decimal

from django.db import models


class Pedido(models.Model):
    """Pedido para retiro (take away) armado desde el catálogo público.

    No es una `Venta`: todavía no entró plata ni se descontó stock. Es una
    comanda: el kiosquero la marca como entregada recién cuando el cliente
    pasa por el local y paga.
    """

    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("entregado", "Entregado"),
        ("cancelado", "Cancelado"),
    ]

    nombre_cliente = models.CharField(
        max_length=120,
        verbose_name="Nombre del cliente",
        help_text="Como se identificó el cliente en el catálogo público.",
    )
    telefono = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Teléfono",
        help_text="Opcional: el del cliente, para avisarle cuando el pedido está.",
    )
    comentario = models.TextField(
        blank=True,
        verbose_name="Comentario",
        help_text="Aclaraciones del cliente (horario de retiro, cómo se lo "
                  "identifica, etc.).",
    )
    estado = models.CharField(
        max_length=10, choices=ESTADOS, default="pendiente"
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total estimado al momento del pedido (queda congelado).",
    )
    fecha = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha del pedido"
    )

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"

    def __str__(self):
        return f"Pedido #{self.pk} — {self.nombre_cliente}"

    @property
    def cantidad_items(self):
        """Cuántos productos distintos pidió (no unidades)."""
        return self.detalles.count()

    @property
    def unidades_totales(self):
        return sum(d.cantidad for d in self.detalles.all())

    @property
    def esta_pendiente(self):
        return self.estado == "pendiente"


class ItemPedido(models.Model):
    """Una línea del pedido: producto, cantidad y precio del momento.

    Guarda el nombre y el precio unitario *congelados*: si después el
    producto cambia de precio o se da de baja, el pedido histórico sigue
    diciendo lo que el cliente vio cuando lo armó.
    """

    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="detalles"
    )
    producto = models.ForeignKey(
        "ventas.Producto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items_pedido",
    )
    nombre_producto = models.CharField(max_length=150)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["pk"]
        verbose_name = "ítem de pedido"
        verbose_name_plural = "ítems de pedido"

    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.cantidad}x {self.nombre_producto}"

