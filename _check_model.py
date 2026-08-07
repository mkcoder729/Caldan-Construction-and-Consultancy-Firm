import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calsite.settings")
django.setup()

from shop.models import Product

print("ShopSection values:", [c[0] for c in Product.ShopSection.choices])
print("Category values:", len(Product.Category.choices), "total")
print("Construction categories:",
      [c[0] for c in Product.Category.choices if Product.CATEGORY_TO_SECTION.get(c[0]) == Product.ShopSection.CONSTRUCTION])
print("General Store categories:",
      [c[0] for c in Product.Category.choices if Product.CATEGORY_TO_SECTION.get(c[0]) == Product.ShopSection.GENERAL_STORE])

# Check field shows up
fields = [f.name for f in Product._meta.get_fields()]
assert "shop_section" in fields, "shop_section field missing"
print("shop_section field: OK")
print("indexes:", [i.fields for i in Product._meta.indexes])