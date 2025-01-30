from django.shortcuts import render, redirect, get_object_or_404,HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from .models import Customer, Category, Products, Productimage
from .forms import CategoryForm, ProductForm, ProductImageForm
from django.core.paginator import Paginator
from django.core.files.base import ContentFile
from .decorator import superuser_required
from .forms import ProductForm, ProductEditForm, ProductImageForm
from django.contrib.auth.models import User 

# ------admin login------
def adminlogin(request):


    if request.user.is_superuser:
        return redirect('dashboard')
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None: 
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, 'admin/adminlogin.html')

# -----admin logout------
def adminlogout(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect('adminlogin')

# -----admin dashboard------
@never_cache
@superuser_required
def dashboard(request):
    if not request.user.is_superuser:
        return HttpResponse("You are not authorized to view this page.")
    total_customers = User.objects.count()
    total_products = Products.objects.count()
    total_categories = Category.objects.count()
    total_images = Productimage.objects.count()

    context = {
        'total_customers': total_customers,
        'total_products': total_products,
        'total_categories': total_categories,
        'total_images': total_images,
    }
    return render(request, 'admin/dashboard.html', context)



#--------Customer Management--------

@never_cache
@superuser_required

def customer(request):
    customer_list = User.objects.all().order_by('-id')
    paginator = Paginator(customer_list, 10)
    page_number = request.GET.get('page')
    customers = paginator.get_page(page_number)
    return render(request, 'admin/customer.html', {'customers': customers})

# -----listing all customers------
@never_cache
@superuser_required
def customers(request):
    customers = User.objects.all()
    paginator = Paginator(customers, 10)
    page_number = request.GET.get('page')
    customers = paginator.get_page(page_number)
    return render(request, 'admin/customer.html', {'customers': customers})


# -----search customer-----
@never_cache
@superuser_required
def customer_search(request):
    if request.method=='POST':
        search = request.POST.get('search')
        if search is not None:
            user = User.objects.filter(username__icontains=search).order_by('username')
        else:
            user = User.objects.all()
        return render(request,'admin/admincustomers.html',{'customers': user})


# -----Block a customer-------
@never_cache
@superuser_required
def block_customer(request, id):
    customer = get_object_or_404(User, id=id)
    customer.is_active = False
    customer.save()
    messages.warning(request, f"{customer.username} has been blocked.")
    return redirect('customers')

# -----Unblock a customer-------
@never_cache
@superuser_required
def unblock_customer(request, id):
    customer = get_object_or_404(User, id=id)
    customer.is_active = True
    customer.save()
    messages.success(request, f"{customer.username} has been unblocked.")
    return redirect('customers')

# -----List all categories------
@never_cache
@superuser_required
def category(request):
    categories = Category.objects.filter(is_deleted=False)
    return render(request, 'admin/category.html', {'categories': categories})

@never_cache
@superuser_required
def category_search(request):
    if request.user.is_superuser:
        if request.method=='POST':
            search = request.POST.get('search')
            if search is not None:
                item = Category.objects.filter(name__icontains=search).order_by('name')
            else:
                item = Category.objects.all()
            return render(request,'admin/category.html',{'items':item})


# -----Add a category------
@never_cache
@superuser_required
def add_category(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category added successfully.")
            return redirect('category')
    else:
        form = CategoryForm()
    return render(request, 'admin/add_category.html', {'form': form})

# -----Edit a category------
@never_cache
@superuser_required
def edit_category(request, id):
    category = get_object_or_404(Category, id=id)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully.")
            return redirect('category')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'admin/edit_category.html', {'form': form})

# -----Delete a category (soft delete)------
@never_cache
@superuser_required
def delete_category(request, id):
    category = get_object_or_404(Category, id=id)
    category.is_deleted = True
    category.save()
    messages.success(request, "Category deleted successfully.")
    return redirect('category')


# -----List all products------
@never_cache
@superuser_required
def products(request):
    if request.user.is_superuser:
        product_list = Products.objects.all().order_by('-updated_at')
        category = Category.objects.all()
        
        paginator = Paginator(product_list, 5)
        page_number = request.GET.get('page')
        product = paginator.get_page(page_number)
        
        return render(request, 'admin/product.html', {'products': product, 'category': category})
    return redirect(adminlogin)

# -----search product-----
@never_cache
@superuser_required
def product_search(request):
    if request.user.is_superuser:
        if request.method=='POST':
            search = request.POST.get('search')
            if search:
                product = Products.objects.filter(name__icontains=search).order_by('name')
            else:
                product = Products.objects.all()
                
            return render(request,'admin/products.html',{'products':product})


# -----Add a product------
@superuser_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            
            # Handle multiple images
            images = request.FILES.getlist('product_images')
            for i, image in enumerate(images):
                Productimage.objects.create(
                    product=product,
                    image=image,
                    is_primary=(i == 0),
                    alt_text=f"{product.name} image {i+1}"
                )
            
            messages.success(request, 'Product added successfully')
            return redirect('products')
    else:
        form = ProductForm()
    
    return render(request, 'admin/add_product.html', {'form': form})



# -----Edit product------
@superuser_required
def edit_product(request, product_id):
    product = get_object_or_404(Products, id=product_id)
    
    if request.method == 'POST':
        form = ProductEditForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            
            # Handle new images if any
            new_images = request.FILES.getlist('product_images')
            if new_images:
                # Delete old images
                product.product_images.all().delete()
                
                # Add new images
                for i, image in enumerate(new_images):
                    Productimage.objects.create(
                        product=product,
                        image=image,
                        is_primary=(i == 0),
                        alt_text=f"{product.name} image {i+1}"
                    )
            
            messages.success(request, 'Product updated successfully')
            return redirect('products')
    else:
        form = ProductEditForm(instance=product)
    
    return render(request, 'admin/edit_product.html', {
        'form': form,
        'product': product
    })

# -----Delete a product (soft delete)------
@superuser_required
def delete_product(request, product_id):
    product = get_object_or_404(Products, id=product_id)
    product.is_active = False
    product.save()
    messages.success(request, 'Product deleted successfully')
    return redirect('products')


# -----Delete a productimage (soft delete)------

@superuser_required
def delete_product_image(request, image_id):
    image = get_object_or_404(Productimage, id=image_id)
    product = image.product
    
    # Don't allow deletion if it would leave less than 3 images
    if product.images.count() <= 3:
        messages.error(request, 'Product must have at least 3 images')
        return redirect('edit_product', product_id=product.id)
    
    image.delete()
    messages.success(request, 'Image deleted successfully')
    return redirect('edit_product', product_id=product.id)


# -----set primary image------
@superuser_required
def set_primary_image(request, image_id):
    image = get_object_or_404(Productimage, id=image_id)
    product = image.product
    
    # Remove primary status from all other images
    product.images.all().update(is_primary=False)
    
    # Set this image as primary
    image.is_primary = True
    image.save()
    
    messages.success(request, 'Primary image updated successfully')
    return redirect('edit_product', product_id=product.id)