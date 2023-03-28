from django import forms
from .models import Product

class AddProductForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.all())

class DeleteProductForm(forms.Form):
    pass
