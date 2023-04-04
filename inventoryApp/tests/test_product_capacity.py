from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import Store, Material, MaterialStock, User
from ..serializers import ProductCapacitySerializer
from ..factories import MaterialFactory, MaterialQuantityFactory, MaterialStockFactory, ProductFactory, StoreFactory

class ProductCapacitySerializerTestCase(APITestCase):

    def setUp(self):
        self.user = User.objects.create(user_id=1)
        self.material = MaterialFactory()
        self.product1 = ProductFactory()
        self.material_quantity1 = MaterialQuantityFactory(ingredient=self.material)
        self.store = StoreFactory(user=self.user)
        self.material_stock = MaterialStockFactory(material=self.material, store=self.store)

        self.store.products.add(self.product1)
        self.product1.material_quantity.add(self.material_quantity1)

    def authenticate(self):
        self.user = User.objects.get(user_id=1)
        self.client.force_authenticate(self.user)

    def test_store_serializer(self):
        self.authenticate()
        serializer = ProductCapacitySerializer(instance=self.store, context={'currentstore':self.store})

        expected_data = {
            'store_name': self.store.store_name,
            'products': [
                {
                    'id': self.product1.id,
                    'name': self.product1.name,
                    'material_quantity': [
                        {
                            "quantity": self.material_quantity1.quantity,
                            "ingredient": self.material_quantity1.ingredient.pk
                        }
                    ]
                }
            ],
            'material_stock': [
                {
                    'product_name': self.product1.name,
                    'product_material_with_lowest_stock': {
                        'material_name': self.material.name,
                        'stock_capacity': self.material_stock.current_capacity,
                        'material_quantity_each': self.material_quantity1.quantity,
                        'product_quantity': int(self.material_stock.current_capacity / self.material_quantity1.quantity)
                    }
                }
            ]
        }

        self.assertEqual(serializer.data, expected_data)

class ProductCapacityViewTestCase(APITestCase):

    def setUp(self):
        self.user = User.objects.create(user_id=1)
        self.material = MaterialFactory()
        self.product1 = ProductFactory()
        self.material_quantity1 = MaterialQuantityFactory(ingredient=self.material)
        self.store = StoreFactory(user=self.user)
        self.material_stock = MaterialStockFactory(material=self.material, store=self.store)

        self.store.products.add(self.product1)
        self.product1.material_quantity.add(self.material_quantity1)

    def authenticate(self):
        self.user = User.objects.get(user_id=1)
        self.client.force_authenticate(self.user)

    def test_product_capacity_view(self):
        self.authenticate()
        url = reverse('product_capacity')
        response = self.client.get(url)

        expected_data = {
            'store_name': self.store.store_name,
            'products': [
                {
                    'id': self.product1.id,
                    'name': self.product1.name,
                    'material_quantity': [
                        {
                            "quantity": self.material_quantity1.quantity,
                            "ingredient": self.material_quantity1.ingredient.pk
                        }
                    ]
                }
            ],
            'material_stock': [
                {
                    'product_name': self.product1.name,
                    'product_material_with_lowest_stock': {
                        'material_name': self.material.name,
                        'stock_capacity': self.material_stock.current_capacity,
                        'material_quantity_each': self.material_quantity1.quantity,
                        'product_quantity': int(self.material_stock.current_capacity / self.material_quantity1.quantity)
                    }
                }
            ]
        }

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

        # Length should be 3, as it should have 3 keys: 'store_name', 'products', 'material_stock'
        self.assertEqual(len(response.data), 3)

        # Values for 'products' key
        self.assertEqual(response.data['products'][0]['name'], self.product1.name)
        self.assertEqual(response.data['products'][0]['material_quantity'][0]['quantity'], self.material_quantity1.quantity)
        self.assertEqual(response.data['products'][0]['material_quantity'][0]['ingredient'], self.material_quantity1.ingredient.pk)

        # Values for 'material_stock' key
        self.assertEqual(response.data['material_stock'][0]['product_name'], self.product1.name)
        # Values for 'product_material_with_lowest_stock' key
        self.assertEqual(response.data['material_stock'][0]['product_material_with_lowest_stock']['material_name'], self.material.name)
        self.assertEqual(response.data['material_stock'][0]['product_material_with_lowest_stock']['stock_capacity'], self.material_stock.current_capacity)
        self.assertEqual(response.data['material_stock'][0]['product_material_with_lowest_stock']['material_quantity_each'], self.material_quantity1.quantity)
        self.assertEqual(response.data['material_stock'][0]['product_material_with_lowest_stock']['product_quantity'], int(self.material_stock.current_capacity / self.material_quantity1.quantity))
