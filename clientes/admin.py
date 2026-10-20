from django.contrib import admin

from .models import Cliente, PagoCuentaCorriente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "nombre",
        "apellido",
        "dni",
        "puntos",
        "limite_credito",
        "saldo_deuda",
        "fecha_registro",
        "activo",
    ]
    list_filter = ["activo", "fecha_registro"]
    search_fields = ["nombre", "apellido", "dni", "email"]


@admin.register(PagoCuentaCorriente)
class PagoCuentaCorrienteAdmin(admin.ModelAdmin):
    list_display = ["id", "cliente", "monto", "fecha", "usuario"]
    list_filter = ["fecha"]
    search_fields = ["cliente__nombre", "cliente__apellido", "cliente__dni"]
    autocomplete_fields = ["cliente"]
