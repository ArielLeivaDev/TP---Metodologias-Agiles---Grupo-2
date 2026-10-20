from django.contrib import admin

from .models import ItemPedido, Pedido


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ("nombre_producto", "cantidad", "precio_unitario")


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre_cliente",
        "telefono",
        "estado",
        "total",
        "fecha",
    )
    list_filter = ("estado", "fecha")
    search_fields = ("nombre_cliente", "telefono")
    readonly_fields = ("fecha", "total")
    inlines = [ItemPedidoInline]
