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
from decimal import Decimal
from django.http import JsonResponse
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.contrib.auth import update_session_auth_hash

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
    for product in products:
        original_price = product.original_price
        current_price = product.price  
        
        if original_price and isinstance(original_price, Decimal) and original_price > current_price:
            discount = original_price - current_price
            discount_percentage = (discount / original_price) * Decimal('100')
            product.discount_price = discount  
            product.discount_percentage = round(float(discount_percentage), 2)
        else:
            product.discount_price = Decimal('0')
            product.discount_percentage = None

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


@never_cache
@login_required(login_url='userlogin')
def profile_view(request):
    user = request.user
    try:
        customer = Customer.objects.get(user=user)
    except Customer.DoesNotExist:
        customer = Customer.objects.create(user=user)
    
    # Get orders with pagination
    orders = Order.objects.filter(user=user).order_by('-created_at')
    
    # Get addresses
    addresses = Address.objects.filter(user=user, is_deleted=False)
    
    if request.method == 'POST':
        if request.POST.get('action') == 'cancel_order':
            order_id = request.POST.get('order_id')
            try:
                order = Order.objects.get(id=order_id, user=user)
                if order.status not in ['delivered', 'cancelled']:
                    order.status = 'cancelled'
                    order.save()
                    messages.success(request, 'Order cancelled successfully!')
                else:
                    messages.error(request, 'This order cannot be cancelled.')
            except Order.DoesNotExist:
                messages.error(request, 'Order not found.')
            return redirect('profile')
    
    context = {
        'customer': customer,
        'orders': orders,
        'addresses': addresses,
    }
    return render(request, 'user/profile.html', context)


@never_cache
@login_required(login_url='userlogin')
def edit_profile(request):
    user = request.user
    try:
        customer = Customer.objects.get(user=user)
    except Customer.DoesNotExist:
        customer = Customer.objects.create(user=user)
    
    # Initialize forms
    user_form = UserUpdateForm(instance=user)
    password_form = CustomPasswordChangeForm(user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_profile':
            user_form = UserUpdateForm(request.POST, instance=user)
            try:
                with transaction.atomic():
                    if user_form.is_valid():
                        user_form.save()
                        
                        # Update Customer information
                        customer.phone = request.POST.get('phone', '').strip()
                        customer.gender = request.POST.get('gender', '')
                        customer.city = request.POST.get('city', '').strip()
                        customer.pincode = request.POST.get('pincode', '').strip()
                        customer.save()
                        
                        messages.success(request, 'Profile updated successfully!')
                        return redirect('profile')
                    else:
                        messages.error(request, 'Please correct the errors below.')
            except Exception as e:
                messages.error(request, f'Error updating profile: {str(e)}')

        elif action == 'change_password':
            password_form = CustomPasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                try:
                    user = password_form.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, 'Password changed successfully!')
                    return redirect('profile')
                except Exception as e:
                    messages.error(request, f'Error changing password: {str(e)}')
            else:
                messages.error(request, 'Please correct the password errors.')
    
    context = {
        'customer': customer,
        'user_form': user_form,
        'password_form': password_form,
    }
    return render(request, 'user/edit_profile.html', context)

@login_required(login_url='userlogin')
def cancel_order(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id, user=request.user)
        if order.status in ['pending', 'processing']:
            order.status = 'cancelled'
            order.save()
            messages.success(request, 'Order cancelled successfully!')
        else:
            messages.error(request, 'This order cannot be cancelled.')
    return redirect('profile')


@login_required(login_url='userlogin')
def set_default_address(request, address_id):
    if request.method == 'POST':
        address = get_object_or_404(Address, id=address_id, user=request.user)
        # Remove default from other addresses
        Address.objects.filter(user=request.user).update(is_default=False)
        # Set new default
        address.is_default = True
        address.save()
        messages.success(request, 'Default address updated successfully!')
    return redirect('profile')


@login_required(login_url='userlogin')
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'user/order_detail.html', {'order': order})


@login_required
def view_cart(request):
    try:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.select_related('product').all()  
        
        subtotal = sum(item.quantity * item.price for item in cart_items)
        total = subtotal - cart.discount
        
        context = {
            'cart_items': cart_items,
            'subtotal': subtotal,
            'discount': cart.discount,
            'total': total
        }
        return render(request, 'user/cart.html', context)
    except Exception as e:
        messages.error(request, f'Error viewing cart: {str(e)}')
        return redirect('userhome')


