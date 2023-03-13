from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Store, Product, Material, MaterialQuantity, MaterialStock
# Register your models here.

admin.site.register(User, UserAdmin)
admin.site.register(Store)
admin.site.register(Product)
admin.site.register(Material)
admin.site.register(MaterialQuantity)
admin.site.register(MaterialStock)
