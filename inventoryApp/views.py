from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from inventoryApp import forms
from inventoryApp import serializers as serializersapp
from rest_framework import generics, serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .authentication import expires_in, token_expire_handler
from .models import MaterialStock, Product, Store

#===============================================================
#                   login, logout and token
#===============================================================

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
    

#===============================================================
#                       DRF Views
#===============================================================

#----------------------- inventory view -------------------------------
@api_view(['GET',])
def inventory(request):
    """
    List all material stocks and % of capacity for a specific store, based on auth'ed user
    """
    if request.method == 'GET':
        materialstock = MaterialStock.objects.all()
        serializer = serializersapp.InventorySerializer(materialstock, context={'request':request.user})
        return Response(serializer.data)
    
#----------------------- product_capacity view -------------------------------
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

#----------------------- MaterialStockListAPIView view -------------------------------
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
        required_fields = ['material', 'current_capacity', 'max_capacity']
        for field in required_fields:
            if not request.data.get(field):
                return Response({'error': f'{field.capitalize()} field is missing.'}, status=status.HTTP_400_BAD_REQUEST)
            
        material = request.data.get('material')
        current_cap = request.data.get('current_capacity')
        max_cap = request.data.get('max_capacity')

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

#----------------------- MaterialStockDetailAPIView view -------------------------------
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

#----------------------- ProductListAPIView view -------------------------------
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
        
#----------------------- ProductDeleteAPIView view -------------------------------
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


#----------------------- restock view -------------------------------
# Allow multiple material restocking in a single JSON POST request using dict list
@api_view(['GET', 'POST'])
def restock(request):
    """
    List all material stocks, price for restocking, and amount of restock.
    """
    current_store = Store.objects.filter(user__username=request.user).first()
    if request.method == 'GET':
        material_stocks = MaterialStock.objects.filter(store=current_store)
        serializer = serializersapp.GetRestockSerializer(material_stocks, many=True)
        response_data = {
            'materials': serializer.data,
            'overall_price': sum([m['total_price'] for m in serializer.data])
        }

        if response_data.get('overall_price') == 0:
            return Response("All material stocks for this store are already full.", status=status.HTTP_204_NO_CONTENT)
        
        return Response(response_data, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        material_stocks = MaterialStock.objects.filter(store=current_store)
        if all(ms.current_capacity == ms.max_capacity for ms in material_stocks):
            return Response({"error": "Restocks failed. All material stocks for this store are already full."}, status=status.HTTP_204_NO_CONTENT)
        
        if not request.data.get('materials'):
            # If user doesn't specify which materials to update, update current_capacity of all MaterialStock objects to their max_capacity
            response_data = {'materials': []}
            overall_price = 0
            for material_stock in material_stocks:
                added_quantity = material_stock.max_capacity - material_stock.current_capacity
                if added_quantity == 0:
                    continue
                material_stock.current_capacity = material_stock.max_capacity
                material = material_stock.material
                material_name = material_stock.material.name
                material_stock.save(update_fields=['current_capacity'])
                total_price = added_quantity * material.price
                overall_price += total_price
                response_data['materials'].append({
                    'material': material.pk,
                    'material_name': material_name,
                    'quantity': added_quantity,
                    'capacity': f"{material_stock.current_capacity}/{material_stock.max_capacity}",
                    'total_price': total_price,
                })
                response_data['overall_price'] = overall_price
        
        else:
            # if user specify which material stocks to update, update current_capacity of specified stocks based on given material and quantity.
            serializer = serializersapp.PostRestockSerializer(data=request.data['materials'], many=True, context={'store': current_store})

            if not serializer.is_valid():
                error_data = {'error': 'Restocks request failed due to invalid data. Please review the following list of invalid restock',
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
                    return Response({'error': 'The quantity to be restocked is more than the maximum capacity of the material stock.'}, status=status.HTTP_400_BAD_REQUEST)

                material = material_stock.material
                material_name = material.name
                total_price = added_quantity * material.price
                overall_price += total_price
                
                material_stock.current_capacity = new_capacity
                material_stock.save(update_fields=['current_capacity'])

                response_data['materials'].append({
                    'material': material_id,
                    'material_name': material_name,
                    'quantity': added_quantity,
                    'capacity': f"{material_stock.current_capacity}/{material_stock.max_capacity}",
                    'total_price': total_price,
                })
            response_data['overall_price'] = overall_price
        return Response(response_data, status=status.HTTP_200_OK)

#----------------------- sales view -------------------------------
# Allow multiple product sales in a single JSON POST request using dict list
@api_view(['GET', 'POST'])
def sales(request):
    current_store = Store.objects.filter(user__username=request.user).first()

    if request.method == 'GET':
        queryset = Product.objects.filter(product_stores=current_store).order_by('pk')
        serializer = serializersapp.ProductSerializer(queryset, many=True)
        response_data = {'Products available in this store:':[serializer.data]}
        return Response(response_data, status=status.HTTP_200_OK)


    elif request.method == 'POST':
        serializer = serializersapp.SalesSerializer(data=request.data['sales'], context={'store':current_store}, many=True)

        if not serializer.is_valid():
            error_data = {'error': 'Sales request failed due to invalid data. Please review the following list of invalid sales',
                        'sales': serializer.errors}
            return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

        response_data = {
            'success': True,
            'message': 'Material stocks subtracted successfully',
            'updated material stocks': []
            } 

        # Loop through each product and subtract the required material from the stock
        for sale_index, sale in enumerate(serializer.validated_data):
            total_subtracted_capacity = 0
            product = get_object_or_404(Product, id=sale['product_id'])

            for material_quantity in product.material_quantity.all():
                material = material_quantity.ingredient
                stock = get_object_or_404(MaterialStock, store=current_store, material=material)
                subtracted_capacity = material_quantity.quantity * sale['quantity']
                stock.current_capacity -= subtracted_capacity
                stock.save()

                total_subtracted_capacity += subtracted_capacity  # Increment total_subtracted_capacity for each material

                new_response_data = {
                    'id': stock.pk,
                    'material': material.name,
                    'total_subtracted_capacity': total_subtracted_capacity, 
                    'remaining capacity': f'{stock.current_capacity}/{stock.max_capacity}'
                    } 
                for item in response_data['updated material stocks']:
                    if item['id'] == new_response_data['id']:
                        item.update(new_response_data)
                        break
                else:
                    response_data['updated material stocks'].append(new_response_data)

            # Update total_subtracted_capacity to response_data after each sale
            response_data['updated material stocks'][sale_index]['total_subtracted_capacity'] = total_subtracted_capacity

        return Response(response_data, status=status.HTTP_200_OK)

#===============================================================
#                   HTML Template Views
#===============================================================

#----------------------- store_products view -------------------------------
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

#----------------------- add_product view -------------------------------
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

#----------------------- delete_product view -------------------------------
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

#----------------------- MaterialStockView view -------------------------------
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
    
#----------------------- MaterialStockCreateView view -------------------------------
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
    
#----------------------- MaterialStockUpdateView view -------------------------------
class MaterialStockUpdateView(generic.UpdateView):
    model = MaterialStock
    form_class = forms.MaterialStockUpdateForm
    template_name = 'material_stock_form.html'
    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('store_stocks')

#----------------------- MaterialStockDeleteView view -------------------------------
class MaterialStockDeleteView(generic.DeleteView):
    model = MaterialStock
    template_name = 'material_stock_delete.html'
    def get_success_url(self):
        return reverse_lazy('store_stocks')


