from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import User
from ..serializers import InventorySerializer
from ..factories import MaterialStockFactory, MaterialFactory, MaterialQuantityFactory, StoreFactory, ProductFactory

class MaterialStockDetailAPIViewTestCase(APITestCase):
    
    def setUp(self):
        self.user = User.objects.create(user_id=1)
        self.store = StoreFactory(user=self.user)
        self.material = MaterialFactory()
        self.material_quantity = MaterialQuantityFactory(ingredient=self.material)
        self.product = ProductFactory()
        self.material_stock = MaterialStockFactory(store=self.store, material=self.material_quantity.ingredient, current_capacity=500, max_capacity=1000)

        self.product.material_quantity.add(self.material_quantity)
        self.store.products.add(self.product)
        self.url = reverse('material_stocks_detail', kwargs={'pk': self.material_stock.pk})

    def authenticate(self):
        self.user = User.objects.get(user_id=1)
        self.client.force_authenticate(self.user)

    def test_get_material_stock_detail(self):
        self.authenticate()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("material"), self.material.pk)

    def test_update_material_stock(self):
        self.authenticate()
        value = {
            "max_capacity": 500,
        }
        response = self.client.put(self.url, value)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("max_capacity"), 500)
        self.assertEqual(response.data.get("material"), self.material.pk)
        
    def test_update_material_stock_with_invalid_capacity(self):
         self.authenticate()
         value = {
             "max_capacity": 10,
         }
         response = self.client.put(self.url, value)
         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
         self.assertEqual(
             response.data.get("error"),
             "Maximum capacity cannot be lower than current capacity."
         )
 
    def test_delete_material_stock(self):
         self.authenticate()
         response = self.client.delete(self.url)
         self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
 

class MaterialStockListAPIViewTestCase(APITestCase):
    
    def setUp(self):
        self.user = User.objects.create(user_id=1)
        self.store = StoreFactory(user=self.user)
        self.material1 = MaterialFactory()
        self.material2 = MaterialFactory()
        self.material_quantity = MaterialQuantityFactory(ingredient=self.material1)
        self.product = ProductFactory()
        self.material_stock = MaterialStockFactory(store=self.store, material=self.material_quantity.ingredient, current_capacity=500, max_capacity=1000)

        self.product.material_quantity.add(self.material_quantity)
        self.store.products.add(self.product)
        self.url = reverse('material_stocks')

    def authenticate(self):
        self.user = User.objects.get(user_id=1)
        self.client.force_authenticate(self.user)

    def test_create_material_stock(self):
        self.authenticate()
        value = {
            "material": self.material2.pk,
            "max_capacity": 500,
            "current_capacity": 100,
            "store": self.store.pk,
        }
        response = self.client.post(self.url, value)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get("material"), self.material2.pk)

    def test_list_material_stocks(self):
        self.authenticate()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['material'], self.material_stock.material.pk)
        self.assertEqual(response.data['results'][0]['max_capacity'], self.material_stock.max_capacity)