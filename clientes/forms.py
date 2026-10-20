from decimal import Decimal

from django import forms

from usuarios.templatetags.formatos import montos

from .models import Cliente


def _dni_normalizado(valor, cliente=None):
    """Limpia el DNI/CUIT (puntos, guiones, espacios) y valida duplicados."""
    dni = (
        (valor or "")
        .strip()
        .replace(".", "")
        .replace("-", "")
        .replace(" ", "")
    )
    if not dni:
        raise forms.ValidationError("Ingresá el DNI o CUIT del cliente.")
    if not dni.isdigit() or not (7 <= len(dni) <= 11):
        raise forms.ValidationError(
            "El DNI/CUIT debe tener entre 7 y 11 dígitos (sin puntos ni guiones)."
        )
    en_uso = Cliente.objects.filter(dni=dni)
    if cliente:
        en_uso = en_uso.exclude(pk=cliente.pk)
    if en_uso.exists():
        raise forms.ValidationError(
            "Ese DNI/CUIT ya está registrado en otro cliente."
        )
    return dni


class ClienteForm(forms.ModelForm):
    """Alta y edición de clientes (HU-12 + cuenta corriente HU-14)."""

    class Meta:
        model = Cliente
        fields = [
            "nombre",
            "apellido",
            "dni",
            "telefono",
            "email",
            "limite_credito",
            "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(
                attrs={"class": "kiosco-input", "placeholder": "Nombre"}
            ),
            "apellido": forms.TextInput(
                attrs={"class": "kiosco-input", "placeholder": "Apellido"}
            ),
            "dni": forms.TextInput(
                attrs={
                    "class": "kiosco-input",
                    "placeholder": "Ej: 30123456",
                    "inputmode": "numeric",
                    "autocomplete": "off",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "kiosco-input",
                    "placeholder": "Ej: 11 5555-5555 (opcional)",
                    "autocomplete": "off",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "kiosco-input",
                    "placeholder": "email@ejemplo.com (opcional)",
                    "autocomplete": "off",
                }
            ),
            "limite_credito": forms.NumberInput(
                attrs={
                    "class": "kiosco-input",
                    "placeholder": "Ej: 20000 (0 = sin cuenta corriente)",
                    "inputmode": "decimal",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "dni": "DNI/CUIT",
            "limite_credito": "Límite de crédito (FIAR)",
            "activo": "Cliente activo",
        }
        help_texts = {
            "limite_credito": "Máximo que se le puede fiar. 0 = no tiene "
                              "cuenta corriente.",
        }

    def __init__(self, *args, **kwargs):
        self.cliente = kwargs.pop("cliente", None)
        super().__init__(*args, **kwargs)
        # El subclass de alta rápida no trae todos los campos.
        for campo in ("telefono", "email", "limite_credito"):
            if campo in self.fields:
                self.fields[campo].required = False
        if "limite_credito" in self.fields and not self.is_bound:
            self.fields["limite_credito"].initial = (
                self.instance.limite_credito
                if self.instance and self.instance.pk
                else Decimal("0.00")
            )

    def clean_dni(self):
        return _dni_normalizado(self.cleaned_data.get("dni"), self.cliente)

    def clean_limite_credito(self):
        limite = self.cleaned_data.get("limite_credito") or Decimal("0.00")
        if limite < 0:
            raise forms.ValidationError("El límite no puede ser negativo.")
        return limite


class ClienteRapidoForm(ClienteForm):
    """Ventanita rápida del cobro (HU-12): solo lo imprescindible."""

    class Meta(ClienteForm.Meta):
        fields = ["nombre", "apellido", "dni"]
        widgets = {
            campo: widget
            for campo, widget in ClienteForm.Meta.widgets.items()
            if campo in ("nombre", "apellido", "dni")
        }


class PagoCuentaCorrienteForm(forms.Form):
    """Cobro de un pago de la deuda del cliente (HU-14)."""

    monto = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "kiosco-input",
                "placeholder": "0.00",
                "inputmode": "decimal",
                "step": "0.01",
                "min": "0.01",
            }
        ),
        label="Monto del pago",
    )
    observacion = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "kiosco-input",
                "placeholder": "Observación (opcional)",
                "autocomplete": "off",
            }
        ),
        label="Observación",
    )

    def __init__(self, *args, cliente=None, **kwargs):
        self.cliente = cliente
        super().__init__(*args, **kwargs)

    def clean_monto(self):
        monto = self.cleaned_data.get("monto")
        if monto is None or monto <= 0:
            raise forms.ValidationError("El pago tiene que ser mayor a cero.")
        if self.cliente and monto > self.cliente.saldo_deuda:
            raise forms.ValidationError(
                f"El cliente debe ${montos(self.cliente.saldo_deuda)}: no "
                "podés cobrar más que eso."
            )
        return monto
