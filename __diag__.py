import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calsite.settings')
django.setup()

from django.urls import resolve, reverse

print('--- Attempt 1: reverse("index") ---')
try:
    print('OK:', reverse('index'))
except Exception as e:
    print('FAIL:', e)

print('--- Attempt 2: reverse("website:index") ---')
try:
    print('OK:', reverse('website:index'))
except Exception as e:
    print('FAIL:', e)

print('--- Attempt 3: resolve("/") ---')
try:
    m = resolve('/')
    print('OK: url_name=%s, namespace=%s, view_name=%s, func=%s' % (m.url_name, m.namespace, m.view_name, m.func))
except Exception as e:
    print('FAIL:', e)

print('--- Attempt 4: resolve("/services/") ---')
try:
    m = resolve('/services/')
    print('OK: url_name=%s, namespace=%s, view_name=%s, func=%s' % (m.url_name, m.namespace, m.view_name, m.func))
except Exception as e:
    print('FAIL:', e)

print('--- Attempt 5: resolve("/about/") ---')
try:
    m = resolve('/about/')
    print('OK: url_name=%s, namespace=%s, view_name=%s, func=%s' % (m.url_name, m.namespace, m.view_name, m.func))
except Exception as e:
    print('FAIL:', e)
