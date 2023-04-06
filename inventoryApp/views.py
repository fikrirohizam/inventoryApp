from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from inventoryApp import forms
from .models import MaterialStock, Store, Product
from inventoryApp import serializers as serializersapp
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework import generics
from django.views import generic
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .authentication import token_expire_handler, expires_in
from rest_framework.authtoken.models import Token
from django.contrib import messages
from rest_framework import serializers
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from django.db.models import F
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import logout
from django.http import JsonResponse

# Create your views here.


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def login_view(request):
    signin_serializer = serializersapp.UserSigninSerializer(data = request.data)
    if not signin_serializer.is_valid():
        return Response(signin_serializer.errors, status = status.HTTP_400_BAD_REQUEST)

    user = authenticate(
            username = signin_serializer.data['username'],
            password = signin_serializer.data['password'] 
        )
    if not user:
        return Response({'detail': 'Invalid Credentials or activate account'}, status=status.HTTP_404_NOT_FOUND)
        authentication_form
    #TOKEN STUFF
    token, _ = Token.objects.get_or_create(user = user)
    username = signin_serializer.data['username']
    #token_expire_handler will check, if the token is expired it will generate new one
    is_expired, token = token_expire_handler(token)     
    if is_expired:
        Token.objects.create(user = user)

    return Response({
        'user': username, 
        'expires_in': expires_in(token),
        'token': token.key
    }, status=status.HTTP_200_OK)

@csrf_exempt
def login_html_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            
            #TOKEN STUFF
            token, _ = Token.objects.get_or_create(user = user)
            #token_expire_handler will check, if the token is expired it will generate new one
            is_expired, token = token_expire_handler(token)     
            if is_expired:
                Token.objects.create(user = user)
                
            # Set key cookie
            response = redirect('store_products')
            response.set_cookie(key='key', value=token.key, httponly=True)
            return response
        else:
            return JsonResponse({'status': 'Login failed', 'error': 'Invalid Credentials or activate account'})
    else:
        return render(request, 'login.html')
    
def logout_view(request):
    logout(request)
    return redirect('html_login')

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

        serializer = serializersapp.RestockGetSerializer(current_store.stocks.all(), many=True)

        return Response(serializer.data)

    elif request.method == 'POST':
        current_store = Store.objects.filter(user__username=request.user).first()
        serializer = serializersapp.RestockPostSerializer(data=request.data)
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
        serializer = serializersapp.InventorySerializer(materialstock, context={'request':request.user})
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
        serializer = serializersapp.ProductCapacitySerializer(current_store)
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
        serializer = serializersapp.SalesSerializer(data=request.data, context={'store':current_store})
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
        queryset = MaterialStock.objects.filter(store=current_store).order_by('pk')
        return queryset

    def get_serializer_class(self):
        # enable adding current_capacity value when creating new MaterialStock
        current_store = Store.objects.filter(user__username=self.request.user).first()
        class NewMaterialStockSerializer(serializersapp.MaterialStockSerializer):
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
        
        if current_store is None or material is None:
            return super().create(request, *args, **kwargs)

        existing_material_stock = MaterialStock.objects.filter(store=current_store, material=material).first()
        if existing_material_stock:
            return Response({
                'error': "This material stock already exists in this store. Please use other material or update existing stock."
            }, status=status.HTTP_400_BAD_REQUEST)

        if max_cap < current_cap:
            return Response({
                'error': "Max capacity must not be lower than current capacity."
            }, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)

class MaterialStockDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = serializersapp.MaterialStockSerializer

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
    serializer_class = serializersapp.ProductSerializer

    def get_queryset(self):
        current_store = Store.objects.filter(user__username=self.request.user).first()
        queryset = Product.objects.filter(product_stores=current_store).order_by('pk')
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
            serializer = serializersapp.ProductSerializer(product)
            return Response({"success": "Product has been assigned to this store", "product":serializer.data},status=status.HTTP_200_OK)
        
