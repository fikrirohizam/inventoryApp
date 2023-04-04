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
   
class RestockGetSerializer2(serializers.Serializer):    
    materials = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        fields = ('materials', 'total_price')

    def get_materials(self, instance):
        return MaterialQuantitySerializer2(MaterialQuantity.objects.all(),many=True).data
    
    def get_total_price(self, instance):
        quantitysum = MaterialQuantity.objects.aggregate(result=Sum(F('ingredient__price')* F('quantity')))
        return next(iter(quantitysum.values()))
    
class RestockGetSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.name')
    material_price = serializers.DecimalField(source='material.price', max_digits=10, decimal_places=2)
    class Meta:
        model = MaterialStock
        fields = ['material_name', 'material_price', 'max_capacity', 'current_capacity']
        
class RestockPostSerializer(serializers.Serializer):
    material = serializers.IntegerField()
    quantity = serializers.IntegerField()

class MaterialStockSerializer(serializers.ModelSerializer):
    material_name = serializers.StringRelatedField(source='material.name')
    class Meta:
        model = MaterialStock
        fields = ('id','material','material_name','max_capacity','current_capacity',)
        read_only_fields = ['current_capacity', 'material',]

class InventoryMaterialStockSerializer(serializers.ModelSerializer):
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
        user = self.context["request"]
        return InventoryMaterialStockSerializer(MaterialStock.objects.filter(store__user__username= user),many=True).data

class MaterialQuantitySerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialQuantity
        fields = ['quantity', 'ingredient']

class ProductSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    material_quantity = MaterialQuantitySerializer(many=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'material_quantity']

"""     def create(self, validated_data):
        material_quantities_data = validated_data.pop('material_quantity')
        product = Product.objects.create(**validated_data)
        current_store = Store.objects.filter(user=self.context['request'].user).first()

        for material_quantity_data in material_quantities_data:
            quantity = material_quantity_data['quantity']
            material = material_quantity_data['material']
            material_quantity, created = MaterialQuantity.objects.get_or_create(quantity=quantity, material_id=material)
            if not created:
                existing_product = Product.objects.filter(product_stores=current_store, material_quantity=material_quantity).first()
                if existing_product:
                    product = existing_product
                else:
                    material_quantity.products.add(product)
            else:
                product.material_quantity.add(product)

        product.product_stores.add(current_store)
        return product """
    
class ProductCapacitySerializer(serializers.ModelSerializer):
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


class RestocksSerializer(serializers.Serializer):
    material = serializers.IntegerField()
    quantity = serializers.IntegerField()

    def validate_material(self, value):
        try:
            MaterialStock.objects.get(store=self.context['store'], material=value)
        except MaterialStock.DoesNotExist:
            raise serializers.ValidationError('Material stock not found.')
        return value
    

