from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import User
from ..serializers import InventorySerializer
from ..factories import MaterialStockFactory, StoreFactory

class InventorySerializerTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create(user_id=1)
        self.store = StoreFactory.create(user=self.user)
        self.material_stock = MaterialStockFactory.create(store=self.store)
        self.serializer = InventorySerializer(instance=self.material_stock, context={'request': self.user})

    def authenticate(self):
        self.user = User.objects.get(user_id=1)
        self.client.force_authenticate(self.user)

    def test_contains_expected_fields(self):
        self.authenticate()
        data = self.serializer.data
        self.assertEqual(set(data['materials'][0].keys()), set(['material', 'material_name', 'max_capacity', 'current_capacity', 'percentage_of_capacity']))
    
    def test_material_name_field_content(self):
        data = self.serializer.data
        self.assertEqual(data['materials'][0]['material'], self.material_stock.material.pk)

class InventoryViewTestCase(APITestCase):
    url = reverse('inventory')

    def setUp(self):
        self.user = User.objects.create(user_id=1)
        self.store = StoreFactory.create(user=self.user)
        self.material_stock = MaterialStockFactory.create(store=self.store)
        self.serializer = InventorySerializer(instance=self.material_stock, context={'request': self.user})

    def authenticate(self):
        self.user = User.objects.get(user_id=1)
        self.client.force_authenticate(self.user)

    def test_get_all_material_stocks(self):
        self.authenticate()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data['materials'][0]['material'], self.material_stock.material.pk)
        self.assertEqual(response.data['materials'][0]['max_capacity'], self.material_stock.max_capacity)
        self.assertEqual(response.data['materials'][0]['current_capacity'], self.material_stock.current_capacity)
        self.assertEqual(response.data['materials'][0]['percentage_of_capacity'], self.material_stock.percentage_of_capacity)

