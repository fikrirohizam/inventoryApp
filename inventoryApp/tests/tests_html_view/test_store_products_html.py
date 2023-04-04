from django.test import TestCase, Client
from django.urls import reverse
from inventoryApp.models import Store, Product, User
from inventoryApp.factories import MaterialFactory, MaterialQuantityFactory, MaterialStockFactory, ProductFactory, StoreFactory
from inventoryApp import forms

class StoreProductsTestCase(TestCase):
    url = reverse('store_products')

    def setUp(self):
        self.user = User.objects.create(user_id=1)
        self.material = MaterialFactory()
        self.product = ProductFactory(name='Product 1')
        self.material_quantity = MaterialQuantityFactory(ingredient=self.material)
        self.store = StoreFactory(user=self.user, store_name='Test Store')
        self.material_stock = MaterialStockFactory(material=self.material, store=self.store)

        self.store.products.add(self.product)
        self.product.material_quantity.add(self.material_quantity)

    def authenticate(self):
        self.user = User.objects.get(user_id=1)
        self.client.force_login(self.user)

    def test_store_products(self):
        self.authenticate()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store_products.html')
        self.assertContains(response, 'Test Store')
        self.assertContains(response, 'Product 1')

    def test_store_products_not_logged_in(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('html_login') + '?next=' + self.url)

class AddDeleteProductTestCase(TestCase):
    url = reverse('add_product')

    def setUp(self):
        self.user = User.objects.create(user_id=1)
        self.material = MaterialFactory()
        self.product = ProductFactory(name='Product 1')
        self.material_quantity = MaterialQuantityFactory(ingredient=self.material)
        self.store = StoreFactory(user=self.user, store_name='Test Store')
        self.material_stock = MaterialStockFactory(material=self.material, store=self.store)

        self.product.material_quantity.add(self.material_quantity)

    def authenticate(self):
        self.user = User.objects.get(user_id=1)
        self.client.force_login(self.user)

    def test_add_product_view_post(self):
        self.authenticate()
        form_data = {'product': self.product.pk}
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('store_products'))
        self.assertTrue(self.product in self.store.products.all())

    def test_delete_product_view_post(self):
        self.authenticate()
        self.store.products.add(self.product)
        response = self.client.post(reverse('delete_product', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('store_products'))
        self.assertFalse(self.store.products.filter(pk=self.product.id).exists())