class ProductDeleteAPIView(generics.RetrieveDestroyAPIView):
    serializer_class = serializersapp.ProductSerializer

    def update(self, request, *args, **kwargs):
        return Response({'error':'Update product is not allowed'},status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def get_queryset(self):
        current_store = Store.objects.filter(user__username=self.request.user).first()
        queryset = Product.objects.filter(product_stores=current_store).order_by('pk')
        return queryset
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        current_store = Store.objects.filter(user__username=self.request.user).first()
        if instance.product_stores.filter(pk=current_store.pk).exists():
            instance.product_stores.remove(current_store)
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)
    
    def perform_destroy(self, instance):
        instance.delete()

# Allow multiple material restocking in a single JSON POST request using dict list
@api_view(['GET', 'POST'])
def restocks(request):
    """
    List all material stocks, price for restocking, and amount of restocks.
    """
    current_store = Store.objects.filter(user__username=request.user).first()
    if request.method == 'GET':
        material_stocks = MaterialStock.objects.filter(store=current_store)
        response_data = {'materials': []}
        overall_price = 0
        for material_stock in material_stocks:
            added_quantity = material_stock.max_capacity - material_stock.current_capacity
            if added_quantity == 0:
                continue            
            material = material_stock.material
            total_price = added_quantity * material.price
            overall_price += total_price
            response_data['materials'].append({
                'material': material.pk,
                'price' : material.price,
                'restock quantity': added_quantity,
                'current_capacity': f"{material_stock.current_capacity}/{material_stock.max_capacity}",
                'total_price': total_price,
            })
            response_data['overall_price'] = overall_price

        if len(response_data.get('materials')) == 0:
            return Response("All material stocks for this store are already full.", status=status.HTTP_204_NO_CONTENT)
        
        return Response(response_data, status=status.HTTP_200_OK)

    elif request.method == 'POST':
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
                material = material_stock.material
                material_stock.save(update_fields=['current_capacity'])
                total_price = added_quantity * material.price
                overall_price += total_price
                response_data['materials'].append({
                    'material': material.pk,
                    'quantity': added_quantity,
                    'current_capacity': material_stock.current_capacity,
                    'total_price': total_price,
                })
                response_data['overall_price'] = overall_price
        
        else:
            # if user specify which material stocks to update, update current_capacity of specified stocks based on given material and quantity.
            serializer = serializersapp.RestocksSerializer(data=request.data['materials'], many=True, context={'store': current_store})

            if not serializer.is_valid():
                error_data = {'error': 'Restocks request failed due to invalid data. Please review the following list of invalid restocks',
                              'materials': serializer.errors}
                return Response(error_data, status=status.HTTP_400_BAD_REQUEST)
                        
            overall_price = 0
            response_data = {'materials': []}
            for material_data in serializer.validated_data:
                material_id = material_data['material']
                added_quantity = material_data['quantity']
                material_stock = MaterialStock.objects.filter(store=current_store, material=material_id).first()
                if material_stock is None:
                    return Response({'error': 'Material stock not found.'}, status=status.HTTP_404_NOT_FOUND)
                
                new_capacity = material_stock.current_capacity + added_quantity
                if new_capacity > material_stock.max_capacity:
                    response_data['materials'].append({
                    'material': material_id,
                    'quantity': added_quantity,
                    'current_capacity': f"{material_stock.current_capacity}/{material_stock.max_capacity}",
                    'error': 'Restock for this material failed. Adding this amount would exceed maximum capacity.',
                    })
                    continue
                material_stock.current_capacity = new_capacity
                material = material_stock.material
                material_stock.save(update_fields=['current_capacity'])
                total_price = added_quantity * material.price
                overall_price += total_price
                response_data['materials'].append({
                    'material': material_id,
                    'quantity': added_quantity,
                    'current_capacity': f"{material_stock.current_capacity}/{material_stock.max_capacity}",
                    'total_price': total_price,
                })
            response_data['overall_price'] = overall_price
        return Response(response_data, status=status.HTTP_200_OK)

