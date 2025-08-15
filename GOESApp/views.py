from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .forms import RegisterForm , CheckoutForm, AddressForm, NewsletterForm
from django.contrib import messages
from .models import Cart, CartItem, Product, Category,Transaction, Newsletter, Color, Size, ProductImage, HomePageImages, CustomUser, OrderItem, DiscountCode
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import uuid
import requests
from django.conf import settings
from django.db.models import Q
from django.core.mail import send_mass_mail
from django.contrib.auth.forms import PasswordResetForm
from django.template.loader import render_to_string
from django.db.models.query_utils import Q
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes

def home(request):
    if request.method == 'POST':
        form = NewsletterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            if not Newsletter.objects.filter(email=email).exists():
                Newsletter.objects.create(email=email)
                messages.success(request, 'Thank you for subscribing!')
                return redirect('home')
            else:
                messages.warning(request, 'This email is already subscribed.')
                return redirect('home')    
    else:
        form = NewsletterForm()
        
    products = Product.objects.filter(is_active=True).order_by('name')  # Fetch all products
    home_images = HomePageImages.objects.all()
    categories = Category.objects.all()
    context = {
        'products': products,
        'categories': categories,
        'form': form,
        'home_images':home_images,
    }
    return render(request, 'GOESApp/index.html', context)

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import time
import requests

def send_newsletter(request):
    if request.method == 'POST':
        subject = request.POST.get('subject')
        text_content = request.POST.get('message')
        html_content = f'''
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                    h2 {{ color: #000; border-bottom: 1px solid #ddd; padding-bottom: 10px; }}
                    .footer {{ margin-top: 30px; font-size: 12px; color: #777; text-align: center; }}
                    .logo {{ text-align: center; margin-bottom: 20px; }}
                    .button {{ display: inline-block; background-color: #000; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
                    .button:hover {{ background-color: #333; }}
                </style>
            </head>
            <body>
                <div class="logo">
                    <h1>GOES - God On Every Side</h1>
                </div>
                <h2>{subject}</h2>
                <div class="content">
                    {text_content}
                </div>
                <div class="footer">
                    <p>© {time.strftime('%Y')} GOES Clothing. All rights reserved.</p>
                    <p>You received this email because you subscribed to our newsletter.</p>
                    <p>If you wish to unsubscribe, please <a href="#">click here</a>.</p>
                </div>
            </body>
        </html>
        '''
        subscribers = Newsletter.objects.values_list('email', flat=True)

        if not subscribers:
            messages.error(request, 'No subscribers found.')
            return redirect('send_newsletter')

        try:
            # Send emails in batches to avoid rate limiting
            batch_size = 50
            total_sent = 0
            failed_emails = []
            
            for i in range(0, len(subscribers), batch_size):
                batch = subscribers[i:i+batch_size]
                
                for subscriber in batch:
                    try:
                        email = EmailMultiAlternatives(
                            subject=subject,
                            body=text_content,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=[subscriber]
                        )
                        email.attach_alternative(html_content, "text/html")
                        email.send()
                        total_sent += 1
                    except Exception as e:
                        failed_emails.append(subscriber)
                        print(f"Failed to send to {subscriber}: {str(e)}")
                        
                # Add a small delay between batches to avoid rate limiting
                if i + batch_size < len(subscribers):
                    time.sleep(1)
            
            if failed_emails:
                messages.warning(request, f'Newsletter sent to {total_sent} subscribers. Failed to send to {len(failed_emails)} subscribers.')
            else:
                messages.success(request, f'Newsletter sent successfully to all {total_sent} subscribers!')
                
        except Exception as e:
            messages.error(request, f'Failed to send newsletter: {str(e)}')

        return redirect('send_newsletter')
    return render(request, 'GOESApp/send_newsletter.html')


from django.http import JsonResponse

def subscriber_count(request):
    """Return the count of newsletter subscribers as JSON"""
    count = Newsletter.objects.count()
    return JsonResponse({'count': count})

