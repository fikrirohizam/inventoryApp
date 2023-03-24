from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import Store, Material, MaterialStock, User
from ..serializers import ProductSerializer
from ..factories import MaterialFactory, MaterialQuantityFactory, MaterialStockFactory, ProductFactory, StoreFactory

class ProductListAPIViewTestCase(APITestCase):
    url = reverse('products')

    def setUp(self):
        self.user = User.objects.create(user_id=1)
        self.store = StoreFactory(user=self.user)
        self.material = MaterialFactory()
        self.material_quantity = MaterialQuantityFactory(ingredient=self.material)
        self.product = ProductFactory()

        self.product.material_quantity.add(self.material_quantity)
        self.store.products.add(self.product)

    def authenticate(self):
        self.user = User.objects.get(user_id=1)
        self.client.force_authenticate(self.user)

    def test_get_products_list(self):
        self.authenticate()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], self.product.name)

    def test_delete_product_from_store(self):
        self.authenticate()
        data = {'id': self.product.id}
        response = self.client.delete(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(self.store.products.filter(id=self.product.id).exists())

    def test_serialized_product_data(self):
        self.authenticate()
        serializer_data = ProductSerializer(instance=self.product).data
        print('ddd',serializer_data)

        self.assertEqual(serializer_data['name'], self.product.name)
        self.assertEqual(len(serializer_data['material_quantity']), 1)
        self.assertEqual(serializer_data['material_quantity'][0]['quantity'], self.material_quantity.quantity)
        self.assertEqual(serializer_data['material_quantity'][0]['ingredient'], self.material.pk)
