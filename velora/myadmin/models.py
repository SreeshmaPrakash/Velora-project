from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from decimal import Decimal


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=(('M', 'Male'), ('F', 'Female')),default='M', null=True, blank=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    pincode = models.CharField(max_length=6, blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)


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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, default='ORD000001')
    payment_method = models.ForeignKey('PaymentMethod', on_delete=models.SET_NULL, null=True)
    address = models.ForeignKey('Address', on_delete=models.SET_NULL, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number or self.order_number == 'ORD000001':
            last_order = Order.objects.order_by('-id').first()
            if last_order and last_order.order_number != 'ORD000001':
                last_number = int(last_order.order_number[3:])
                self.order_number = f"ORD{str(last_number + 1).zfill(6)}"
            else:
                self.order_number = "ORD000001"
        super().save(*args, **kwargs)


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