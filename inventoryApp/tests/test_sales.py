from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import User
from ..serializers import SalesSerializer
from ..factories import MaterialFactory, MaterialQuantityFactory, MaterialStockFactory, ProductFactory, StoreFactory

class MultiSalesTestCase(APITestCase):
    url = reverse('multisales')

    def setUp(self):
        self.user = User.objects.create(user_id=1)
        self.store = StoreFactory(user=self.user)

        self.material1 = MaterialFactory()
        self.material2 = MaterialFactory()
        self.product1 = ProductFactory()
        self.product2 = ProductFactory()
        self.material_quantity1 = MaterialQuantityFactory(ingredient=self.material1, quantity=5)
        self.material_quantity2 = MaterialQuantityFactory(ingredient=self.material2, quantity=10)
        self.material_stock1 = MaterialStockFactory(store=self.store, material=self.material_quantity1.ingredient, current_capacity=500, max_capacity=1000)
        self.material_stock2 = MaterialStockFactory(store=self.store, material=self.material_quantity2.ingredient, current_capacity=500, max_capacity=1000)
        
        self.store.products.add(self.product1, self.product2)
        self.product1.material_quantity.add(self.material_quantity1)
        self.product2.material_quantity.add(self.material_quantity2)

    def authenticate(self):
        self.user = User.objects.get(user_id=1)
        self.client.force_authenticate(self.user)

    def test_multisales_with_valid_data(self):
        self.authenticate()
        data = {
            'sales': [
                {'product_id': self.product1.id, 'quantity': 2},
                {'product_id': self.product2.id, 'quantity': 10}
            ]
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_data = {
            "success": True,
            "message": "Material stocks subtracted successfully",
            "updated material stocks": [
                {
                    "id": 1,
                    "material": self.material1.name,
                    "total_subtracted_capacity": 10,
                    "remaining capacity": "490/1000"
                },
                {
                    "id": 2,
                    "material": self.material2.name,
                    "total_subtracted_capacity": 100,
                    "remaining capacity": "400/1000"
                }
            ]
        }

        self.assertEqual(response.data, expected_data)
        # Check that material stock has been updated
        self.material_stock1.refresh_from_db()
        self.material_stock2.refresh_from_db()
        self.assertEqual(self.material_stock1.current_capacity, 490)
        self.assertEqual(self.material_stock2.current_capacity, 400)

        self.material = MaterialFactory()

    def test_multisales_with_invalid_product_id(self):
        self.authenticate()
        data = {
            'sales': [
                {'product_id': 9999, 'quantity': 2},
                {'product_id': self.product2.id, 'quantity': 1}
            ]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 
                         'Sales request failed due to invalid data. Please review the following list of invalid sales')
        self.assertIn(response.data['sales'][0]['non_field_errors'][0], 'Invalid product id')
        
    def test_multisales_with_insufficient_stock(self):
        self.authenticate()
        # Reduce the stock capacity so that it's not enough to fulfill the sales
        self.material_stock1.current_capacity = 2
        self.material_stock1.save()
        data = {
            'sales': [
                {'product_id': self.product1.id, 'quantity': 2},
                {'product_id': self.product2.id, 'quantity': 1}
            ]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 
                         'Sales request failed due to invalid data. Please review the following list of invalid sales')
        self.assertIn(response.data['sales'][0]['non_field_errors'][0], 'Insufficient material stock')
        
class SalesSerializerTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create(user_id=1)
        self.material = MaterialFactory()
        self.product = ProductFactory()
        self.material_quantity = MaterialQuantityFactory(ingredient=self.material)
        self.store = StoreFactory(user=self.user)
        self.material_stock = MaterialStockFactory(material=self.material, store=self.store)

        self.store.products.add(self.product)
        self.product.material_quantity.add(self.material_quantity)

    def authenticate(self):
        self.user = User.objects.get(user_id=1)
        self.client.force_authenticate(self.user)

    def test_invalid_product_id(self):
        self.authenticate()

        data = {
            'product_id': 999,
            'quantity': 1
        }
        serializer = SalesSerializer(data=data, context={'store':self.store})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['non_field_errors'][0], 'Invalid product id')

    def test_insufficient_material_stock(self):
        self.authenticate()
        self.material_stock.current_capacity = 0
        self.material_stock.save()

        data = {
            'product_id': self.product.id,
            'quantity': 1
        }
        serializer = SalesSerializer(data=data, context={'store':self.store})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['non_field_errors'][0], 'Insufficient material stock')

class SalesViewTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create(user_id=1)
        self.material = MaterialFactory()
        self.product = ProductFactory()
        self.material_quantity = MaterialQuantityFactory(ingredient=self.material)
        self.store = StoreFactory(user=self.user)
        self.material_stock = MaterialStockFactory(material=self.material, store=self.store)

        self.store.products.add(self.product)
        self.product.material_quantity.add(self.material_quantity)

    def authenticate(self):
        self.user = User.objects.get(user_id=1)
        self.client.force_authenticate(self.user)

    def test_valid_sales(self):
        self.authenticate()
        self.material_stock.max_capacity = 1000
        self.material_stock.current_capacity = self.material_stock.max_capacity
        self.material_stock.save()
        data = {
            'product_id': self.product.id,
            'quantity': 1
        }
        response = self.client.post(reverse('sales'), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, 'success')

    def test_insufficient_material_stock(self):
        self.authenticate()
        self.material_stock.current_capacity = 0
        self.material_stock.save()

        data = {
            'product_id': self.product.id,
            'quantity': 1000
        }
        response = self.client.post(reverse('sales'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['non_field_errors'][0], 'Insufficient material stock')
