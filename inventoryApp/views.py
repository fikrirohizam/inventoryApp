from django.http import HttpResponse, JsonResponse
from rest_framework.parsers import JSONParser
from rest_framework import viewsets, permissions
from .models import Material, MaterialQuantity, MaterialStock, Store
from .serializers import RestockSerializer, InventorySerializer, ProductCapacitySerializer
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import authentication, permissions
from rest_framework import exceptions
from rest_framework import mixins
from rest_framework import generics
from rest_framework import status
from rest_framework import routers
from rest_framework import renderers
from rest_framework.decorators import action
from rest_framework.response import Response

from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
# Create your views here.

@api_view(['GET', 'POST'])
def restock(request):
    """
    List all materials, quantity, and total price, or create a new one (restock).
    """
    if request.method == 'GET':
        material = Material.objects.all()
        serializer = RestockSerializer(material)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = RestockSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
    List all material stocks for a specific shop, based on auth user
    """
    if request.method == 'GET':
        materialstock = Store.objects.all()
        serializer = ProductCapacitySerializer(materialstock, context={'request':request}, many=True)
        return Response(serializer.data)
     
# Testing same restock view using modelviewset
class MaterialViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows material to be viewed or edited.
    """
    queryset = Material.objects.all()
    serializer_class = RestockSerializer