from django.db import models
from django.contrib.auth.models import AbstractUser
from django.forms import ValidationError

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
        percent = (100 * self.current_capacity/self.max_capacity)
        return float("%.2f" % percent)
    
    def __str__(self):
        s = self.store.store_name
        m = self.material.name
        c = self.current_capacity
        mc = self.max_capacity
        return ("%s (%s) %s/%s" % (s,m,c,mc))
    class Meta:
        unique_together = (('store', 'material'),)

    def clean(self):
        if self.current_capacity > self.max_capacity:
            raise ValidationError("Current capacity cannot be higher than max capacity")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

