from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views

urlpatterns = [
    path('', views.adminlogin, name='adminlogin'),
    path('adminlogout/', views.adminlogout, name='adminlogout'),
    path('dashboard/', views.dashboard, name='dashboard'),


    # -----Customer Management-----
    path('customers/', views.customers, name='customers'),
    path('customers/<int:id>/block/', views.block_customer, name='block_customer'),
    path('customers/<int:id>/unblock/', views.unblock_customer, name='unblock_customer'),
    path('customersearch/',views.customer_search,name='customerSearch'),


    # -----Category Management-----
    path('category/', views.category, name='category'),
    path('category/add/', views.add_category, name='add_category'),
    path('categories/edit/<int:id>/', views.edit_category, name='edit_category'),
    path('categories/delete/<int:id>/', views.delete_category, name='delete_category'),
    path('categorysearch/',views.category_search,name='categorySearch'),

    # -----Products Managemnet------
    path('products/', views.products, name='products'),
    path('products/add/', views.add_product, name='add_product'), 
    path('products/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('products/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('productsearch/',views.product_search,name='productSearch'),

    # ------order management-----
    path('orders/', views.orders, name='orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('inventory/', views.inventory, name='inventory'),
    path('inventory/update/<int:product_id>/', views.update_stock, name='update_stock'),

]




if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)