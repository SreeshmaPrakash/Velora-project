
from django.urls import path,include
from . import views

urlpatterns = [
    path('', views.userhome,name='userhome'),
    path('userlogin/', views.userlogin,name='userlogin'),
    path('userlogout/', views.userlogout,name='userlogout'),
    path('signup/', views.usersignup, name='usersignup'),
    path('verify_signup_otp/', views.verify_signup_otp, name='verify_signup_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    
    path('products/', views.product_list, name='product_list'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('category/<int:category_id>/', views.category_products, name='category_products'),


    # -----user profile------
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('order/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('address/<int:address_id>/set-default/', views.set_default_address, name='set_default_address'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),


    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/<int:item_id>/', views.update_cart, name='update_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
]