def shop(request):
    category_id = request.GET.get('category')
    search_query = request.GET.get('search', '').strip()
    
    # Base query for active products
    products = Product.objects.filter(is_active=True)
    
    # Apply category filter
    if category_id and category_id != 'all':
        products = products.filter(category_id=category_id)
    
    # Apply search filter
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Order products
    products = products.order_by('name')
    
    # Get all categories
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
        'cart_count': cart_item_count(request)['cart_count'],
    }
    return render(request, 'GOESApp/shop.html', context)

@login_required(login_url='/login_user')
def checkout(request):
    categories = Category.objects.all()
    cart = None
    cart_items = []
    total_price = 0
    shipping_fee = 2000  # Default shipping fee for Abuja
    subtotal = 0
    address = None
    has_address = False
    discount_code = None
    discount_amount = 0
    applied_discount = False

    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.all()
        subtotal = sum(item.total_price() for item in cart_items)
        address = request.user.address if hasattr(request.user, 'address') and request.user.address else None
        has_address = address is not None and all([
            address.street,
            address.city,
            address.state,
            address.postal_code,
            address.country,
            address.phone_number
        ])
        
        # Calculate shipping fee based on address
        if has_address:
            country = address.country.lower() if address.country else ''
            state = address.state.lower() if address.state else ''
            if country == 'nigeria':
                if state in ['abuja', 'federal capital territory', 'fct']:
                    shipping_fee = 2000  # Abuja/FCT shipping fee
                else:
                    shipping_fee = 5000  # Other Nigerian states
                total_price = subtotal + shipping_fee
            else:
                shipping_fee = 15000  # International shipping fee
                total_price = subtotal + shipping_fee
        
    except Cart.DoesNotExist:
        messages.error(request, "Your cart is empty.")
        return redirect('cart')

    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect('cart')

    if request.method == 'POST':
        if 'proceed_to_pay' in request.POST:
            form = CheckoutForm(request.POST, instance=address)
            if not has_address and not form.is_valid():
                messages.error(request, "Please save a valid delivery address before proceeding to payment.")
                return redirect('checkout')
            
            if form.is_valid():
                # Apply discount if valid
                discount_code = form.cleaned_data.get('discount_code')
                if discount_code and subtotal >= 200000:
                    try:
                        discount = DiscountCode.objects.get(code=discount_code, is_used=False, expires_at__gt=timezone.now())
                        discount_amount = subtotal * (discount.discount_percentage / 100)
                        total_price = subtotal - discount_amount + shipping_fee
                        applied_discount = True
                    except DiscountCode.DoesNotExist:
                        messages.error(request, "Invalid or expired discount code.")
                        return redirect('checkout')
                
                # Save address if provided
                address = form.save()
                if not request.user.address:
                    request.user.address = address
                    request.user.save()
                
                # Recalculate shipping fee based on new address
                country = form.cleaned_data.get('country', '').lower()
                state = form.cleaned_data.get('state', '').lower()
                if country == 'nigeria':
                    if state in ['abuja', 'federal capital territory', 'fct']:
                        shipping_fee = 2000
                    else:
                        shipping_fee = 5000
                else:
                    shipping_fee = 15000
                total_price = (subtotal - discount_amount) + shipping_fee
                
                # Create transaction
                tx_ref = f"txn-{uuid.uuid4().hex[:10]}"
                order_note = request.POST.get('order_note', '')
                transaction = Transaction.objects.create(
                    user=request.user,
                    amount=total_price,
                    tx_ref=tx_ref,
                    address=address,
                    order_note=order_note,
                    transaction_status='pending'
                )
                # Add products to the transaction
                transaction.products.set([item.product for item in cart_items])
                # Store discount code if applied
                if discount_code and applied_discount:
                    transaction.discount_code = DiscountCode.objects.get(code=discount_code)
                    transaction.discount_code.is_used = True
                    transaction.discount_code.save()
                transaction.save()
                return redirect('initiate_payment', transaction_id=transaction.id)
            else:
                messages.error(request, "Please correct the errors in the form.")
        else:
            # Handle address form submission
            form = CheckoutForm(request.POST, instance=address)
            if form.is_valid():
                address = form.save()
                if not request.user.address:
                    request.user.address = address
                    request.user.save()
                
                # Recalculate shipping fee based on new address
                country = form.cleaned_data.get('country', '').lower()
                state = form.cleaned_data.get('state', '').lower()
                if country == 'nigeria':
                    if state in ['abuja', 'federal capital territory', 'fct']:
                        shipping_fee = 2000
                    else:
                        shipping_fee = 5000
                else:
                    shipping_fee = 15000
                
                total_price = subtotal + shipping_fee
                
                messages.success(request, "Delivery address updated successfully.")
                return redirect('checkout')
            else:
                messages.error(request, "Please correct the errors in the form.")
    else:
        form = CheckoutForm(instance=address)

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'total_price': total_price,
        'form': form,
        'categories': categories,
        'has_address': has_address,
        'discount_amount': discount_amount,
        'applied_discount': applied_discount,
    }
    return render(request, 'GOESApp/checkout.html', context)

