from django import forms
from .models import Products, Productimage, Category

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class ProductForm(forms.ModelForm):
    class Meta:
        model = Products
        fields = ['name', 'description', 'price','discount_price', 'stock', 'category', 'is_active', 'is_featured']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product description'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter price'
            }),
            'discount_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter discounted price'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter stock quantity'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
    def clean_discount_price(self):
        discount_price = self.cleaned_data.get('discount_price')
        price = self.cleaned_data.get('price')

        if discount_price and discount_price >= price:
            raise forms.ValidationError("Discount price must be less than the original price.")
        return discount_price
    
    product_images = MultipleFileField(
        required=True,
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )

    def clean_product_images(self):
        images = self.files.getlist('product_images')
        if len(images) < 3:
            raise forms.ValidationError("Please upload at least 3 images")
        
        for image in images:
            if not image.content_type.startswith('image'):
                raise forms.ValidationError("Please upload only image files")
            if image.size > 5*1024*1024:  # 5MB limit
                raise forms.ValidationError("Image file too large ( > 5mb )")
        
        return images


class ProductEditForm(forms.ModelForm):
    class Meta:
        model = Products
        fields = ['name', 'description', 'price', 'discount_price', 'stock', 'category', 'is_active', 'is_featured']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product description'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter price'
            }),
            'discount_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter discounted price'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter stock quantity'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    def clean_discount_price(self):
        discount_price = self.cleaned_data.get('discount_price')
        price = self.cleaned_data.get('price')

        if discount_price and discount_price >= price:
            raise forms.ValidationError("Discount price must be less than the original price.")
        return discount_price
    

    # Optional field for new images
    product_images = MultipleFileField(
        required=False,  # Not required during edit
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )

    def clean_product_images(self):
        images = self.files.getlist('product_images')
        if images:  # Only validate if new images are uploaded
            if len(images) < 3:
                raise forms.ValidationError("Please upload at least 3 images")
            
            for image in images:
                if not image.content_type.startswith('image'):
                    raise forms.ValidationError("Please upload only image files")
                if image.size > 5*1024*1024:  # 5MB limit
                    raise forms.ValidationError("Image file too large ( > 5mb )")
        
        return images

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = Productimage
        fields = ['image', 'alt_text', 'is_primary']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'alt_text': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter image description'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']