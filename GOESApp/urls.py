from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


# Create your views here.
urlpatterns = [
    path('', views.home, name='home'),
    path('register', views.register, name='register'),
    path('shop/', views.shop, name='shop'),
    path('login_user', views.login_user, name='login_user'),
    path('logout_user', views.logout_user, name='logout_user'),
    path('profile', views.profile, name='profile'),
    path('cart', views.cart, name='cart'),
    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('product_detail/<int:product_id>/', views.product_detail, name='product_detail'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),  # Placeholder for checkout view
    path('initiate-payment/<int:transaction_id>/', views.initiate_payment, name='initiate_payment'),
    path('payment-callback/', views.payment_callback, name='payment_callback'),
    path('edit-address/', views.edit_address, name='edit_address'),
    path('thank-you/<int:transaction_id>/', views.thank_you, name='thank_you'), 
    path('order-detail/<int:transaction_id>/', views.order_detail, name='order_detail'),
    path('order-detail/<int:transaction_id>/', views.order_detail, name='order_detail'),
    path('our-story/', views.our_story, name='our_story'),
    path('policies/', views.policies, name='policies'),  
    path('send/', views.send_newsletter, name='send_newsletter'),
    path('lookbook/', views.lookbook, name='lookbook'),
    path('subscriber-count/', views.subscriber_count, name='subscriber_count'), path('generate-discount-code/', views.generate_discount_code, name='generate_discount_code'),
    path('validate-discount-code/', views.validate_discount_code, name='validate_discount_code'),
    path('newsletter-signup/', views.newsletter_signup, name='newsletter_signup'),
    
    # Password Reset URLs
    path('password_reset/', views.password_reset_request, name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='GOESApp/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='GOESApp/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='GOESApp/password_reset_complete.html'), name='password_reset_complete'),
]