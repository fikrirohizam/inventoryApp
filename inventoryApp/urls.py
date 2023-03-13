from django.urls import include, path, re_path
from rest_framework import routers
from . import views
from rest_framework.authtoken import views as viewsRest
from rest_framework.urlpatterns import format_suffix_patterns



router = routers.DefaultRouter()
router.register(r'materials', views.MaterialViewSet, basename='materials')

urlpatterns = [

# Django rest framework project
    path('', include(router.urls), name='rest_index'),
    path('restock/', views.restock),

]