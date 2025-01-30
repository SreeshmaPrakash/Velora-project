from django.contrib import admin
from .models import Customer, Category, Products, Productimage
# Register your models here.
admin.site.register({Customer, Category, Products, Productimage})