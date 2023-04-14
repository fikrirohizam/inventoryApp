from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Store, Product, Material, MaterialQuantity, MaterialStock, SalesHistory, SalesHistoryProduct
# Register your models here.

admin.site.register(User, UserAdmin)
admin.site.register(Store)
admin.site.register(Product)
admin.site.register(Material)
admin.site.register(MaterialQuantity)
admin.site.register(MaterialStock)
admin.site.register(SalesHistory)
admin.site.register(SalesHistoryProduct)

