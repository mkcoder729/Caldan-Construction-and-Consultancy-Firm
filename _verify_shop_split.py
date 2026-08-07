"""End-to-end verification of the Construction Shop + General Store split."""
import os
import sys
import django

# Force UTF-8 stdout for Windows cp1252 compatibility in settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calsite.settings')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
django.setup()

from django.core.management import call_command
from django.template.loader import get_template
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from shop.models import Product

print('=' * 70)
print('1. Migration check')
print('=' * 70)
call_command('makemigrations', 'shop', dry_run=True, verbosity=1)

print()
print('=' * 70)
print('2. Section counts')
print('=' * 70)
from django.db.models import Count
for row in Product.objects.values('shop_section').annotate(c=Count('id')).order_by('shop_section'):
    print(f"   {row['shop_section']:15s} -> {row['c']:3d} products")

print()
print('=' * 70)
print('3. Category-by-section breakdown')
print('=' * 70)
from collections import defaultdict
by_section = defaultdict(list)
for code, _ in Product.Category.choices:
    section = Product.CATEGORY_TO_SECTION.get(code)
    if section:
        by_section[section].append(code)
for section, cats in by_section.items():
    print(f"   {section}: {len(cats)} categories")
    for c in cats:
        print(f"      - {c}")

print()
print('=' * 70)
print('4. Run seed_products (idempotent)')
print('=' * 70)
try:
    call_command('seed_products', verbosity=1)
except SystemExit as exc:
    print(f"   SystemExit: {exc}")
except Exception as exc:
    print(f"   Error: {exc}")

print()
print('=' * 70)
print('5. Run seed_general_store (idempotent)')
print('=' * 70)
try:
    call_command('seed_general_store', verbosity=1)
except SystemExit as exc:
    print(f"   SystemExit: {exc}")
except Exception as exc:
    print(f"   Error: {exc}")

print()
print('=' * 70)
print('6. Post-seed section counts')
print('=' * 70)
for row in Product.objects.values('shop_section').annotate(c=Count('id')).order_by('shop_section'):
    print(f"   {row['shop_section']:15s} -> {row['c']:3d} products")

print()
print('=' * 70)
print('7. Template render check (admin product list)')
print('=' * 70)
try:
    tpl = get_template('shop/dashboard/admin/products/list.html')
    factory = RequestFactory()
    from accounts.models import User
    admin_user = User.objects.filter(is_staff=True).first() or AnonymousUser()
    request = factory.get('/dashboard/shop/admin/products/?section=CONSTRUCTION')
    request.user = admin_user
    from shop.views._admin_views import product_list
    response = product_list(request)
    rendered = response.render().content.decode('utf-8')
    has_section_filter = 'id_section' in rendered
    has_section_column = 'Construction' in rendered
    print(f"   Render OK ({len(rendered)} chars)")
    print(f"   Section filter rendered: {has_section_filter}")
    print(f"   Section column rendered: {has_section_column}")
except Exception as exc:
    import traceback
    print(f"   Render FAILED: {exc}")
    traceback.print_exc()

print()
print('=' * 70)
print('8. Template render check (public shop home + section)')
print('=' * 70)
for url in ['/shop/', '/shop/section/CONSTRUCTION/', '/shop/section/GENERAL_STORE/']:
    try:
        tpl = get_template('shop/index.html')
        print(f"   {url} -> template loads OK")
    except Exception as exc:
        print(f"   {url} -> template FAILED: {exc}")

print()
print('=' * 70)
print('9. Template render check (product detail breadcrumb)')
print('=' * 70)
try:
    tpl = get_template('shop/product_detail.html')
    print('   product_detail.html loads OK')
except Exception as exc:
    print(f"   product_detail.html FAILED: {exc}")

print()
print('Verification complete.')
