from rest_framework import viewsets 
from .models import Material, MaterialStock, Store, Product
from .serializers import ProductSerializer,RestocksSerializer,UserSigninSerializer,ProductCapacitySerializer,RestockGetSerializer,RestockPostSerializer,SalesSerializer, InventorySerializer,MaterialStockSerializer
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import generics
from django.views import generic
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .authentication import token_expire_handler, expires_in
from rest_framework.authtoken.models import Token
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from django.db.models import F
# Create your views here.


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def login(request):
    signin_serializer = UserSigninSerializer(data = request.data)
    if not signin_serializer.is_valid():
        return Response(signin_serializer.errors, status = status.HTTP_400_BAD_REQUEST)

    user = authenticate(
            username = signin_serializer.data['username'],
            password = signin_serializer.data['password'] 
        )
    if not user:
        return Response({'detail': 'Invalid Credentials or activate account'}, status=status.HTTP_404_NOT_FOUND)
        
    #TOKEN STUFF
    token, _ = Token.objects.get_or_create(user = user)
    username = signin_serializer.data['username']
    #token_expire_handler will check, if the token is expired it will generate new one
    is_expired, token = token_expire_handler(token)     # The implementation will be described further

    return Response({
        'user': username, 
        'expires_in': expires_in(token),
        'token': token.key
    }, status=status.HTTP_200_OK)

class CustomAuthToken(ObtainAuthToken):

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email
        })
    

