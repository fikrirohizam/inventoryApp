from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from rest_framework.parsers import JSONParser
from rest_framework import viewsets, permissions
from .models import Material, MaterialQuantity, MaterialStock, Store, Product
from .serializers import ProductSerializer,UserSigninSerializer,StoreSerializer,RestockGetSerializer,RestockPostSerializer,SalesSerializer, InventorySerializer,MaterialStockSerializer
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import authentication, permissions
from rest_framework import exceptions
from rest_framework import mixins, reverse
from rest_framework import generics
from rest_framework import status
from rest_framework import routers
from rest_framework import renderers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .authentication import token_expire_handler, expires_in
from rest_framework.authtoken.models import Token
from rest_framework import serializers

from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_200_OK
)
# Create your views here.


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def login(request):
    signin_serializer = UserSigninSerializer(data = request.data)
    if not signin_serializer.is_valid():
        return Response(signin_serializer.errors, status = HTTP_400_BAD_REQUEST)

    user = authenticate(
            username = signin_serializer.data['username'],
            password = signin_serializer.data['password'] 
        )
    if not user:
        return Response({'detail': 'Invalid Credentials or activate account'}, status=HTTP_404_NOT_FOUND)
        
    #TOKEN STUFF
    token, _ = Token.objects.get_or_create(user = user)
    username = signin_serializer.data['username']
    #token_expire_handler will check, if the token is expired it will generate new one
    is_expired, token = token_expire_handler(token)     # The implementation will be described further

    return Response({
        'user': username, 
        'expires_in': expires_in(token),
        'token': token.key
    }, status=HTTP_200_OK)

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
    if request.method == 'GET':
        material = Material.objects.all()
        serializer = RestockGetSerializer(material)
        return Response(serializer.data)

    elif request.method == 'POST':
        current_store = Store.objects.get(user__username=request.user)
        material = Material.objects.get(material_id=int(request.data.get('material')))
        serializer = RestockPostSerializer(material, context={'quantity':int(request.data.get('quantity')), 'material':int(request.data.get('material'))})
        try:
            old_stock = MaterialStock.objects.get(store__store_name=current_store, material=request.data.get('material'))
            old_stock.current_capacity= int(request.data.get('quantity'))+old_stock.current_capacity
            old_stock.save()
            return Response(serializer.data, status=201)
        
        except MaterialStock.DoesNotExist:
            return Response("This material stock does not exist yet for this store. Please create new stock/")


@api_view(['GET',])
def inventory(request):
    """
    List all material stocks and % of capacity for a specific store, based on auth'ed user
    """
    if request.method == 'GET':
        materialstock = MaterialStock.objects.all()
        serializer = InventorySerializer(materialstock, context={'request':request})
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
        serializer = StoreSerializer(current_store, context={'currentstore':current_store})
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
            print(existing_material_stock)
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
            return Response({'error': 'Maximum capacity cannot be lower than current capacity.',
                             'accepted value:':'must NOT be lower than %s' % current_capacity}, status=status.HTTP_400_BAD_REQUEST)
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
        try:
            product_id = request.data.get('id')
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"message": "Product does not exist"}, status=400)

        current_store.products.add(product)
        serializer = ProductSerializer(product)
        return Response(serializer.data)
    
    def delete(self, request):
        current_store = Store.objects.filter(user__username=self.request.user).first()

        product_id = request.data.get("id")
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"message": "Product not found in current store"}, status=status.HTTP_404_NOT_FOUND)

        current_store.products.remove(product)
        return Response(status=status.HTTP_204_NO_CONTENT)
# Testing same restock view using modelviewset
class MaterialViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows material to be viewed or edited.
    """
    queryset = Material.objects.all()
    serializer_class = RestockGetSerializer