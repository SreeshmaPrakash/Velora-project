from django.db import models
from django.contrib.auth.models import User
from PIL import Image


# Customer and Wallet Models
class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer')
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    is_blocked = models.BooleanField(default=False)

    def __str__(self):
        return self.name


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


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    phone = models.CharField(max_length=15)
    is_default = models.BooleanField(default=False)


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, related_name='orders')
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, related_name='orders')
    total_price = models.FloatField()
    created_at = models.DateField(auto_now_add=True)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.IntegerField()
    price = models.FloatField()
    status = models.CharField(max_length=50)


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
    discount = models.FloatField(default=0.0)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='carts')


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.IntegerField()
    price = models.FloatField()


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
    otp = models.CharField(max_length=6, blank=True, null=True)

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