@login_required(login_url='/login_user')
def initiate_payment(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()

    context = {
        'transaction': transaction,
        'cart_items': cart_items,
        'public_key': settings.FLUTTERWAVE_PUBLIC_KEY,
        'redirect_url': 'https://www.godoneveryside.com/payment-callback',
        'customer': {
            'name': f"{request.user.first_name} {request.user.last_name}",
            'email': request.user.email,
        },
    }
    return render(request, 'GOESApp/initiate_payment.html', context)

import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# views.py
@csrf_exempt
@csrf_exempt
@require_http_methods(["GET", "POST"])
def payment_callback(request):
    if request.method == "POST":
        try:
            webhook_data = json.loads(request.body.decode('utf-8'))
            event_type = webhook_data.get('event')
            transaction_data = webhook_data.get('data', {})
            tx_ref = transaction_data.get('tx_ref')
            transaction_id = transaction_data.get('id')
            status = transaction_data.get('status')

            try:
                transaction = Transaction.objects.get(tx_ref=tx_ref)
            except Transaction.DoesNotExist:
                return HttpResponse(status=404)

            if event_type == 'charge.completed' and status in ['successful', 'completed']:
                verification_response = verify_transaction(transaction_id)
                if (verification_response['status'] == 'success' and 
                    verification_response['data']['status'] in ['successful', 'completed'] and
                    verification_response['data']['amount'] == float(transaction.amount) and
                    verification_response['data']['currency'] == 'NGN'):
                    transaction.flw_transaction_id = transaction_id
                    transaction.transaction_status = 'approved'
                    transaction.save()
                    cart, created = Cart.objects.get_or_create(user=transaction.user)
                    cart_items = cart.items.all()
                    
                    # Create OrderItem objects for each CartItem
                    for cart_item in cart_items:
                        product = cart_item.product
                        if product.in_stock >= cart_item.quantity:
                            product.in_stock -= cart_item.quantity
                            product.save()
                            # Create an OrderItem for this cart item
                            OrderItem.objects.create(
                                transaction=transaction,
                                product=product,
                                quantity=cart_item.quantity,
                                size=cart_item.size,
                                color=cart_item.color,
                                price=product.price  # Store the price at the time of purchase
                            )
                        else:
                            transaction.transaction_status = 'declined'
                            transaction.save()
                            return HttpResponse(status=400)
                    cart_items.delete()
                    
                    # Send order confirmation email with request
                    send_order_confirmation_email(request, transaction)
                    
            elif status == 'failed':
                transaction.transaction_status = 'declined'
                transaction.save()
            return HttpResponse(status=200)
        except Exception as e:
            print(f"Webhook error: {str(e)}")
            return HttpResponse(status=400)

    elif request.method == "GET":
        status = request.GET.get('status')
        tx_ref = request.GET.get('tx_ref')
        transaction_id = request.GET.get('transaction_id')

        if status in ['successful', 'completed']:
            try:
                transaction = Transaction.objects.get(tx_ref=tx_ref)
                verification_response = verify_transaction(transaction_id)
                if (verification_response['status'] == 'success' and 
                    verification_response['data']['status'] in ['successful', 'completed'] and
                    verification_response['data']['amount'] == float(transaction.amount) and
                    verification_response['data']['currency'] == 'NGN'):
                    transaction.flw_transaction_id = transaction_id
                    transaction.transaction_status = 'processing'
                    transaction.save()
                    cart, created = Cart.objects.get_or_create(user=transaction.user)
                    cart_items = cart.items.all()
                    
                    # Create OrderItem objects for each CartItem
                    for cart_item in cart_items:
                        product = cart_item.product
                        if product.in_stock >= cart_item.quantity:
                            product.in_stock -= cart_item.quantity
                            product.save()
                            # Create an OrderItem for this cart item
                            OrderItem.objects.create(
                                transaction=transaction,
                                product=product,
                                quantity=cart_item.quantity,
                                size=cart_item.size,
                                color=cart_item.color,
                                price=product.price  # Store the price at the time of purchase
                            )
                        else:
                            transaction.transaction_status = 'declined'
                            transaction.save()
                            messages.error(request, f"Insufficient stock for {product.name}.")
                            return redirect('cart')
                    cart_items.delete()
                    # Update transaction status to approved
                    transaction.transaction_status = 'approved'
                    transaction.save()
                    
                    # Send order confirmation email with request
                    send_order_confirmation_email(request, transaction)
                    
                    messages.success(request, "Payment successful! Your order is being processed. A confirmation email has been sent to your email address.")
                    return redirect('thank_you', transaction_id=transaction.id)  # Redirect to thank_you page
                else:
                    print(f"Verification failed: {verification_response}")
                    transaction.transaction_status = 'declined'
                    transaction.save()
                    messages.error(request, "Payment verification failed.")
            except Transaction.DoesNotExist:
                messages.error(request, "Transaction not found.")
        elif status == 'cancelled':
            try:
                transaction = Transaction.objects.get(tx_ref=tx_ref)
                transaction.transaction_status = 'declined'
                transaction.save()
                messages.error(request, "Payment was cancelled.")
            except Transaction.DoesNotExist:
                messages.error(request, "Transaction not found.")
        else:
            messages.error(request, f"Payment failed with status: {status}. Please try again.")

        return redirect('cart')
    
def send_order_confirmation_email(request, transaction):
    subject = f'GOES Clothing - Order Confirmation'
    order_items = transaction.order_items.all()
    address = transaction.address
    address_text = f"{address.street}, {address.city}, {address.state}, {address.postal_code}, {address.country}"
    
    # Calculate subtotal
    subtotal = sum(item.total_price() for item in order_items)
    # Calculate shipping fee
    shipping_fee = 2000
    if address:
        country = address.country.lower() if address.country else ''
        state = address.state.lower() if address.state else ''
        if country == 'nigeria':
            if state in ['abuja', 'federal capital territory', 'fct']:
                shipping_fee = 2000
            else:
                shipping_fee = 5000
        else:
            shipping_fee = 15000
    
    # Calculate discount if applied
    discount_amount = 0
    discount_code_text = ''
    if transaction.discount_code:
        discount_amount = subtotal * (transaction.discount_code.discount_percentage / 100)
        discount_code_text = f"Discount Code Applied ({transaction.discount_code.code}): -₦{discount_amount}\n"

    text_content = f"""Dear {transaction.user.first_name} {transaction.user.last_name},

Thank you for your purchase from GOES Clothing!

Order Details:
Order Confirmation 
Date: {transaction.transaction_date.strftime('%Y-%m-%d %H:%M')}
Subtotal: ₦{subtotal}
{discount_code_text}Shipping Fee: ₦{shipping_fee}
Total Amount: ₦{transaction.amount}

Products:
{''.join([f"- {item.product.name} (Qty: {item.quantity}) - ₦{item.price}" for item in order_items])}

Shipping Address:
{address_text}

{'Order Note: ' + transaction.order_note if transaction.order_note else ''}

Your order is being processed and will be shipped soon.

Thank you for shopping with us!

GOES Clothing Team
God On Every Side
"""
    
    style_content = '''
<html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
            h2 { color: #000; border-bottom: 1px solid #ddd; padding-bottom: 10px; }
            .order-details { background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0; }
            .product-item { margin-bottom: 15px; display: flex; align-items: center; }
            .product-image { width: 80px; height: 80px; margin-right: 15px; object-fit: cover; border-radius: 5px; }
            .product-info { flex: 1; }
            .footer { margin-top: 30px; font-size: 12px; color: #777; text-align: center; }
            .logo { text-align: center; margin-bottom: 20px; }
            .logo img { max-width: 150px; height: auto; }
            .button { display: inline-block; background-color: #000; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
            .button:hover { background-color: #333; }
            .total-amount { font-size: 18px; font-weight: bold; color: #000; background-color: #f0f0f0; padding: 10px; border-radius: 5px; text-align: center; margin: 15px 0; }
            .quantity { display: inline-block; background-color: #000; color: white; padding: 3px 8px; border-radius: 3px; margin-left: 5px; }
        </style>
    </head>
    <body>
        <div class="logo">
            <img src="https://www.godoneveryside.com/static/images/LOGO_20_TRANS[1].png" alt="GOES Clothing Logo">
            <h1>GOES - God On Every Side</h1>
        </div>
'''
    
    product_items = []
    for item in order_items:
        product_image = ProductImage.objects.filter(product=item.product).first()
        image_url = ''
        if product_image and product_image.image:
            image_url = product_image.image.url
            if not image_url.startswith('http'):
                image_url = request.build_absolute_uri(image_url)
        
        size_text = f"Size: {item.size.name} | " if item.size else ""
        color_text = f"Color: {item.color.name} | " if item.color else ""
        
        product_items.append(f"""
        <div class="product-item">
            <img src="{image_url}" alt="{item.product.name}" class="product-image">
            <div class="product-info">
                <strong>{item.product.name}</strong> <span class="quantity">Qty: {item.quantity}</span><br>
                {size_text}{color_text}₦{item.price}
            </div>
        </div>""")
    
    product_list_html = '\n'.join(product_items)
    order_note_html = f'<h3>Order Note:</h3><p>{transaction.order_note}</p>' if transaction.order_note else ''
    discount_html = f'<p><strong>Discount ({transaction.discount_code.code}):</strong> -₦{discount_amount}</p>' if transaction.discount_code else ''
    
    dynamic_content = (
        f"<h2>Order Confirmation</h2>\n"
        f"<p>Dear {transaction.user.first_name} {transaction.user.last_name},</p>\n"
        f"<p>Thank you for your purchase from GOES Clothing!</p>\n\n"
        
        f"<div class=\"order-details\">\n"
        f"<h3>Order Details:</h3>\n"
        f"<p><strong>Order Confirmation</strong> </p>\n"
        f"<p><strong>Date:</strong> {transaction.transaction_date.strftime('%Y-%m-%d %H:%M')}</p>\n"
        f"<p><strong>Subtotal:</strong> ₦{subtotal}</p>\n"
        f"{discount_html}\n"
        f"<p><strong>Shipping Fee:</strong> ₦{shipping_fee}</p>\n"
        f"<div class=\"total-amount\">Total Amount: ₦{transaction.amount}</div>\n\n"
        
        f"<h3>Products:</h3>\n"
        f"{product_list_html}\n\n"
        
        f"<h3>Shipping Address:</h3>\n"
        f"<p>{address_text}</p>\n\n"
        
        f"{order_note_html}\n"
        f"</div>\n\n"
        
        f"<p>Your order is being processed and will be shipped soon.</p>\n"
        f"<p>Thank you for shopping with us!</p>\n\n"
        
        f"<div class=\"footer\">\n"
        f"<p><strong>GOES Clothing Team</strong></p>\n"
        f"<p>God On Every Side</p>\n"
        f"<p>© {time.strftime('%Y')} GOES Clothing. All rights reserved.</p>\n"
        f"</div>\n"
        f"</body>\n"
        "</html>"
    )
    
    html_content = style_content + dynamic_content
    
    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[transaction.user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        return True
    except Exception as e:
        print(f"Failed to send order confirmation email: {str(e)}")
        return False
                
def thank_you(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    categories = Category.objects.all()
    cart_count = 0
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.items.count()

    context = {
        'transaction': transaction,
        'categories': categories,
        'cart_count': cart_count,
    }
    return render(request, 'GOESApp/thank_you.html', context)

def verify_transaction(transaction_id):
    url = f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify"
    headers = {
        'Authorization': f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
        'Content-Type': 'application/json',
    }
    response = requests.get(url, headers=headers)
    return response.json()


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    
    # Check if product is active and in stock
    if not product.is_active:
        messages.error(request, f"{product.name} is currently not available.")
        return redirect('product_detail', product_id=product.id)
    
    if product.in_stock <= 0:
        messages.error(request, f"{product.name} is out of stock.")
        return redirect('product_detail', product_id=product.id)

    quantity = int(request.POST.get('quantity', 1))
    
    # Check if requested quantity is available
    if quantity > product.in_stock:
        messages.error(request, f"Only {product.in_stock} units of {product.name} are available.")
        return redirect('product_detail', product_id=product.id)
        
    size_name = request.POST.get('size')
    color_name = request.POST.get('color')

    # If user is authenticated, fetch or create cart
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key, user=None)

    # Get size and color objects if provided
    size = None
    color = None
    if size_name:
        size = get_object_or_404(Size, name=size_name)
        if size not in product.sizes.all():
            messages.error(request, f"Selected size {size_name} is not available for {product.name}.")
            return redirect('product_detail', product_id=product.id)
    if color_name:
        color = get_object_or_404(Color, name=color_name)
        if color not in product.colors.all():
            messages.error(request, f"Selected color {color_name} is not available for {product.name}.")
            return redirect('product_detail', product_id=product.id)

    # Add or update cart item
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        size=size,
        color=color
    )
    
    # Check if the updated quantity would exceed available stock
    new_quantity = cart_item.quantity + quantity if not created else quantity
    if new_quantity > product.in_stock:
        messages.error(request, f"Cannot add {quantity} more units. Only {product.in_stock} units of {product.name} are available.")
        return redirect('product_detail', product_id=product.id)
        
    if not created:
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity
    cart_item.save()

    messages.success(request, f"{product.name} ({size_name or 'No size'}, {color_name or 'No color'}) added to cart!")
    return redirect('product_detail', product_id=product.id)

def cart_item_count(request):
    count = 0
    try:
        if request.user.is_authenticated:
            cart = Cart.objects.get(user=request.user)
        else:
            session_key = request.session.session_key
            if session_key:
                cart = Cart.objects.get(session_key=session_key)
            else:
                cart = None
        if cart:
            count = sum(item.quantity for item in cart.items.all())
    except Cart.DoesNotExist:
        pass
    return {'cart_count': count}

@require_POST
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart_item.delete()
    messages.success(request, f"{cart_item.product.name} removed from cart!")
    return redirect('cart')

@login_required(login_url='/login_user')
def order_detail(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    categories = Category.objects.all()
    cart_count = 0
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.items.count()

    # Get order items
    order_items = transaction.order_items.all()
    
    # Calculate shipping fee based on address
    shipping_fee = 2000  # Default shipping fee for Abuja
    address = transaction.address
    if address:
        country = address.country.lower() if address.country else ''
        state = address.state.lower() if address.state else ''
        if country == 'nigeria':
            if state in ['abuja', 'federal capital territory', 'fct']:
                shipping_fee = 2000  # Abuja/FCT shipping fee
            else:
                shipping_fee = 5000  # Other Nigerian states
        else:
            shipping_fee = 15000  # International shipping fee
    
    # Calculate subtotal
    subtotal = sum(item.total_price() for item in order_items)
    
    # Create product list with details
    products_with_details = []
    for item in order_items:
        product_image = ProductImage.objects.filter(product=item.product).first()
        image_url = request.build_absolute_uri(product_image.image.url) if product_image and product_image.image else ''
        products_with_details.append({
            'product': item.product,
            'quantity': item.quantity,
            'image_url': image_url,
            'size': item.size.name if item.size else '',
            'color': item.color.name if item.color else '',
            'price': item.price,  # Use the price stored in OrderItem
        })

    context = {
        'transaction': transaction,
        'categories': categories,
        'cart_count': cart_count,
        'products_with_details': products_with_details,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'total_amount': transaction.amount,  # Already includes shipping
    }
    return render(request, 'GOESApp/order_detail.html', context)

@login_required(login_url='/login_user')
def profile(request):
    user = request.user
    address = user.address if hasattr(user, 'address') else None
    categories = Category.objects.all()
    cart_count = 0
    if user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=user)
        cart_count = cart.items.count()

    # Fetch transactions
    transactions = Transaction.objects.filter(user=user).order_by('-transaction_date')
    
    # Categorize transactions
    current_orders = transactions.filter(transaction_status__in=['pending', 'processing', 'approved'])
    past_orders = transactions.filter(transaction_status='declined')  # Add 'delivered' status in the future

    context = {
        'user': user,
        'address': address,
        'categories': categories,
        'cart_count': cart_count,
        'current_orders': current_orders,
        'past_orders': past_orders,
    }
    return render(request, 'GOESApp/profile.html', context)


@login_required(login_url='/login_user')
def edit_address(request):
    categories = Category.objects.all()
    user = request.user
    address = user.address if hasattr(user, 'address') and user.address else None

    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            address = form.save()
            if not user.address:
                user.address = address
                user.save()
            messages.success(request, "Address updated successfully.")
            return redirect('profile')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = AddressForm(instance=address)

    context = {
        'form': form,
        'is_edit': address,
        'categories': categories,
    }
    return render(request, 'GOESApp/edit_address.html', context)

def cart(request):
    categories = Category.objects.all()
    cart = None
    cart_items = []
    total_price = 0
    shipping_fee = 2000  # Default shipping fee for Abuja in NGN
    subtotal = 0

    try:
        if request.user.is_authenticated:
            cart = Cart.objects.get(user=request.user)
            # Get user's address if available to calculate shipping
            address = None
            if hasattr(request.user, 'address') and request.user.address:
                address = request.user.address
                # Calculate shipping fee based on location
                country = address.country.lower() if address.country else ''
                state = address.state.lower() if address.state else ''
                
                if country == 'nigeria':
                    if state == 'abuja' or state == 'federal capital territory' or state == 'fct':
                        shipping_fee = 2000  # Abuja/FCT shipping fee
                    else:
                        shipping_fee = 5000  # Other Nigerian states shipping fee
                else:
                    shipping_fee = 15000  # International shipping fee
        else:
            session_key = request.session.session_key
            if session_key:
                cart = Cart.objects.get(session_key=session_key)

        if cart:
            cart_items = cart.items.all()
            subtotal = sum(item.total_price() for item in cart_items)
            total_price = subtotal + shipping_fee

    except Cart.DoesNotExist:
        pass

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'total_price': total_price,
        'categories': categories,
    }
    return render(request, 'GOESApp/cart.html', context)


