from django.db import models
from django.contrib.auth.models import AbstractUser

class Address(models.Model):
    street = models.CharField(max_length=255, blank=True, null=True)      
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
        return f"{self.street}, {self.city}, {self.state}, {self.country}"

    class Meta:
        verbose_name = 'Address'
        verbose_name_plural = 'Addresses'
        
def get_default_category():
    return Category.objects.get_or_create(name="All Products")[0].id

class CustomUser(AbstractUser):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    username = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, null=True, unique=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    address = models.OneToOneField('Address', on_delete=models.SET_NULL, null=True, blank=True, related_name='user')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.username} - {self.email}"

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        

        
class Category(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

        
class Product(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    slash_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to='product_images/', )
    category = models.ForeignKey(
        "Category",
        on_delete=models.CASCADE,
        related_name="products",
        default=get_default_category
    )
    in_stock = models.PositiveIntegerField(default=0, help_text="Number of items in stock")
    description = models.TextField(blank=True, null=True)    
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.name} - {self.price}"

    def delete(self, *args, **kwargs):
        self.is_active = False
        self.save()

    # def is_purchased(self):
    #     """Checks if this product is linked to an approved transaction."""
    #     return self.transactions.filter(transaction_status="approved").exists()

    # is_purchased.boolean = True  # Shows as a boolean (Yes/No) in Django Admin
    # is_purchased.short_description = "Purchased"  # Column name in Django Admin

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField()
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name} - {self.rating} stars"

    class Meta:
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        ordering = ['-created_at']


    
# models.py
class Transaction(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    products = models.ManyToManyField(Product, related_name='transactions')
    tx_ref = models.CharField(max_length=100, unique=True)  # Ensure unique tx_ref
    flw_transaction_id = models.CharField(max_length=100, blank=True, null=True)  # Store Flutterwave transaction ID
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)  # Link to address
    TRANSACTION_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    )
    transaction_status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='pending')
    transaction_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username if self.user else 'Anonymous'} - {self.amount} - {self.transaction_status}"

    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-transaction_date']
        
class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='cart', null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)  # For anonymous users
    created_at = models.DateTimeField(auto_now_add=True)
    products = models.ManyToManyField(Product, related_name='cart_items', blank=True)

    def __str__(self):
        if self.user:
            return f"Cart of {self.user.username}"
        else:
            return f"Cart for session {self.session_key}"

    def total_price(self):
        return sum(item.total_price() for item in self.items.all())



class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        if self.cart and self.cart.user:
            return f"{self.quantity} of {self.product.name} in {self.cart.user.username}'s cart"
        return f"{self.quantity} of {self.product.name} in an anonymous cart"

    def total_price(self):
        return self.product.price * self.quantity