# Allow multiple product sales in a single JSON POST request using dict list
@api_view(['POST'])
def multisales(request):
    current_store = Store.objects.filter(user__username=request.user).first()
    serializer = serializersapp.SalesSerializer(data=request.data['sales'], context={'store':current_store}, many=True)

    if not serializer.is_valid():
        error_data = {'error': 'Sales request failed due to invalid data. Please review the following list of invalid sales',
                      'sales': serializer.errors}
        return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

    # Loop through each product and subtract the required material from the stock
    for sale in serializer.validated_data:
        response_data = {'sales':[]}
        product = get_object_or_404(Product, id=sale['product_id'])
        for material_quantity in product.material_quantity.all():
            material = material_quantity.ingredient
            stock = get_object_or_404(MaterialStock, store=current_store, material=material)
            if stock.current_capacity < material_quantity.quantity * sale['quantity']:
                return Response({'error':'Insufficient material stock'}, status=status.HTTP_400_BAD_REQUEST)
            
            stock.current_capacity -= material_quantity.quantity * sale['quantity']
            response_data['sales'].append({
                'product_id' : sale['product_id'],
                'quantity' : sale['quantity'],
                'success' : 'Material stock subtracted successfully',
                })
            stock.save()

    return Response(response_data, status=status.HTTP_200_OK)

#///////////////////////////////////////////////////////////////
#----------------HTML VIEW---------------------------------------

@login_required(login_url='html_login')
def store_products(request):
    current_store = Store.objects.filter(user__username=request.user).first()
    products = current_store.products.all()
    available_products = Product.objects.exclude(product_stores=current_store)
    return render(request, 'store_products.html', {
        'store': current_store,
        'products': products,
        'available_products': available_products,
    })

def add_product(request):
    current_store = Store.objects.filter(user__username=request.user).first()
    if request.method == 'POST':
        form = forms.AddProductForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            current_store.products.add(product)
            return redirect('store_products')
    else:
        form = forms.AddProductForm()
    return render("Something went wrong when adding product.")

def delete_product(request, product_id):
    current_store = Store.objects.filter(user__username=request.user).first()
    product = get_object_or_404(Product, pk=product_id, product_stores=current_store)
    if request.method == 'POST':
        form = forms.DeleteProductForm(request.POST)
        if form.is_valid():
            current_store.products.remove(product)
            return redirect('store_products')
    else:
        form = forms.DeleteProductForm()
    return render("Something went wrong when deleting product.")

class MaterialStockView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'material_stocks.html'
    login_url = 'html_login'

    def get_context_data(self, **kwargs):
        current_store = Store.objects.filter(user__username=self.request.user).first()
        context = super().get_context_data(**kwargs)
        material_stocks = MaterialStock.objects.filter(store=current_store)
        context['store'] = current_store
        context['material_stocks'] = material_stocks
        return context
    
class MaterialStockCreateView(generic.CreateView):
    model = MaterialStock
    form_class = forms.MaterialStockAddForm
    template_name = 'material_stock_form.html'

    def form_valid(self, form):
        store = Store.objects.get(pk=self.kwargs['store_id'])
        material = form.cleaned_data['material']
        if MaterialStock.objects.filter(store=store, material=material).exists():
            form.add_error('material', 'Material stock already exists for this store and material.')
            return self.form_invalid(form)
        material_stock = form.save(commit=False)
        material_stock.store = store
        material_stock.save()
        return super().form_valid(form)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['store_id'] = self.kwargs['store_id']
        return kwargs
    
    def get_success_url(self):
        return reverse_lazy('store_stocks')
    
class MaterialStockUpdateView(generic.UpdateView):
    model = MaterialStock
    form_class = forms.MaterialStockUpdateForm
    template_name = 'material_stock_form.html'
    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('store_stocks')

class MaterialStockDeleteView(generic.DeleteView):
    model = MaterialStock
    template_name = 'material_stock_delete.html'
    def get_success_url(self):
        return reverse_lazy('store_stocks')


