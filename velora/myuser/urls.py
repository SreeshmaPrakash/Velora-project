
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
]
