from django.test import TestCase, Client
from django.urls import reverse
from inventoryApp.models import Store, Product, User
from inventoryApp.factories import StoreWithProductsFactory,MaterialFactory, MaterialQuantityFactory, MaterialStockFactory, ProductFactory, StoreFactory
from inventoryApp import forms
from inventoryApp.models import Store, Material, MaterialStock
from inventoryApp.forms import MaterialStockAddForm

class MaterialStockCreateViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create(user_id=1)
        self.material = MaterialFactory.create(name='material1')
        self.material_quantity = MaterialQuantityFactory(ingredient=self.material)
        self.product = ProductFactory.create(name='Product 1', material_quantity=self.material_quantity)
        self.store = StoreWithProductsFactory(user=self.user, store_name='Test Store', products=[self.product])

        self.url = reverse('create_stock', kwargs={'store_id': self.store.pk})

    def authenticate(self):
        self.user = User.objects.get(user_id=1)
        self.client.force_login(self.user)

    def test_view_success(self):
        self.authenticate()
        form_data = {'material': self.material.pk, 'max_capacity': 200, 'current_capacity': 100}
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('store_stocks'))

        # Check that the MaterialStock was created correctly
        material_stock = MaterialStock.objects.get(store=self.store, material=self.material)
        self.assertEqual(material_stock.max_capacity, 200)
        self.assertEqual(material_stock.current_capacity, 100)

    def test_form_error(self):
        self.authenticate()
        # Create an existing MaterialStock for the store and material
        MaterialStockFactory.create(store=self.store, material=self.material)

        form_data = {'material': self.material.pk, 'max_capacity': 200, 'current_capacity': 100}
        response = self.client.post(self.url, form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertInHTML('This store already has material stock for all currently available materials. Please update existing stock instead.',response.content.decode())
