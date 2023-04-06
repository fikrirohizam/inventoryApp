from django import forms
from .models import Product, MaterialStock, Material, Store

class AddProductForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.all())

class DeleteProductForm(forms.Form):
    pass

class MaterialStockUpdateForm(forms.ModelForm):
    class Meta:
        model = MaterialStock
        fields = ['max_capacity']

    def clean_max_capacity(self):
        max_capacity = self.cleaned_data.get('max_capacity')
        current_capacity = self.instance.current_capacity
        if max_capacity < current_capacity:
            raise forms.ValidationError("Max capacity cannot be lower than current capacity.")
        return max_capacity
    
class MaterialStockAddForm(forms.ModelForm):
    class Meta:
        model = MaterialStock
        exclude = ['store']

    def __init__(self, *args, **kwargs):
        store_id = kwargs.pop('store_id', None)
        super().__init__(*args, **kwargs)
        if store_id:
            store = Store.objects.get(pk=store_id)
            used_material_ids = store.stocks.values_list('material__material_id', flat=True)
            available_materials = Material.objects.exclude(material_id__in=used_material_ids)
            if available_materials:
                self.fields['material'].queryset = available_materials
            else:
                self.fields['material'].widget = forms.HiddenInput()
                self.message = "This store already has material stock for all currently available materials. Please update existing stock instead."
            self.initial['store'] = store_id
            
    def clean(self):
        current_capacity = self.cleaned_data.get('current_capacity')
        max_capacity = self.cleaned_data.get('max_capacity')
        if current_capacity > max_capacity:
            raise forms.ValidationError("Current capacity cannot be higher than max capacity.")
        return self.cleaned_data