@api_view(['GET', 'POST'])
def restock(request):
    """
    List all materials, quantity, and total price, or create a new one (restock).
    """
    current_store = Store.objects.get(user__username=request.user)
    if request.method == 'GET':

        serializer = RestockGetSerializer(current_store.stocks.all(), many=True)

        return Response(serializer.data)

    elif request.method == 'POST':
        current_store = Store.objects.filter(user__username=request.user).first()
        serializer = RestockPostSerializer(data=request.data)
        if serializer.is_valid():
            material_id = serializer.validated_data['material']
            add_value = serializer.validated_data['quantity']
            try:
                material_stock = MaterialStock.objects.get(store=current_store, material=material_id)
            except MaterialStock.DoesNotExist:
                return Response({'error': 'Material stock not found.'}, status=status.HTTP_404_NOT_FOUND)
            new_capacity = material_stock.current_capacity + add_value
            if new_capacity > material_stock.max_capacity:
                return Response({'error': 'Adding this amount would exceed maximum capacity.'}, status=status.HTTP_400_BAD_REQUEST)
            material_stock.current_capacity = new_capacity
            material = material_stock.material
            material_stock.save()
            total_price = add_value * material.price
            response_data = {
                'material': material_id,
                'quantity': add_value,
                'current_capacity': new_capacity,
                'total_price': total_price,
            }
            return Response(response_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET',])
def inventory(request):
    """
    List all material stocks and % of capacity for a specific store, based on auth'ed user
    """
    if request.method == 'GET':
        materialstock = MaterialStock.objects.all()
        serializer = InventorySerializer(materialstock, context={'request':request.user})
        return Response(serializer.data)
    
@api_view(['GET',])
def product_capacity(request):
    """
    List the products in the store and quantity of product available to
    be produced based on available stocks
    """
    if request.method == 'GET':
        current_store = Store.objects.filter(user__username=request.user).first()
        materialstock = Product.objects.all()
        serializer = ProductCapacitySerializer(current_store, context={'currentstore':current_store})
        return Response(serializer.data)
     
@api_view(['POST'])
def sales(request):
    """
    Post product sold and quantity of product, which then
    reduces the material stocks related to the product based
    on how much material it needs, and how much product is sold
    """
    if request.method == 'POST':
        current_store = Store.objects.filter(user__username=request.user).first()
        serializer = SalesSerializer(data=request.data, context={'store':current_store})
        if serializer.is_valid():
            product_id = serializer.validated_data['product_id']
            quantity = serializer.validated_data['quantity']

            # Get the store and product objects
            try:
                product = Product.objects.get(id=product_id)
            except (Product.DoesNotExist):
                return Response({'error': 'Invalid product id'}, status=status.HTTP_400_BAD_REQUEST)

            # Loop through each MaterialQuantity object and subtract the material from the stock
            for material_quantity in product.material_quantity.all():
                material = material_quantity.ingredient
                try:
                    stock = MaterialStock.objects.get(store=current_store, material=material)
                except MaterialStock.DoesNotExist:
                    return Response({'error': 'Store does not have the required material in stock'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    if stock.current_capacity < material_quantity.quantity * quantity:
                        return Response({'error': 'Insufficient material stock'}, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        stock.current_capacity -= material_quantity.quantity * quantity
                        stock.save()

            return Response({'success': 'Material stock subtracted successfully'})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MaterialStockListAPIView(generics.ListCreateAPIView):
    
    def get_queryset(self):
        current_store = Store.objects.filter(user__username=self.request.user).first()
        queryset = MaterialStock.objects.filter(store=current_store)
        return queryset

    def get_serializer_class(self):
        # enable adding current_capacity value when creating new MaterialStock
        current_store = Store.objects.filter(user__username=self.request.user).first()
        class NewMaterialStockSerializer(MaterialStockSerializer):
            store = serializers.HiddenField(
                default=current_store
            )
            class Meta:
                model = MaterialStock
                fields = '__all__'
            
        return NewMaterialStockSerializer

    def create(self, request, *args, **kwargs):
        current_store = Store.objects.filter(user__username= request.user).first()
        material = request.data.get('material', None)
        current_cap = request.data.get('current_capacity')
        max_cap = request.data.get('max_capacity')
        if current_store is not None and material is not None:
            existing_material_stock = MaterialStock.objects.filter(store=current_store, material=material).first()
            if existing_material_stock:
                return Response({'error': "This material stock already exists in this store. Please use other material or update existing stock."}, status= status.HTTP_400_BAD_REQUEST)
            elif max_cap < current_cap:
                return Response({'error': "Max capacity must NOT be lower than current capacity."}, status= status.HTTP_400_BAD_REQUEST)
            else:
                serializer = self.get_serializer(existing_material_stock)
                Response(serializer.data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)

class MaterialStockDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MaterialStockSerializer

    def get_queryset(self):
        current_store = Store.objects.filter(user__username=self.request.user).first()
        queryset = MaterialStock.objects.filter(store=current_store)
        return queryset
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        current_capacity = int(instance.current_capacity) # get current_capacity value from existing object
        max_capacity = int(request.data.get('max_capacity', instance.max_capacity))
        if current_capacity > max_capacity:
            return Response({'error': 'Maximum capacity cannot be lower than current capacity.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

class ProductListAPIView(generics.ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        current_store = Store.objects.filter(user__username=self.request.user).first()
        queryset = Product.objects.filter(product_stores=current_store)
        return queryset
        
    def post(self, request):
        current_store = Store.objects.filter(user__username=self.request.user).first()
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({'error': " 'product_id' value is not given."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product does not exist"}, status=404) 
        try:
            existing_product = Store.objects.get(store_id= current_store.pk, products=product)
            return Response({"error": "Product already assigned to this store"}, status=status.HTTP_400_BAD_REQUEST) 
        except Store.DoesNotExist:
            current_store.products.add(product)
            serializer = ProductSerializer(product)
            return Response({"success": "Product has been assigned to this store", "product":serializer.data},status=status.HTTP_200_OK)
        
           
    """ 
    def create(self, request):
        current_store = Store.objects.filter(user__username=self.request.user).first()
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(store=current_store)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    """
    def delete(self, request):
        current_store = Store.objects.filter(user__username=self.request.user).first()

        product_id = request.data.get("product_id")
        if not product_id:
            return Response({'error': " 'product_id' value is not given."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product does not exist"}, status=400)
        try:
            existing_product = Store.objects.get(store_id= current_store.pk, products=product)
            current_store.products.remove(product)
            return Response({"success": "Product has been removed from store"},status=status.HTTP_200_OK)
        except Store.DoesNotExist:
            return Response({"error": "This product is not available in this store."},status=status.HTTP_204_NO_CONTENT)

# Allow multiple material restocking in a single JSON POST request using dict list
@api_view(['POST'])
def restocks(request):
    current_store = Store.objects.filter(user__username=request.user).first()
    if not request.data.get('materials'):
        # If user doesn't specify which materials to update, update current_capacity of all MaterialStock objects to their max_capacity
        material_stocks = MaterialStock.objects.filter(store=current_store)
        response_data = {'materials': []}
        overall_price = 0
        for material_stock in material_stocks:
            added_quantity = material_stock.max_capacity - material_stock.current_capacity
            if added_quantity == 0:
                continue
            material_stock.current_capacity = material_stock.max_capacity
            material_stock.save()
            material = material_stock.material
            overall_price += added_quantity * material.price
            response_data['materials'].append({
                'material': material.pk,
                'quantity': added_quantity,
                'current_capacity': material_stock.current_capacity,
                'total_price': added_quantity * material.price,
            })
            response_data['overall_price'] = overall_price
    
    else:
        # if user specify which material stocks to update, update current_capacity of specified stocks based on given material and quantity.
        serializer = RestocksSerializer(data=request.data['materials'], many=True, context={'store': current_store})
        if serializer.is_valid():
            overall_price = 0
            response_data = {'materials': []}
            for material_data in serializer.validated_data:
                material_id = material_data['material']
                added_quantity = material_data['quantity']
                material_stock = MaterialStock.objects.get(store=current_store, material=material_id)
                new_capacity = material_stock.current_capacity + added_quantity
                if new_capacity > material_stock.max_capacity:
                    return Response({'error': 'Adding this amount would exceed maximum capacity.'}, status=status.HTTP_400_BAD_REQUEST)
                material_stock.current_capacity = new_capacity
                material = material_stock.material
                material_stock.save()
                overall_price += added_quantity * material.price
                response_data['materials'].append({
                    'material': material_id,
                    'quantity': added_quantity,
                    'current_capacity': material_stock.current_capacity,
                    'total_price': added_quantity * material.price,
                })
            response_data['overall_price'] = overall_price
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    return Response(response_data, status=status.HTTP_200_OK)

# Allow multiple product sales in a single JSON POST request using dict list
@api_view(['POST'])
def multisales(request):
    if request.method == 'POST':
        current_store = Store.objects.filter(user__username=request.user).first()
        serializer = SalesSerializer(data=request.data['sales'], context={'store':current_store}, many=True)
        if serializer.is_valid():
            # Loop through each product and subtract the required material from the stock
            for sale in serializer.validated_data:
                product_id = sale['product_id']
                quantity = sale['quantity']
                try:
                    product = Product.objects.get(id=product_id)
                except (Product.DoesNotExist):
                    return Response({'error': 'Invalid product id'}, status=status.HTTP_400_BAD_REQUEST)

                for material_quantity in product.material_quantity.all():
                    material = material_quantity.ingredient
                    try:
                        stock = MaterialStock.objects.get(store=current_store, material=material)
                    except MaterialStock.DoesNotExist:
                        return Response({'error': 'Store does not have the required material in stock'}, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        if stock.current_capacity < material_quantity.quantity * quantity:
                            return Response({'error': 'Insufficient material stock'}, status=status.HTTP_400_BAD_REQUEST)
                        else:
                            stock.current_capacity -= material_quantity.quantity * quantity
                            stock.save()

            return Response({'success': 'Material stock subtracted successfully'})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)