def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    else:
        if request.method == 'POST':
            form = RegisterForm(request.POST)
            if form.is_valid():
                user = form.save(commit=False)
                user.save()  # Save the user before authenticating
                login(request, user)
                messages.success(request, f'Welcome, {user.username}! Your account has been created.')
                return redirect('home')
            else:
                messages.error(request, 'Error creating account. Please check the form.')
        else:
            form = RegisterForm()
    return render(request, 'GOESApp/register.html', {'form': form})

def login_user(request):
    if request.user.is_authenticated:
        return redirect('home')
    else:
        error_message = None
        if request.method == 'POST':
            email = request.POST['email']
            password = request.POST['password']
            user = authenticate(request, email=email, password=password)

            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, 'Invalid email or password.')
        return render(request, 'GOESApp/login.html', {'error_message': error_message})


def password_reset_request(request):
    categories = Category.objects.all()
    if request.method == "POST":
        password_reset_form = PasswordResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data['email']
            associated_users = CustomUser.objects.filter(Q(email=data))
            if associated_users.exists():
                for user in associated_users:
                    subject = "Password Reset Requested"
                    email_template_name = "GOESApp/password_reset_email.html"
                    c = {
                        "email": user.email,
                        'domain': request.META['HTTP_HOST'],
                        'site_name': 'GOES Clothing',
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "user": user,
                        'token': default_token_generator.make_token(user),
                        'protocol': 'https' if request.is_secure() else 'http',
                    }
                    email = render_to_string(email_template_name, c)
                    try:
                        from django.core.mail import EmailMessage
                        email_message = EmailMessage(
                            subject, email, settings.DEFAULT_FROM_EMAIL, [user.email]
                        )
                        email_message.content_subtype = 'html'
                        email_message.send()
                    except Exception as e:
                        return render(request, "GOESApp/password_reset_form.html", {
                            "form": password_reset_form,
                            "error": f"There was an error sending an email: {e}",
                            "categories": categories,
                        })
                    return redirect("password_reset_done")
            else:
                messages.error(request, "No user is associated with this email address.")
                return render(request, "GOESApp/password_reset_form.html", {
                    "form": password_reset_form,
                    "categories": categories,
                })
    password_reset_form = PasswordResetForm()
    return render(request=request, template_name="GOESApp/password_reset_form.html", context={"form": password_reset_form, "categories": categories})