@login_required
def add_to_cart(request, product_id):
    if request.method == 'POST':
        # Add logging to track function entry
        print(f"Adding to cart - Product ID: {product_id}, User: {request.user.username}")
        
        try:
            product = get_object_or_404(Products, id=product_id)
            print(f"Product found: {product.name}, Stock: {product.stock}, Active: {product.is_active}")
            
            # Check if product is active and in stock
            if not product.is_active:
                message = 'This product is not available'
                print(f"Error: {message}")
                return JsonResponse({
                    'status': 'error',
                    'message': message
                }) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else redirect('product_detail', product_id=product_id)
            
            # Validate quantity with better error handling
            try:
                quantity = int(request.POST.get('quantity', 1))
                print(f"Requested quantity: {quantity}")
            except ValueError:
                message = 'Invalid quantity provided'
                print(f"Error: {message}")
                return JsonResponse({
                    'status': 'error',
                    'message': message
                }) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else redirect('product_detail', product_id=product_id)
            
            if quantity <= 0:
                message = 'Quantity must be positive'
                print(f"Error: {message}")
                return JsonResponse({
                    'status': 'error',
                    'message': message
                }) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else redirect('product_detail', product_id=product_id)
                
            if quantity > product.stock:
                message = 'Not enough stock available'
                print(f"Error: {message} (Requested: {quantity}, Available: {product.stock})")
                return JsonResponse({
                    'status': 'error',
                    'message': message
                }) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else redirect('product_detail', product_id=product_id)
            
            # Get or create cart with error handling
            try:
                cart, created = Cart.objects.get_or_create(user=request.user)
                print(f"Cart {'created' if created else 'retrieved'} for user")
            except Exception as e:
                print(f"Error creating/getting cart: {str(e)}")
                raise
            
            # Calculate correct price
            current_price = product.discount_price if product.discount_price else product.price
            print(f"Product price: {current_price}")
            
            try:
                # Check if product already in cart
                cart_item, item_created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=product,
                    defaults={
                        'quantity': quantity,
                        'price': current_price
                    }
                )
                
                if not item_created:
                    # Update quantity and price
                    cart_item.quantity += quantity
                    cart_item.price = current_price
                    cart_item.save()
                
                print(f"Cart item {'created' if item_created else 'updated'} - Quantity: {cart_item.quantity}")
                
                messages.success(request, 'Product added to cart successfully!')
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    cart_count = cart.items.count()
                    cart_total = sum(item.quantity * item.price for item in cart.items.all())
                    print(f"Cart updated - Count: {cart_count}, Total: {cart_total}")
                    
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Product added to cart successfully!',
                        'cart_count': cart_count,
                        'cart_total': cart_total
                    })
                    
                return redirect('view_cart')
                
            except Exception as e:
                print(f"Error handling cart item: {str(e)}")
                raise
                
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                })
            messages.error(request, f'Error adding to cart: {str(e)}')
            return redirect('product_detail', product_id=product_id)
    
    # Log non-POST requests
    print(f"Non-POST request received: {request.method}")
    return redirect('product_detail', product_id=product_id)

    
@login_required
def update_cart(request, item_id):
    if request.method == 'POST':
        try:
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
            quantity = int(request.POST.get('quantity', 0))
            
            if quantity > 0:
                if quantity > cart_item.product.stock:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Not enough stock available'
                    }) if request.headers.get('X-Requested-With') == 'XMLHttpRequest' else redirect('view_cart')
                
                cart_item.quantity = quantity
                cart_item.save()
                messages.success(request, 'Cart updated successfully!')
            else:
                cart_item.delete()
                messages.success(request, 'Product removed from cart!')
                
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                cart = cart_item.cart
                cart_items = cart.items.all()
                subtotal = sum(item.quantity * item.price for item in cart_items)
                total = subtotal - cart.discount
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Cart updated successfully!',
                    'subtotal': float(subtotal),
                    'discount': float(cart.discount),
                    'total': float(total),
                    'cart_count': cart.items.count()
                })
            return redirect('view_cart')
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                })
            messages.error(request, f'Error updating cart: {str(e)}')
            return redirect('view_cart')
    
    return redirect('view_cart')

@login_required
def remove_from_cart(request, item_id):
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart = cart_item.cart
        cart_item.delete()
        messages.success(request, 'Product removed from cart!')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            cart_total = sum(item.quantity * item.price for item in cart.items.all())
            return JsonResponse({
                'status': 'success',
                'message': 'Product removed successfully!',
                'cart_count': cart.items.count(),
                'cart_total': float(cart_total)
            })
            
        return redirect('view_cart')
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
        messages.error(request, f'Error removing item: {str(e)}')
        return redirect('view_cart')