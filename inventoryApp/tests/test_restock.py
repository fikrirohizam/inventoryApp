from django.urls import reverse
from inventoryApp import factories, models, serializers
from rest_framework import status
from rest_framework.test import APITestCase


class RestockViewTestCase(APITestCase):
    def setUp(self):
        self.user = models.User.objects.create(user_id=1)
        self.store = factories.StoreFactory(user=self.user)
        self.url = reverse('restock')

    def authenticate(self):
        self.user = models.User.objects.get(user_id=1)
        self.client.force_authenticate(self.user)

    def test_add_single_material(self):
        self.authenticate()
        material = factories.MaterialFactory.create(price=100.0)
        stock = factories.MaterialStockFactory.create(material=material, store=self.store, current_capacity=200, max_capacity=1000)
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
        material1 = factories.MaterialFactory.create(price=100.0)
        stock1 = factories.MaterialStockFactory(material=material1, store=self.store, current_capacity=100, max_capacity=1000)
        material2 = factories.MaterialFactory.create(price=200.0)
        stock2 = factories.MaterialStockFactory(material=material2, store=self.store, current_capacity=200, max_capacity=1000)
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
        material1 = factories.MaterialFactory.create(price=100.0)
        stock1 = factories.MaterialStockFactory(material=material1, store=self.store, current_capacity=50, max_capacity=100)
        material2 = factories.MaterialFactory.create(price=200.0)
        stock2 = factories.MaterialStockFactory(material=material2, store=self.store, current_capacity=30, max_capacity=50)

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

class PostRestockSerializerTestCase(APITestCase):
    def setUp(self):
        self.store = factories.StoreFactory.create(store_name='Test Store')
        self.material = factories.MaterialFactory.create(name='Test Material', price=10)
        self.material_stock = factories.MaterialStockFactory.create(store=self.store, material=self.material, current_capacity=5, max_capacity=10)

    def test_valid_data(self):
        data = {'material': self.material.pk, 'quantity': 3}
        serializer = serializers.PostRestockSerializer(data=data, context={'store': self.store})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, data)

    def test_invalid_material(self):
        data = {'material': 999, 'quantity': 3}
        serializer = serializers.PostRestockSerializer(data=data, context={'store': self.store})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(str(serializer.errors['non_field_errors']), "[ErrorDetail(string='Invalid product id', code='invalid')]")

    def test_insufficient_capacity(self):
        data = {'material': self.material.pk, 'quantity': 722}
        serializer = serializers.PostRestockSerializer(data=data, context={'store': self.store})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(str(serializer.errors['non_field_errors']), "[ErrorDetail(string='The quantity to be restocked is more than the maximum capacity of the material stock.', code='invalid')]")

class GetRestockSerializerTestCase(APITestCase):
    def setUp(self):
        self.user = models.User.objects.create(user_id=1)
        self.store = factories.StoreFactory.create(user=self.user,store_name='Test Store')
        self.material = factories.MaterialFactory.create(name='Test Material', price=10)
        self.material_stock = factories.MaterialStockFactory.create(store=self.store, material=self.material, current_capacity=5, max_capacity=10)
        self.url = reverse('restock')

    def authenticate(self):
        self.user = models.User.objects.get(user_id=1)
        self.client.force_authenticate(self.user)

    def test_get_restock_serializer(self):
        self.authenticate()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['materials']), 1)
        self.assertEqual(response.data['materials'][0]['material'], self.material.pk)
        self.assertEqual(response.data['materials'][0]['material_name'], self.material.name)
        self.assertEqual(response.data['materials'][0]['quantity'], 5)
        self.assertEqual(response.data['materials'][0]['capacity'], '5/10')
        self.assertEqual(response.data['materials'][0]['total_price'], 50.00)