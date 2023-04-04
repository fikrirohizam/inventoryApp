from django.urls import include, path, re_path
from rest_framework import routers
from inventoryApp import views
from rest_framework.authtoken import views as viewsRest
from rest_framework.urlpatterns import format_suffix_patterns



router = routers.DefaultRouter()


urlpatterns = [

    # Django rest framework project
    path('', include(router.urls), name='rest_index'),
    path('api-token-auth/', views.CustomAuthToken.as_view()),
    path('api/login/', views.login_view, name='login'),
    path('restock/', views.restock, name='restock'),
    path('restocks/', views.restocks, name='restocks'),

    path('inventory/', views.inventory, name='inventory'),
    path('product-capacity/', views.product_capacity, name='product_capacity'),
    path('sales/', views.sales, name='sales'),
    path('multisales/', views.multisales, name='multisales'),

    path('material-stocks/', views.MaterialStockListAPIView.as_view(), name='material_stocks'),
    path('material-stocks/<int:pk>', views.MaterialStockDetailAPIView.as_view(), name='material_stocks_detail'),
    path('products/', views.ProductListAPIView.as_view(), name='products'),
    path('products/<int:pk>', views.ProductDeleteAPIView.as_view(), name='products_delete'),

    #--------------------- HTML start -------------------------#
    path('login/', views.login_html_view, name='html_login'),
    path('products-list/', views.store_products, name='store_products'),
    path('products-add/', views.add_product, name='add_product'),
    path('products-delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('material-stock-list/', views.MaterialStockView.as_view(), name='store_stocks'),
    path('material-stock-update/<int:pk>', views.MaterialStockUpdateView.as_view(), name='update_stock'),
    path('material-stock-delete/<int:pk>', views.MaterialStockDeleteView.as_view(), name='delete_stock'),
    path('material-stock-add/<int:store_id>', views.MaterialStockCreateView.as_view(), name='add_stock'),
    path('logout/', views.logout_view, name='logout'),

]