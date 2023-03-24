import datetime
from factory.django import DjangoModelFactory
from . import models
from .models import Material, User, MaterialQuantity, MaterialStock, Store, Product
from factory import Faker
from factory import SubFactory, RelatedFactory,Iterator, Sequence, fuzzy, LazyAttribute

class MaterialFactory(DjangoModelFactory):
    class Meta:
        model = Material
    name = Faker('first_name')
    price = fuzzy.FuzzyDecimal(0.5,100.0)

class MaterialQuantityFactory(DjangoModelFactory):
    class Meta:
        model = MaterialQuantity
    quantity = fuzzy.FuzzyInteger(1,100)
    ingredient = SubFactory(MaterialFactory)

class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product
    material_quantity = RelatedFactory(MaterialQuantityFactory)
    name = Faker('name')

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
    user_id = fuzzy.FuzzyInteger(1,100)
    username = Faker('name')

class MaterialStockFactory(DjangoModelFactory):
    class Meta:
        model = MaterialStock
    store = SubFactory('inventoryApp.factories.StoreFactory')
    material = SubFactory(MaterialFactory)
    max_capacity = fuzzy.FuzzyInteger(1,100)
    current_capacity = LazyAttribute(lambda x: fuzzy.FuzzyInteger(1, x.max_capacity).fuzz()) 

class StoreFactory(DjangoModelFactory):
    class Meta:
        model = Store
    store_name = Faker('company')
    products = RelatedFactory(ProductFactory)
    user = SubFactory(UserFactory)


