from django.forms import DateInput, FloatField
from .models import Material, MaterialQuantity, MaterialStock, Store, Product
from rest_framework import serializers
from django.db.models import Sum
from django.db.models import F

class MaterialQuantitySerializer(serializers.ModelSerializer):
    material = serializers.SerializerMethodField()

    class Meta:
        model = MaterialQuantity
        fields = ('material','quantity',)

    def get_material(self,obj):
        return obj.ingredient.material_id
    
class RestockSerializer(serializers.Serializer):
    materials = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        fields = ('materials', 'total_price')

    def get_materials(self, instance):
        return MaterialQuantitySerializer(MaterialQuantity.objects.all(),many=True).data
    
    def get_total_price(self, instance):
        test = MaterialQuantity.objects.aggregate(result=Sum(F('ingredient__price')* F('quantity')))
        return test
    
class MaterialStockSerializer(serializers.ModelSerializer):
    material = serializers.SerializerMethodField()
    percentage_of_capacity = serializers.ReadOnlyField()
    class Meta:
        model = MaterialStock
        fields = ('material','max_capacity','current_capacity', 'percentage_of_capacity')
    def get_material(self,obj):
        return obj.id
class InventorySerializer(serializers.Serializer):
    materials = serializers.SerializerMethodField()
    class Meta:
        fields = ('materials', )
        
    def get_materials(self, instance):
        user = self.context["request"].user
        return MaterialStockSerializer(MaterialStock.objects.filter(store__user__username= user),many=True).data
    

class StoreProductSerializer(serializers.ModelSerializer):
    product = serializers.IntegerField(source='id')
    quantity = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = ('product', 'quantity')

    def get_quantity(self, obj):
        #product = Product.objects.filter(id=obj.id).values()
        product = Sum(F('stocks__current_capacity')-F('products__material_quantity__quantity'))
        return Store.objects.filter(products__id=obj.id).aggregate(quantity=product)
    
class ProductCapacitySerializer(serializers.ModelSerializer):
    remaining_capacities = StoreProductSerializer(source="products", many=True, read_only=True)
    class Meta:
        model=Store
        fields = ('remaining_capacities',  )
        
