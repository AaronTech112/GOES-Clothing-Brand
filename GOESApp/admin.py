from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from .models import (
    CustomUser,
    Address,
    Category,
    Product,
    Review,
    Transaction,
    Cart,
    CartItem,
    Newsletter,
    Color,
    Size,
    ProductImage,
    HomePageImages,
    DiscountCode,
    OrderItem
)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'is_staff',
    )
    list_filter = (
        'is_staff', 'is_active',
    )
    search_fields = (
        'email', 'username', 'first_name', 'last_name',
    )
    ordering = ('email',)
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': (
            'phone_number', 'profile_picture', 'bio', 'address',
        )}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': (
            'phone_number', 'profile_picture', 'bio', 'address',
        )}),
    )

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('street', 'city', 'state', 'postal_code', 'country')
    search_fields = ('street', 'city', 'state', 'postal_code', 'country')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', 'description')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'comment')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('tx_ref', 'user', 'amount', 'transaction_status', 'transaction_date', 'flw_transaction_id', 'address')
    list_filter = ('transaction_status', 'transaction_date')
    search_fields = ('tx_ref', 'user__username', 'flw_transaction_id')
    actions = ['approve_transactions', 'decline_transactions']

    def approve_transactions(self, request, queryset):
        queryset.update(transaction_status='approved')
        self.message_user(request, "Selected transactions have been approved.")
    approve_transactions.short_description = "Approve selected transactions"

    def decline_transactions(self, request, queryset):
        queryset.update(transaction_status='declined')
        self.message_user(request, "Selected transactions have been declined.")
    decline_transactions.short_description = "Decline selected transactions"

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_key')
    search_fields = ('user__username', 'session_key')

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity')
    search_fields = ('product__name',)

@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at')
    search_fields = ('email',)
    
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'in_stock', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')
    inlines = [ProductImageInline]
    filter_horizontal = ('sizes', 'colors')  # Use filter_horizontal for better many-to-many UI
    
@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'hex_code')
    search_fields = ('name',)
    
admin.site.register(HomePageImages)

admin.site.register(DiscountCode)

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'product', 'quantity', 'price')
    list_filter = ('transaction__transaction_status',)
    search_fields = ('transaction__tx_ref', 'product__name')
