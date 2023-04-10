from inventoryApp import models
from rest_framework import serializers
from django.db.models import Sum
from django.db.models import F

class UserSigninSerializer(serializers.Serializer):
    username = serializers.CharField(required = True)
    password = serializers.CharField(required = True)
    
class MaterialQuantitySerializer2(serializers.ModelSerializer):
    material = serializers.SerializerMethodField()

    class Meta:
        model = models.MaterialQuantity
        fields = ('material','quantity',)

    def get_material(self,obj):
        return obj.ingredient.material_id
   
class RestockGetSerializer2(serializers.Serializer):    
    materials = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        fields = ('materials', 'total_price')

    def get_materials(self, instance):
        return MaterialQuantitySerializer2(models.MaterialQuantity.objects.all(),many=True).data
    
    def get_total_price(self, instance):
        quantitysum = models.MaterialQuantity.objects.aggregate(result=Sum(F('ingredient__price')* F('quantity')))
        return next(iter(quantitysum.values()))
    
class RestockGetSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.name')
    material_price = serializers.DecimalField(source='material.price', max_digits=10, decimal_places=2)
    class Meta:
        model = models.MaterialStock
        fields = ['material_name', 'material_price', 'max_capacity', 'current_capacity']
        
class RestockPostSerializer(serializers.Serializer):
    material = serializers.IntegerField()
    quantity = serializers.IntegerField()

class MaterialStockSerializer(serializers.ModelSerializer):
    material_name = serializers.StringRelatedField(source='material.name')
    class Meta:
        model = models.MaterialStock
        fields = ('id','material','material_name','max_capacity','current_capacity',)
        read_only_fields = ['current_capacity', 'material',]

class InventoryMaterialStockSerializer(serializers.ModelSerializer):
    material = serializers.SerializerMethodField()
    material_name = serializers.StringRelatedField(source='material.name')
    percentage_of_capacity = serializers.ReadOnlyField()
    class Meta:
        model = models.MaterialStock
        fields = ('material', 'material_name', 'max_capacity','current_capacity', 'percentage_of_capacity')
    def get_material(self,obj):
        return obj.material.material_id
    
class InventorySerializer(serializers.Serializer):
    materials = serializers.SerializerMethodField()
    class Meta:
        fields = ('materials', )
        
    def get_materials(self, instance):
        user = self.context["request"]
        return InventoryMaterialStockSerializer(models.MaterialStock.objects.filter(store__user__username= user),many=True).data

class MaterialQuantitySerializer(serializers.ModelSerializer):
    ingredient_name = serializers.StringRelatedField(source='ingredient.name')
    class Meta:
        model = models.MaterialQuantity
        fields = ['quantity', 'ingredient', 'ingredient_name']

class ProductSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    material_quantity = MaterialQuantitySerializer(many=True)

    class Meta:
        model = models.Product
        fields = ['id', 'name', 'material_quantity']
    
class ProductCapacitySerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True)
    remaining_capacities = serializers.SerializerMethodField()

    class Meta:
        model = models.Store
        fields = ['store_name', 'products', 'remaining_capacities']

    def get_remaining_capacities(self, store):
        material_stocks = models.MaterialStock.objects.filter(store=store)
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
            product = models.Product.objects.get(id=product_id)
        except (models.Product.DoesNotExist):
            raise serializers.ValidationError({'product_id': product_id, 
                                               'non_field_errors': 'Invalid product id'})

        for material_quantity in product.material_quantity.all():
            material = material_quantity.ingredient
            try:
                stock = models.MaterialStock.objects.get(store=self.context['store'], material=material)
            except models.MaterialStock.DoesNotExist:
                raise serializers.ValidationError({'product_id': product_id, 
                                                   'non_field_errors': 'Store does not have the required material in stock'})
            
            if stock.current_capacity < material_quantity.quantity * data['quantity']:
                raise serializers.ValidationError({'product_id': product_id, 
                                                   'non_field_errors': 'Insufficient material stock'})

        return data


class MultipleRestocksSerializer(serializers.Serializer):
    material = serializers.IntegerField()
    quantity = serializers.IntegerField()

    def validate(self, data):
        material = data.get('material')
        quantity = data.get('quantity')
        
        try:
            material_stock = models.MaterialStock.objects.get(store=self.context['store'], material=material)
        except models.MaterialStock.DoesNotExist:
            raise serializers.ValidationError({'material': material,
                                               'quantity': quantity,
                                               'non_field_errors': 'Invalid product id'})
        
        if quantity + material_stock.current_capacity > material_stock.max_capacity:
            raise serializers.ValidationError({'material': material,
                                               'quantity': quantity,
                                               'non_field_errors': 'The quantity to be restocked is more than the maximum capacity of the material stock.'})

        return data
    
class GetRestocksSerializer(serializers.ModelSerializer):
    material = serializers.PrimaryKeyRelatedField(queryset=models.Material.objects.all())
    material_name = serializers.StringRelatedField(source='material.name')
    quantity = serializers.SerializerMethodField()
    capacity = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = models.MaterialStock
        fields = ('material', 'material_name', 'quantity', 'capacity', 'total_price')

    def get_quantity(self, obj):
        quantity = obj.max_capacity - obj.current_capacity
        return quantity if quantity > 0 else 0
    
    def get_capacity(self, obj):
        return f'{obj.current_capacity}/{obj.max_capacity}'
    
    def get_total_price(self, obj):
        return obj.material.price * self.get_quantity(obj)
