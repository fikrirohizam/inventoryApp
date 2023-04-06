from factory.django import DjangoModelFactory
from inventoryApp import models
from factory import Faker
from factory import SubFactory, RelatedFactory, fuzzy, LazyAttribute
from factory import post_generation

class MaterialFactory(DjangoModelFactory):
    class Meta:
        model = models.Material
    name = Faker('first_name')
    price = fuzzy.FuzzyDecimal(0.5,100.0)

class MaterialQuantityFactory(DjangoModelFactory):
    class Meta:
        model = models.MaterialQuantity
    quantity = fuzzy.FuzzyInteger(1,100)
    ingredient = SubFactory(MaterialFactory)

class ProductFactory(DjangoModelFactory):
    class Meta:
        model = models.Product
    material_quantity = RelatedFactory(MaterialQuantityFactory)
    name = Faker('name')

class UserFactory(DjangoModelFactory):
    class Meta:
        model = models.User
    user_id = fuzzy.FuzzyInteger(1,100)
    username = Faker('name')

class MaterialStockFactory(DjangoModelFactory):
    class Meta:
        model = models.MaterialStock
    store = SubFactory('inventoryApp.factories.StoreFactory')
    material = SubFactory(MaterialFactory)
    max_capacity = fuzzy.FuzzyInteger(1,100)
    current_capacity = LazyAttribute(lambda x: fuzzy.FuzzyInteger(1, x.max_capacity).fuzz()) 

class StoreFactory(DjangoModelFactory):
    class Meta:
        model = models.Store
    store_name = Faker('company')
    products = RelatedFactory(ProductFactory)
    user = SubFactory(UserFactory)


# Does not create new product if it is called with added products
# e.g. StoreFactory(products=[self.product])
class StoreWithProductsFactory(DjangoModelFactory):
    class Meta:
        model = models.Store
    store_name = Faker('company')
    user = SubFactory(UserFactory)

    @post_generation
    def products(self, create, extracted, **kwargs):
        if not create:
            return
        
        if extracted:
            # Use the provided products instead of creating new ones.
            self.products.set(extracted)
            return

        # Create a default product for the store.
        self.products.add(ProductFactory())


