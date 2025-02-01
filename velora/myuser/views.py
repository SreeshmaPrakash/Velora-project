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


@login_required
def profile(request):
    context = {
        'active_tab': 'profile',
        'user': request.user,
        'customer': request.user.customer  
    }
    return render(request, 'user/profile.html', context)

@login_required
def manage_addresses(request):
    addresses = Address.objects.filter(user=request.user, is_deleted=False)
    context = {
        'active_tab': 'addresses',
        'addresses': addresses
    }
    return render(request, 'user/profile.html', context)

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'active_tab': 'orders',
        'orders': orders
    }
    return render(request, 'user/profile.html', context)

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
def add_address(request):
    if request.method == 'POST':
        try:
            address = Address(
                user=request.user,
                full_name=request.POST.get('full_name'),
                phone=request.POST.get('phone'),
                address_line1=request.POST.get('address_line1'),
                address_line2=request.POST.get('address_line2'),
                city=request.POST.get('city'),
                state=request.POST.get('state'),
                pincode=request.POST.get('pincode'),
                is_default=request.POST.get('is_default') == 'on'
            )
            
            if address.is_default:
                # Remove default from other addresses
                Address.objects.filter(user=request.user).update(is_default=False)
            
            address.save()
            messages.success(request, 'Address added successfully!')
        except Exception as e:
            messages.error(request, f'Error adding address: {str(e)}')
    return redirect('profile')


@login_required(login_url='userlogin')
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        try:
            address.full_name = request.POST.get('full_name')
            address.phone = request.POST.get('phone')
            address.address_line1 = request.POST.get('address_line1')
            address.address_line2 = request.POST.get('address_line2')
            address.city = request.POST.get('city')
            address.state = request.POST.get('state')
            address.pincode = request.POST.get('pincode')
            
            is_default = request.POST.get('is_default') == 'on'
            if is_default:
                Address.objects.filter(user=request.user).update(is_default=False)
                address.is_default = True
                
            address.save()
            messages.success(request, 'Address updated successfully!')
            return redirect('profile')
        except Exception as e:
            messages.error(request, f'Error updating address: {str(e)}')
            
    return render(request, 'user/edit_address.html', {'address': address})



@login_required(login_url='userlogin')
def delete_address(request, address_id):
    if request.method == 'POST':
        address = get_object_or_404(Address, id=address_id, user=request.user)
        address.is_deleted = True
        address.save()
        messages.success(request, 'Address deleted successfully!')
    return redirect('profile')



@login_required(login_url='userlogin')
def set_default_address(request, address_id):
    if request.method == 'POST':
        address = get_object_or_404(Address, id=address_id, user=request.user)
        Address.objects.filter(user=request.user).update(is_default=False)
        address.is_default = True
        address.save()
        messages.success(request, 'Default address updated successfully!')
    return redirect('profile')


@login_required(login_url='userlogin')
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.orderitem_set.all().select_related('product')
    
    context = {
        'order': order,
        'order_items': order_items,
        'shipping_address': order.shipping_address,
        'billing_address': order.billing_address,
    }
    return render(request, 'user/order_detail.html', context)


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
def view_cart(request):
    try:
        cart = Cart.objects.get(user=request.user)
        
        # Properly prefetch product images
        cart_items = CartItem.objects.filter(cart=cart)\
            .select_related('product')\
            .prefetch_related(
                'product__product_images',
                'product__images'
            ).all()
        
        subtotal = sum(item.quantity * item.price for item in cart_items)
        total = subtotal - getattr(cart, 'discount', 0)
        
        context = {
            'cart_items': cart_items,
            'subtotal': subtotal,
            'discount': getattr(cart, 'discount', 0),
            'total': total
        }
        return render(request, 'user/cart.html', context)
    except Cart.DoesNotExist:
        cart = Cart.objects.create(user=request.user)
        context = {
            'cart_items': [],
            'subtotal': 0,
            'discount': 0,
            'total': 0
        }
        return render(request, 'user/cart.html', context)
    except Exception as e:
        messages.error(request, f'Error viewing cart: {str(e)}')
        return redirect('userhome')


@login_required(login_url='userlogin') 
def add_to_cart(request, product_id):
    if request.method == 'POST':
        try:
            product = get_object_or_404(Products, id=product_id)
            quantity = int(request.POST.get('quantity', 1))
            
            # Validate quantity
            if quantity <= 0:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Quantity must be positive'
                })
            
            # Check maximum quantity limit (4 or stock)
            max_allowed = min(4, product.stock)
            if quantity > max_allowed:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Maximum quantity allowed is {max_allowed}'
                })
            
            # Get or create cart
            cart, _ = Cart.objects.get_or_create(user=request.user)
            
            # Check existing cart item
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={
                    'quantity': 0,
                    'price': product.price
                }
            )
            
            # Check total quantity including existing items
            new_total_quantity = cart_item.quantity + quantity
            if new_total_quantity > max_allowed:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Cannot add more items. Maximum allowed is {max_allowed}'
                })
            
            # Update cart item
            cart_item.quantity = new_total_quantity
            cart_item.price = product.price
            cart_item.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Product added to cart successfully!',
                'cart_count': cart.items.count(),
                'cart_total': float(sum(item.quantity * item.price for item in cart.items.all()))
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@login_required(login_url='userlogin') 
def update_cart(request, item_id):
    if request.method == 'POST':
        try:
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
            quantity = int(request.POST.get('quantity', 1))
            
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



@login_required(login_url='userlogin') 
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
    

