from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from decimal import Decimal
from django.utils import timezone  
import random


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=(('M', 'Male'), ('F', 'Female')),default='M', null=True, blank=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    pincode = models.CharField(max_length=6, blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    @staticmethod
    def generate_otp():
        return str(random.randint(1000, 9999))
    
    def is_valid(self):
        now = timezone.now()
        time_diff = now - self.created_at
        return not self.is_used and time_diff.total_seconds() <= 30

class Wallet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.FloatField(default=0.0)


# Category Model
class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name


# Product Models
class Products(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.IntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    images = models.ManyToManyField('Productimage', related_name='product_images')

    def soft_delete(self):
        self.is_deleted = True
        self.save()

    def __str__(self):
        return self.name
    
    # Compute the discount percentage
    def discount_percentage(self):
        if self.discount_price and self.discount_price < self.price:
            discount = (self.price - self.discount_price) / self.price * 100
            return round(discount, 2)
        return 0

    # Define the original price
    def original_price(self):
        if self.discount_price:
            return self.price
        return None

class Productimage(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='product_images')
    image = models.ImageField(upload_to='product_images/')
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def save(self, *args, **kwargs):
        # Process image before saving
        if self.image:
            self.resize_and_crop_image()
        super().save(*args, **kwargs)

    def resize_and_crop_image(self):
        img = Image.open(self.image)
        
        # Convert to RGB if image is in RGBA mode
        if img.mode == 'RGBA':
            img = img.convert('RGB')

        # Calculate aspect ratio
        aspect_ratio = 1  # For square images. Change as needed

        # Get current dimensions
        width, height = img.size

        # Calculate dimensions to crop to
        if width > height:
            new_width = height
            new_height = height
            left = (width - height) / 2
            top = 0
            right = (width + height) / 2
            bottom = height
        else:
            new_width = width
            new_height = width
            left = 0
            top = (height - width) / 2
            right = width
            bottom = (height + width) / 2

        # Crop image
        img = img.crop((left, top, right, bottom))

        # Resize image
        THUMBNAIL_SIZE = (800, 800)  # Adjust size as needed
        img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

        # Save the processed image
        img.save(self.image.path, quality=90, optimize=True)

# Order and Payment Models
class PaymentMethod(models.Model):
    name = models.CharField(max_length=100)


class OrderStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    SHIPPED = 'shipped', 'Shipped'
    DELIVERED = 'delivered', 'Delivered'
    CANCELLED = 'cancelled', 'Cancelled'
    RETURNED = 'returned', 'Returned'


class Order(models.Model):
    ORDER_STATUS = (
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled')
    )

    PAYMENT_METHODS = (
        ('COD', 'Cash on Delivery'),
        ('ONLINE', 'Online Payment')
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    shipping_address = models.TextField(default='')
    shipping_city = models.CharField(max_length=100, default='')
    shipping_state = models.CharField(max_length=100, default='')
    shipping_pincode = models.CharField(max_length=10, default='')
    shipping_phone = models.CharField(max_length=15, default='')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='COD')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=40.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def generate_order_number(self):
        date = timezone.now().strftime('%Y%m%d')
        # Get the count of orders for today
        count = Order.objects.filter(
            created_at__date=timezone.now().date()
        ).count()
        # Generate order number with date and sequential number
        return f'ORD{date}{str(count + 1).zfill(4)}'

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Keep trying until we get a unique order number
            while True:
                order_number = self.generate_order_number()
                if not Order.objects.filter(order_number=order_number).exists():
                    self.order_number = order_number
                    break
        
        if not self.total:
            self.total = self.subtotal + self.shipping_fee
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order_number} by {self.user.username}"

    class Meta:
        ordering = ['-created_at']

class OrderItem(models.Model):
    order = models.ForeignKey('Order', related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('Products', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def get_total(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

# Wallet Transaction and Coupons
class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=20)
    amount = models.FloatField()
    date = models.DateField()
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='wallet_product')


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20)
    discount_value = models.FloatField()
    valid_from = models.DateField()
    valid_till = models.DateField()
    max_uses = models.IntegerField()
    is_active = models.BooleanField(default=True)


class AppliedCoupon(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applied_coupons')
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='applied_users')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='coupons')
    applied_at = models.DateField()
    limit = models.IntegerField()


# Cart and Wishlist Models
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def get_total(self):
        return sum(item.get_cost() for item in self.items.all())

    def get_items_count(self):
        return self.items.count()

    def __str__(self):
        return f"Cart for {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 

    def get_cost(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateField(auto_now_add=True)


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='wishlist_items')
    added_at = models.DateField(auto_now_add=True)


# Other Models
class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField()


class Offer(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='offers')
    name = models.CharField(max_length=255)
    discount_type = models.CharField(max_length=20)
    discount_value = models.FloatField()
    valid_from = models.DateField()
    valid_till = models.DateField()
    max_uses = models.IntegerField()
    is_active = models.BooleanField(default=True)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=4, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

    def __str__(self):
        return self.user.username


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.rating}'

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=100, default="")
    phone = models.CharField(max_length=15, default="")
    address_line1 = models.CharField(max_length=255, default="")
    address_line2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, default="")
    state = models.CharField(max_length=100, default="")
    pincode = models.CharField(max_length=6, default="")
    is_default = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name}'s address in {self.city}"
    
class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=50)
    new_status = models.CharField(max_length=50)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class StockHistory(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='stock_history')
    old_stock = models.IntegerField()
    new_stock = models.IntegerField()
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)