def logout_user(request):
    logout(request)
    return redirect('home')

def product_detail(request, product_id):
    categories = Category.objects.all()
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    # Fetch related products in the same category (exclude current)
    category = product.category
    related_products = Product.objects.filter(
        category=category, is_active=True
    ).exclude(pk=product.pk)[:4]
    # Get available sizes and colors
    available_sizes = product.sizes.all()
    available_colors = product.colors.all()
    context = {
        'product': product,
        'related_products': related_products,
        'categories': categories,
        'available_sizes': available_sizes,
        'available_colors': available_colors,
    }
    return render(request, 'GOESApp/product_detail.html', context)

# views.py
def our_story(request):
    categories = Category.objects.all()
    cart_count = 0
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.items.count()

    context = {
        'categories': categories,
        'cart_count': cart_count,
    }
    return render(request, 'GOESApp/our_story.html', context)

# views.py
def policies(request):
    categories = Category.objects.all()
    cart_count = 0
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.items.count()

    context = {
        'categories': categories,
        'cart_count': cart_count,
    }
    return render(request, 'GOESApp/policies.html', context)

import uuid
from django.utils import timezone
from datetime import timedelta

@require_POST
def generate_discount_code(request):
    email = request.POST.get('email')
    if not email:
        return JsonResponse({'success': False, 'error': 'Email is required.'})

    # Check if email is already subscribed
    newsletter, created = Newsletter.objects.get_or_create(email=email)
    
    # Check if a valid discount code already exists for this email
    existing_code = DiscountCode.objects.filter(email=newsletter, is_used=False, expires_at__gt=timezone.now()).first()
    if existing_code:
        return JsonResponse({'success': True, 'code': existing_code.code})

    # Generate a unique discount code
    code = f"GOES5-{uuid.uuid4().hex[:8]}".upper()
    expires_at = timezone.now() + timedelta(days=30)  # Code valid for 30 days

    # Create new discount code
    discount_code = DiscountCode.objects.create(
        email=newsletter,
        code=code,
        discount_percentage=5.00,
        expires_at=expires_at
    )

    return JsonResponse({'success': True, 'code': discount_code.code})

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import DiscountCode
from django.utils import timezone

@require_POST
def validate_discount_code(request):
    code = request.POST.get('discount_code')
    subtotal = float(request.POST.get('subtotal', 0))
    if not code or subtotal < 200000:
        return JsonResponse({'success': False, 'error': 'Invalid code or subtotal less than ₦200,000.'})
    
    try:
        discount = DiscountCode.objects.get(code=code, is_used=False, expires_at__gt=timezone.now())
        discount_amount = subtotal * (float(discount.discount_percentage) / 100)  # Convert Decimal to float
        return JsonResponse({
            'success': True,
            'discount_amount': discount_amount,
            'total_price': subtotal - discount_amount  # Note: Shipping fee added server-side
        })
    except DiscountCode.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid or expired discount code.'})

# views.py
def lookbook(request):
    categories = Category.objects.all()
    cart_count = 0
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.items.count()

    context = {
        'categories': categories,
        'cart_count': cart_count,
    }
    return render(request, 'GOESApp/lookbook.html', context)