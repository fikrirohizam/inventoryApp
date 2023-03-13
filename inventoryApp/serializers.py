from django.forms import DateInput, FloatField
from .models import Material,MaterialQuantity
from rest_framework import serializers
from django.db.models import Sum
from django.db.models import F

class MaterialQuantitySerializer2(serializers.ModelSerializer):
    material = serializers.SerializerMethodField()

    class Meta:
        model = MaterialQuantity
        fields = ('material','quantity',)

    def get_material(self,obj):
        return obj.ingredient.material_id
    
class MaterialSerializer(serializers.ModelSerializer):
    materials = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Material
        fields = ('materials', 'total_price')

    def get_materials(self, instance):
        return MaterialQuantitySerializer2(MaterialQuantity.objects.all(),many=True).data
    
    def get_total_price(self, instance):
        test = MaterialQuantity.objects.aggregate(result=Sum(F('ingredient__price')* F('quantity')))
        return test