@login_required
def checkout(request):
    try:
        # Get user's cart
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.select_related('product').all()
        
        if not cart_items:
            messages.error(request, 'Your cart is empty')
            return redirect('view_cart')
        
        # Get user's saved addresses
        addresses = Address.objects.filter(user=request.user, is_deleted=False)
        
        # Calculate totals
        subtotal = sum(item.quantity * item.price for item in cart_items)
        shipping_fee = Decimal('40.00')
        total = subtotal + shipping_fee
        
        if request.method == 'POST':
            address_id = request.POST.get('address')
            payment_method = request.POST.get('payment_method')
            
            if not address_id:
                messages.error(request, 'Please select a delivery address')
                return redirect('checkout')
            
            try:
                with transaction.atomic():
                    address = Address.objects.get(id=address_id, user=request.user, is_deleted=False)
                    
                    # Create order
                    order = Order.objects.create(
                        user=request.user,
                        shipping_address=f"{address.address_line1} {address.address_line2}".strip(),
                        shipping_city=address.city,
                        shipping_state=address.state,
                        shipping_pincode=address.pincode,
                        shipping_phone=address.phone,
                        payment_method=payment_method,
                        subtotal=subtotal,
                        shipping_fee=shipping_fee,
                        total=total
                    )
                    
                    # Create order items
                    for cart_item in cart_items:
                        OrderItem.objects.create(
                            order=order,
                            product=cart_item.product,
                            quantity=cart_item.quantity,
                            price=cart_item.price
                        )
                        
                        # Update product stock
                        product = cart_item.product
                        if product.stock >= cart_item.quantity:
                            product.stock -= cart_item.quantity
                            product.save()
                        else:
                            raise ValueError(f'Insufficient stock for {product.name}')
                    
                    # Clear cart after successful order creation
                    cart.items.all().delete()
                    
                    messages.success(request, 'Order placed successfully!')
                    return redirect('order_confirmation', order_id=order.id)
                    
            except Address.DoesNotExist:
                messages.error(request, 'Invalid address selected')
                return redirect('checkout')
            except ValueError as e:
                messages.error(request, str(e))
                return redirect('checkout')
            except Exception as e:
                messages.error(request, f'Error processing order: {str(e)}')
                return redirect('checkout')
                
        context = {
            'cart_items': cart_items,
            'addresses': addresses,
            'subtotal': subtotal,
            'shipping_fee': shipping_fee,
            'total': total,
        }
        return render(request, 'user/checkout.html', context)
        
    except Cart.DoesNotExist:
        messages.error(request, 'Your cart is empty')
        return redirect('view_cart')
    
@login_required
def add_address(request):
    if request.method == 'POST':
        try:
            # Get form data
            full_name = request.POST.get('full_name')
            phone = request.POST.get('phone')
            address_line1 = request.POST.get('address_line1')
            address_line2 = request.POST.get('address_line2')
            city = request.POST.get('city')
            state = request.POST.get('state')
            pincode = request.POST.get('pincode')
            is_default = request.POST.get('is_default') == 'on'

            # Validate required fields
            if not all([full_name, phone, address_line1, city, state, pincode]):
                messages.error(request, 'Please fill all required fields')
                return redirect('add_address')

            # If this is the first address or set as default
            if is_default:
                # Set all other addresses as non-default
                Address.objects.filter(user=request.user).update(is_default=False)

            # Create new address
            Address.objects.create(
                user=request.user,
                full_name=full_name,
                phone=phone,
                address_line1=address_line1,
                address_line2=address_line2,
                city=city,
                state=state,
                pincode=pincode,
                is_default=is_default
            )

            messages.success(request, 'Address added successfully')
            return redirect('checkout')  # or wherever you want to redirect

        except Exception as e:
            messages.error(request, f'Error adding address: {str(e)}')
            return redirect('add_address')

    return render(request, 'user/add_address.html')

@login_required
def manage_addresses(request):
    addresses = Address.objects.filter(user=request.user, is_deleted=False)
    return render(request, 'user/manage_addresses.html', {'addresses': addresses})

@login_required
def edit_address(request, address_id):
    try:
        address = Address.objects.get(id=address_id, user=request.user, is_deleted=False)
        
        if request.method == 'POST':
            address.full_name = request.POST.get('full_name')
            address.phone = request.POST.get('phone')
            address.address_line1 = request.POST.get('address_line1')
            address.address_line2 = request.POST.get('address_line2')
            address.city = request.POST.get('city')
            address.state = request.POST.get('state')
            address.pincode = request.POST.get('pincode')
            is_default = request.POST.get('is_default') == 'on'

            if is_default:
                Address.objects.filter(user=request.user).update(is_default=False)
                address.is_default = True

            address.save()
            messages.success(request, 'Address updated successfully')
            return redirect('manage_addresses')

        return render(request, 'user/edit_address.html', {'address': address})

    except Address.DoesNotExist:
        messages.error(request, 'Address not found')
        return redirect('manage_addresses')

@login_required
def delete_address(request, address_id):
    try:
        address = Address.objects.get(id=address_id, user=request.user, is_deleted=False)
        address.is_deleted = True
        address.save()
        messages.success(request, 'Address deleted successfully')
    except Address.DoesNotExist:
        messages.error(request, 'Address not found')
    return redirect('manage_addresses')


@login_required
def order_confirmation(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        context = {
            'order': order,
            'order_items': order.items.all()
        }
        return render(request, 'user/order_confirmation.html', context)
    except Order.DoesNotExist:
        messages.error(request, 'Order not found')
        return redirect('view_cart')
    



