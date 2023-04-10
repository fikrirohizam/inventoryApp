from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import Store, Material, MaterialStock, User
from ..serializers import RestockGetSerializer
from ..factories import MaterialFactory, MaterialStockFactory, StoreFactory

class RestocksViewTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create(user_id=1)
        self.store = StoreFactory(user=self.user)
        self.url = reverse('restocks')

    def authenticate(self):
        self.user = User.objects.get(user_id=1)
        self.client.force_authenticate(self.user)

    def test_add_single_material(self):
        self.authenticate()
        material = MaterialFactory.create(price=100.0)
        stock = MaterialStockFactory.create(material=material, store=self.store, current_capacity=200, max_capacity=1000)
        data = {
            'materials': [
                {
                    'material': material.material_id,
                    'quantity': 20
                }
            ]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['materials'][0]['total_price'], 2000.0)
        self.assertEqual(response.data['overall_price'], 2000.0)
        stock.refresh_from_db()
        self.assertEqual(stock.current_capacity, 220)
        
    def test_add_multiple_materials(self):
        self.authenticate()
        material1 = MaterialFactory.create(price=100.0)
        stock1 = MaterialStockFactory(material=material1, store=self.store, current_capacity=100, max_capacity=1000)
        material2 = MaterialFactory.create(price=200.0)
        stock2 = MaterialStockFactory(material=material2, store=self.store, current_capacity=200, max_capacity=1000)
        data = {
            'materials': [
                {
                    'material': material1.material_id,
                    'quantity': 12
                },
                {
                    'material': material2.material_id,
                    'quantity': 10
                }
            ]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['materials'][0]['total_price'], 1200.0)
        self.assertEqual(response.data['materials'][1]['total_price'], 2000.0)
        self.assertEqual(response.data['overall_price'], 3200.0)
        stock1.refresh_from_db()
        self.assertEqual(stock1.current_capacity, 112)
        stock2.refresh_from_db()
        self.assertEqual(stock2.current_capacity, 210)


    def test_add_no_materials(self):
        # Test that when an empty POST request is sent, 
        # all material stocks are restocked to their maximum capacity
        self.authenticate()
        material1 = MaterialFactory.create(price=100.0)
        stock1 = MaterialStockFactory(material=material1, store=self.store, current_capacity=50, max_capacity=100)
        material2 = MaterialFactory.create(price=200.0)
        stock2 = MaterialStockFactory(material=material2, store=self.store, current_capacity=30, max_capacity=50)

        data = {}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['materials'][0]['total_price'], 5000.0)
        self.assertEqual(response.data['materials'][1]['total_price'], 4000.0)
        self.assertEqual(response.data['materials'][0]['quantity'], 50)
        self.assertEqual(response.data['materials'][1]['quantity'], 20)

        self.assertEqual(response.data['overall_price'], 9000.0)
        stock1.refresh_from_db()
        self.assertEqual(stock1.current_capacity, 100)
        stock2.refresh_from_db()
        self.assertEqual(stock2.current_capacity, 50)

class RestockTestCase(APITestCase):
    def setUp(self):
        self.store = Store.objects.create(store_name='My Store',user=User.objects.create(user_id=1))
        self.material = Material.objects.create(name='Material', price=10.0)
        self.material_stock = MaterialStock.objects.create(store=self.store, material=self.material, max_capacity=100, current_capacity=50)

    def authenticate(self):
        self.user = User.objects.get(user_id=1)
        self.client.force_authenticate(self.user)

    def test_store_material_serializer(self):
        serializer = RestockGetSerializer(instance=self.material_stock)
        expected_data = {'material_name': 'Material', 'material_price': '10.00', 'max_capacity': 100, 'current_capacity': 50}
        self.assertEqual(serializer.data, expected_data)

    def test_store_material_view_unauthenticated(self):
        url = reverse('restock')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_store_material_view(self):
        self.authenticate()
        url = reverse('restock')
        response = self.client.get(url)
        expected_data = {'material_name': 'Material', 'material_price': '10.00', 'max_capacity': 100, 'current_capacity': 50}
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [expected_data])

