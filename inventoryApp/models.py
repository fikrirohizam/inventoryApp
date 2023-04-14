from django.db import models
from django.contrib.auth.models import AbstractUser
from django.forms import ValidationError
from django.utils import timezone

# Create your models here.
class User(AbstractUser):
    user_id = models.AutoField(primary_key=True)

class Material(models.Model):
    material_id = models.AutoField(primary_key=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    name = models.CharField(max_length=300)
    def __str__(self):
        return self.name
    
class MaterialQuantity(models.Model):
    quantity = models.IntegerField()
    ingredient = models.ForeignKey(Material,related_name='quantities',on_delete=models.CASCADE)
    def __str__(self):
        return f'{self.ingredient.name} ({self.quantity})'
    @property
    def total_cost(self):
        return self.quantity * self.ingredient.price
    
class Product(models.Model):
    name = models.CharField(max_length=200)
    material_quantity = models.ManyToManyField(MaterialQuantity,related_name='material_products')
    def __str__(self):
        return self.name

class Store(models.Model):
    store_id = models.AutoField(primary_key=True)
    store_name = models.CharField(max_length=100)
    user = models.OneToOneField(User,related_name='user_store',on_delete=models.CASCADE)
    products = models.ManyToManyField(Product,related_name='product_stores')
    def __str__(self):
        return self.store_name

class MaterialStock(models.Model):
    store = models.ForeignKey(Store,related_name='stocks',on_delete=models.CASCADE)
    material = models.ForeignKey(Material,related_name='materials',on_delete=models.CASCADE, null=True)
    max_capacity =  models.IntegerField()
    current_capacity =  models.IntegerField()
    @property
    def percentage_of_capacity(self):
        current_capacity = self.current_capacity
        max_capacity = self.max_capacity
        percentage = (current_capacity / max_capacity) * 100
        return round(percentage, 2)
    
    def __str__(self):
        store_name = self.store.store_name
        material_name = self.material.name
        current_capacity = self.current_capacity
        max_capacity = self.max_capacity
        return f"{store_name} ({material_name}) {current_capacity}/{max_capacity}"
    class Meta:
        unique_together = (('store', 'material'),)

    def clean(self):
        if self.current_capacity > self.max_capacity:
            raise ValidationError("Current capacity cannot be higher than max capacity")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

class SalesHistory(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, through='SalesHistoryProduct')
    date = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return f"{self.store} - {self.date}"
    
class SalesHistoryProduct(models.Model):
    sales_history = models.ForeignKey(SalesHistory, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    def __str__(self):
        return f"({self.sales_history} - {self.product})"