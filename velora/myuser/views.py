from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from myadmin.models import *
from django.contrib.auth import get_user_model
import time
from .utils import generate_otp, send_otp
from django.db.models import Avg
from .forms import *


User = get_user_model()

@never_cache
@login_required(login_url='userlogin')
def userhome(request):
    products = Products.objects.filter(is_active=True)
    featured_products = Products.objects.filter(is_featured=True, is_active=True)
    context = {
        'products': products,
        'featured_products': featured_products,
    }
    return render(request, 'user/userhome.html', context)


def usersignup(request):
    if request.user.is_authenticated:
        return redirect('userhome')
        
    if request.method == 'POST':
        form = UserSignupForm(request.POST)
        if form.is_valid():
            # user = form.save()
            
            # Generate and send OTP
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password1']

            otp = generate_otp()
            
            # Store data in session
            request.session['signup_data'] = {
                'username': username,
                'email': email,
                'password': password,
                'otp': otp,
                'otp_time': time.time()
            }
            
            send_otp(email, otp)
            messages.success(request, 'Please verify your email with the OTP sent.')
            return redirect('verify_signup_otp')
    else:
        form = UserSignupForm()
    
    return render(request, 'user/usersignup.html', {'form': form})

def userlogin(request):
    if request.user.is_authenticated:
        return redirect('userhome')
        
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('userhome')
    else:
        form = UserLoginForm()
    
    return render(request, 'user/userlogin.html', {'form': form})

@never_cache
@login_required(login_url='userlogin')
def userlogout(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('userlogin')

def verify_signup_otp(request):
    signup_data = request.session.get('signup_data')
    if not signup_data:
        return redirect('usersignup')

    if request.method == 'POST':
        otp = int(request.POST.get('otp'))
        if signup_data and otp == signup_data['otp']:
            print("success")
            user = User.objects.create_user(
                username=signup_data['username'],
                email=signup_data['email'],
                password=signup_data['password']
            )
            user.save()
            messages.success(request, "Signup successful! Welcome!")
            return redirect('userlogin')
        else:
            messages.error(request, "Invalid OTP.")
    
    return render(request, 'user/verify_signup_otp.html',)
                                           

def resend_otp(request):
    signup_data = request.session.get('signup_data')
    
    if not signup_data:
        messages.error(request, 'Session expired. Please sign up again.')
        return redirect('usersignup')
    
    try:
        # Generate new OTP
        new_otp = generate_otp()
        
        # Update session with new OTP
        signup_data['otp'] = new_otp
        signup_data['otp_time'] = time.time()
        request.session['signup_data'] = signup_data
        request.session.modified = True
        
        # Send new OTP
        send_otp(signup_data['email'], new_otp)
        
        messages.success(request, 'New OTP has been sent to your email.')
        return redirect('verify_signup_otp')
        
    except Exception as e:
        messages.error(request, 'Failed to send OTP. Please try again.')
        return redirect('verify_signup_otp')


@never_cache
@login_required(login_url='userlogin')
def product_list(request):
    products = Products.objects.filter(is_active=True)
    categories = Category.objects.all()
    
    # Get category from URL parameter
    category_id = request.GET.get('category')
    selected_category = None

    # Filter by category
    if category_id:
        if category_id != 'all':  # Add this check for "all" category
            try:
                selected_category = Category.objects.get(id=category_id)
                products = products.filter(category=selected_category)
            except Category.DoesNotExist:
                pass

    # Filter by search
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(name__icontains=search_query)

    context = {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'search_query': search_query,
    }
    return render(request, 'user/product_list.html', context)


@never_cache
@login_required(login_url='userlogin')
def product_detail(request, product_id):
    product = get_object_or_404(Products, id=product_id, is_active=True)
    related_products = Products.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product_id)[:4]
    
    reviews = Review.objects.filter(product=product).order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Handle review submission
    if request.method == "POST":
        rating = request.POST.get("rating")
        comment = request.POST.get("comment")

        if rating and comment:
            Review.objects.create(
                product=product,
                user=request.user,
                rating=int(rating),
                comment=comment
            )
            messages.success(request, "Review added successfully!")
            return redirect('product_detail', product_id=product.id)

    context = {
        'product': product,
        'related_products': related_products,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'stock_status': get_stock_status(product),
    }
    return render(request, 'user/product_details.html', context)

def get_stock_status(product):
    if not product.is_active:
        return {
            'status': 'unavailable',
            'message': 'This product is currently unavailable',
            'class': 'text-danger'
        }
    elif product.stock <= 0:
        return {
            'status': 'out_of_stock',
            'message': 'Out of Stock',
            'class': 'text-danger'
        }
    elif product.stock <= 5:
        return {
            'status': 'low_stock',
            'message': f'Only {product.stock} left in stock - order soon',
            'class': 'text-warning'
        }
    else:
        return {
            'status': 'in_stock',
            'message': 'In Stock',
            'class': 'text-success'
        }
    
def category_products(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = Products.objects.filter(category=category, is_active=True)
    context = {
        'category': category,
        'products': products
    }
    return render(request, 'user/category_products.html', context)