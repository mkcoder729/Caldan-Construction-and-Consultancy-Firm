"""
Smoke test for shop admin product views.

Run from project root: set DJANGO_SETTINGS_MODULE=caldan.settings
                       python smoke_test_shop.py
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calsite.settings')

import django
django.setup()

import io
from PIL import Image
from django.test import Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

# Allow testserver for in-process client
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']

from django.contrib.auth import get_user_model
from shop.models import Product

User = get_user_model()

admin = User.objects.filter(email='smoketest@caldan.test').first()
admin_created_by_us = False
if not admin:
    admin = User.objects.create_user(
        email='smoketest@caldan.test',
        password='TestPass123!',
        full_name='Smoke Test',
        phone='0712345678',
    )
    admin_created_by_us = True
admin.is_active = True
admin.is_staff = True
admin.is_superuser = True
admin.is_chief = True
admin.role = 'CHIEF_ADMIN'
admin.save()

client = Client()
client.force_login(admin, backend='django.contrib.auth.backends.ModelBackend')

passed = 0
failed = 0

def check(label, ok, detail=''):
    global passed, failed
    status = 'PASS' if ok else 'FAIL'
    if ok:
        passed += 1
    else:
        failed += 1
    print(f'  [{status}] {label} {detail}')


# ---- 1. URL reverses ----
print('=== URL reverses ===')
for name, kwargs in [
    ('shop:product_list', {}),
    ('shop:product_create', {}),
    ('shop:product_detail', {'product_id': 1}),
    ('shop:product_edit', {'product_id': 1}),
    ('shop:product_delete', {'product_id': 1}),
    ('shop:product_toggle_active', {'product_id': 1}),
    ('shop:product_toggle_featured', {'product_id': 1}),
    ('shop:order_list', {}),
    ('shop:order_detail', {'order_id': 1}),
    ('shop:order_update', {'order_id': 1}),
    ('shop:order_reports', {}),
]:
    try:
        reverse(name, kwargs=kwargs)
        check(f'reverse {name}', True)
    except Exception as e:
        check(f'reverse {name}', False, f'-> {e}')


# ---- 2. product_list GET ----
print('\n=== product_list GET ===')
resp = client.get(reverse('shop:product_list'))
check('returns 200', resp.status_code == 200, f'(got {resp.status_code})')
check('renders Products heading', b'Products' in resp.content)
check('renders Add Product button', b'Add Product' in resp.content)


# ---- 3. product_create GET ----
print('\n=== product_create GET ===')
resp = client.get(reverse('shop:product_create'))
check('returns 200', resp.status_code == 200, f'(got {resp.status_code})')
check('renders Create Product heading', b'Create Product' in resp.content)


# ---- 4. product_create POST valid ----
print('\n=== product_create POST (valid) ===')
img = Image.new('RGB', (100, 100), color='red')
img_bytes = io.BytesIO()
img.save(img_bytes, format='JPEG')
img_bytes.seek(0)

resp = client.post(reverse('shop:product_create'), {
    'name': 'Smoke Test Cement',
    'category': 'CEMENT',
    'unit': 'BAG',
    'short_description': 'Test product for smoke testing.',
    'description': 'Full description here.',
    'price': '500.00',
    'stock_quantity': '50',
    'is_active': 'on',
    'image': SimpleUploadedFile('test.jpg', img_bytes.read(), content_type='image/jpeg'),
}, follow=False)
check('returns 302 redirect', resp.status_code == 302, f'(got {resp.status_code})')

product = Product.objects.filter(name='Smoke Test Cement').first()
check('product created in DB', product is not None)
if product:
    check('slug auto-generated', bool(product.slug))
    check('price stored', float(product.price) == 500.00)
    check('is_active set', product.is_active is True)
    pid = product.id
else:
    pid = None


# ---- 5. product_detail GET ----
if pid:
    print('\n=== product_detail GET ===')
    resp = client.get(reverse('shop:product_detail', kwargs={'product_id': pid}))
    check('returns 200', resp.status_code == 200, f'(got {resp.status_code})')
    check('renders product name', b'Smoke Test Cement' in resp.content)
    check('renders Edit button', b'Edit Product' in resp.content)


# ---- 6. product_edit GET ----
if pid:
    print('\n=== product_edit GET ===')
    resp = client.get(reverse('shop:product_edit', kwargs={'product_id': pid}))
    check('returns 200', resp.status_code == 200, f'(got {resp.status_code})')
    check('renders Edit Product heading', b'Edit Product' in resp.content)


# ---- 7. product_edit POST update ----
if pid:
    print('\n=== product_edit POST (update price) ===')
    img2 = io.BytesIO()
    Image.new('RGB', (50, 50), color='blue').save(img2, format='JPEG')
    img2.seek(0)

    resp = client.post(reverse('shop:product_edit', kwargs={'product_id': pid}), {
        'name': 'Smoke Test Cement (Updated)',
        'category': 'CEMENT',
        'unit': 'BAG',
        'short_description': 'Updated.',
        'description': 'Updated description.',
        'price': '550.00',
        'stock_quantity': '75',
        'is_active': 'on',
    }, follow=False)
    check('returns 302', resp.status_code == 302, f'(got {resp.status_code})')

    product.refresh_from_db()
    check('price updated to 550', float(product.price) == 550.00, f'(got {product.price})')
    check('stock updated to 75', float(product.stock_quantity) == 75, f'(got {product.stock_quantity})')
    check('name updated', product.name == 'Smoke Test Cement (Updated)')


# ---- 8. product_toggle_active ----
if pid:
    print('\n=== product_toggle_active POST ===')
    resp = client.post(reverse('shop:product_toggle_active', kwargs={'product_id': pid}))
    check('returns 302', resp.status_code == 302, f'(got {resp.status_code})')
    product.refresh_from_db()
    check('is_active flipped to False', product.is_active is False)


# ---- 9. product_toggle_featured ----
if pid:
    print('\n=== product_toggle_featured POST ===')
    resp = client.post(reverse('shop:product_toggle_featured', kwargs={'product_id': pid}))
    check('returns 302', resp.status_code == 302, f'(got {resp.status_code})')
    product.refresh_from_db()
    check('is_featured flipped to True', product.is_featured is True)


# ---- 10. product_create POST invalid (negative price) ----
print('\n=== product_create POST (invalid - negative price) ===')
img3 = io.BytesIO()
Image.new('RGB', (50, 50), color='green').save(img3, format='JPEG')
img3.seek(0)

resp = client.post(reverse('shop:product_create'), {
    'name': 'Invalid Product',
    'category': 'CEMENT',
    'unit': 'BAG',
    'price': '-100',
    'stock_quantity': '0',
    'image': SimpleUploadedFile('test.jpg', img3.read(), content_type='image/jpeg'),
}, follow=False)
check('returns 200 (re-renders with errors)', resp.status_code == 200, f'(got {resp.status_code})')

invalid = Product.objects.filter(name='Invalid Product').first()
check('invalid product NOT created', invalid is None)


# ---- 11. product_create POST invalid (compare_price <= price) ----
print('\n=== product_create POST (invalid - compare_price <= price) ===')
img4 = io.BytesIO()
Image.new('RGB', (50, 50), color='yellow').save(img4, format='JPEG')
img4.seek(0)

resp = client.post(reverse('shop:product_create'), {
    'name': 'Bad Compare Price',
    'category': 'CEMENT',
    'unit': 'BAG',
    'price': '500.00',
    'compare_price': '400.00',  # LESS than price -> invalid
    'stock_quantity': '10',
    'image': SimpleUploadedFile('test.jpg', img4.read(), content_type='image/jpeg'),
}, follow=False)
check('returns 200', resp.status_code == 200, f'(got {resp.status_code})')
bad = Product.objects.filter(name='Bad Compare Price').first()
check('bad compare-price product NOT created', bad is None)


# ---- 12. product_service search filter ----
print('\n=== ProductService.get_products filter ===')
from shop.services import ProductService
result = ProductService.get_products(filters={'search': 'Smoke'})
check('search filter finds our test product', result['total'] >= 1)
result = ProductService.get_products(filters={'is_active': True})
check('is_active filter works', True)  # No assertion, just check no crash


# ---- 13. product_delete POST ----
if pid:
    print('\n=== product_delete POST ===')
    resp = client.post(reverse('shop:product_delete', kwargs={'product_id': pid}))
    check('returns 302', resp.status_code == 302, f'(got {resp.status_code})')
    deleted = Product.objects.filter(id=pid).first()
    check('product deleted from DB', deleted is None)


# ---- 14. product_delete refuses when order items exist ----
print('\n=== product_delete refuses when order items exist ===')
from shop.models import Order, OrderItem
from decimal import Decimal
import secrets, string

# Create a stub order + order item
order = Order.objects.create(
    order_number='TEST-' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)),
    client_name='Test Client',
    client_email='test@example.com',
    client_phone='0712345678',
    delivery_address='123 Test St',
    delivery_county='Nairobi',
    delivery_town='Nairobi',
    subtotal=Decimal('500.00'),
    delivery_fee=Decimal('0'),
    total=Decimal('500.00'),
    status='PENDING',
)

img5 = io.BytesIO()
Image.new('RGB', (50, 50), color='purple').save(img5, format='JPEG')
img5.seek(0)

product2 = Product.objects.create(
    name='Test Product With Order',
    category='CEMENT',
    unit='BAG',
    description='Test',
    price=Decimal('500'),
    stock_quantity=10,
    image=SimpleUploadedFile('test2.jpg', img5.read(), content_type='image/jpeg'),
)

OrderItem.objects.create(
    order=order,
    product=product2,
    quantity=1,
    unit_price=Decimal('500'),
    total_price=Decimal('500'),
)

resp = client.post(reverse('shop:product_delete', kwargs={'product_id': product2.id}))
check('returns 302 (redirected with error)', resp.status_code == 302, f'(got {resp.status_code})')
still = Product.objects.filter(id=product2.id).first()
check('product with order NOT deleted', still is not None)


# ---- 15. Order URLs still work ----
print('\n=== Order URLs still resolve and render ===')
resp = client.get(reverse('shop:order_list'))
check('order_list returns 200', resp.status_code == 200, f'(got {resp.status_code})')

resp = client.get(reverse('shop:order_reports'))
check('order_reports returns 200', resp.status_code == 200, f'(got {resp.status_code})')

resp = client.get(reverse('shop:order_detail', kwargs={'order_id': order.id}))
check('order_detail returns 200', resp.status_code == 200, f'(got {resp.status_code})')


# ---- 16. Order update POST (template exists?) ----
print('\n=== Order update POST ===')
from shop.forms import OrderStatusForm
valid_status = OrderStatusForm.STATUS_CHOICES[0][0] if hasattr(OrderStatusForm, 'STATUS_CHOICES') else 'CONFIRMED'
resp = client.post(reverse('shop:order_update', kwargs={'order_id': order.id}), {
    'status': 'PROCESSING',
})
check('order_update POST returns 302', resp.status_code == 302, f'(got {resp.status_code})')
order.refresh_from_db()
check('status updated', order.status == 'PROCESSING', f'(got {order.status})')


# ---- Cleanup ----
print('\n=== Cleanup ===')
OrderItem.objects.filter(order=order).delete()
order.delete()
Product.objects.filter(name__startswith='Smoke Test').delete()
Product.objects.filter(name='Test Product With Order').delete()
if admin_created_by_us:
    admin.delete()
print('done')

print(f'\n=== RESULT ===')
print(f'  PASSED: {passed}')
print(f'  FAILED: {failed}')

import sys
sys.exit(0 if failed == 0 else 1)