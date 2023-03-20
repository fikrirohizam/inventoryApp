from django.forms import DateInput, FloatField
from .models import Material, MaterialQuantity, MaterialStock, Store, Product
from rest_framework import serializers
from django.db.models import Sum
from django.db.models import F, Value
from django.db.models.functions import Coalesce
from django.db.models import OuterRef, Subquery

class UserSigninSerializer(serializers.Serializer):
    username = serializers.CharField(required = True)
    password = serializers.CharField(required = True)
    
class MaterialQuantitySerializer2(serializers.ModelSerializer):
    material = serializers.SerializerMethodField()

    class Meta:
        model = MaterialQuantity
        fields = ('material','quantity',)

    def get_material(self,obj):
        return obj.ingredient.material_id
   
class RestockGetSerializer(serializers.Serializer):    
    materials = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        fields = ('materials', 'total_price')

    def get_materials(self, instance):
        return MaterialQuantitySerializer2(MaterialQuantity.objects.all(),many=True).data
    
    def get_total_price(self, instance):
        quantitysum = MaterialQuantity.objects.aggregate(result=Sum(F('ingredient__price')* F('quantity')))
        return next(iter(quantitysum.values()))

class RestockPostSerializer(serializers.Serializer):
    material = serializers.SerializerMethodField()
    quantity = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    class Meta:
        fields = ('material', 'total_price')

    def get_quantity(self, instance):
        return self.context['quantity']
    
    def get_material(self, instance):
        return self.context['material']
    
    def get_total_price(self, instance):
        quantitysum = Material.objects.filter(material_id=self.context['material']).aggregate(result=Sum(F('price')* self.context['quantity']))
        return next(iter(quantitysum.values()))

class MaterialStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialStock
        fields = ('id','material','max_capacity','current_capacity',)
        read_only_fields = ['current_capacity', 'material',]

class MaterialStockSerializer2(serializers.ModelSerializer):
    material = serializers.SerializerMethodField()
    percentage_of_capacity = serializers.ReadOnlyField()
    class Meta:
        model = MaterialStock
        fields = ('material','max_capacity','current_capacity', 'percentage_of_capacity')
    def get_material(self,obj):
        return obj.material.material_id
    
class InventorySerializer(serializers.Serializer):
    materials = serializers.SerializerMethodField()
    class Meta:
        fields = ('materials', )
        
    def get_materials(self, instance):
        user = self.context["request"].user
        return MaterialStockSerializer2(MaterialStock.objects.filter(store__user__username= user),many=True).data

class MaterialQuantitySerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialQuantity
        fields = ['quantity', 'ingredient']

class ProductSerializer(serializers.ModelSerializer):
    material_quantity = MaterialQuantitySerializer(many=True)

    class Meta:
        model = Product
        fields = ['name', 'material_quantity']
class StoreSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True)
    material_stock = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = ['store_name', 'products', 'material_stock']

    def get_material_stock(self, store):
        material_stocks = MaterialStock.objects.filter(store=store)
        product_data = []

        for product in store.products.all():
            product_material_data = []

            for mq in product.material_quantity.all():
                material = mq.ingredient
                material_stocks_for_material = material_stocks.filter(material=material)
                total_quantity = mq.quantity
                current_capacity = sum(ms.current_capacity for ms in material_stocks_for_material)
                product_quantity = int(current_capacity/total_quantity)

                product_material_data.append({
                    'material_name': material.name,
                    'stock_capacity': current_capacity,
                    'material_quantity_each': total_quantity,
                    'product_quantity': product_quantity
                })
                
            product_material_data_lowest = min(product_material_data, key=lambda x:x['product_quantity'])
            product_data.append({
                'product_name': product.name,
                'product_material_with_lowest_stock': product_material_data_lowest
            })

        return product_data
    
class SalesSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, data):
        product_id = data.get('product_id')

        try:
            product = Product.objects.get(id=product_id)
        except (Product.DoesNotExist):
            raise serializers.ValidationError('Invalid product id')

        for material_quantity in product.material_quantity.all():
            material = material_quantity.ingredient
            try:
                stock = MaterialStock.objects.get(store=self.context['store'], material=material)
            except MaterialStock.DoesNotExist:
                raise serializers.ValidationError('Store does not have the required material in stock')
            else:
                if stock.current_capacity < material_quantity.quantity * data['quantity']:
                    raise serializers.ValidationError('Insufficient material stock')
        
        return data

        