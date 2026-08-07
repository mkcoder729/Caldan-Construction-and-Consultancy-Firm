"""
Fix Service.icon to always include the Font Awesome 6 style prefix.

Before this migration, services were stored with bare class names like
'fa-drafting-compass' (no `fas`/`far`/`fab` prefix). FA 6 requires the
prefix to match its CSS rules, so the icons rendered as empty squares.

This migration:
1. Updates the field default to the correctly-prefixed 'fas fa-tools'.
2. Back-fills every existing row that doesn't already start with a FA
   style prefix by prepending 'fas '.
"""

from django.db import migrations, models


FA_PREFIXES = ('fas ', 'far ', 'fab ', 'fal ', 'fat ', 'fad ')


def forwards_prefix_icons(apps, schema_editor):
    Service = apps.get_model('services', 'Service')
    for service in Service.objects.all():
        icon = service.icon or ''
        if not any(icon.startswith(p) for p in FA_PREFIXES):
            service.icon = 'fas ' + icon if icon else 'fas fa-tools'
            service.save(update_fields=['icon'])


def backwards_noop(apps, schema_editor):
    # The data fix is one-way; reversing would lose the prefix.
    # Leave a no-op so the migration can be reversed without errors.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0002_alter_service_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='icon',
            field=models.CharField(
                default='fas fa-tools',
                help_text="Full FA6 class, e.g. 'fas fa-tools' (style + icon, both required)",
                max_length=50,
            ),
        ),
        migrations.RunPython(forwards_prefix_icons, backwards_noop),
    ]
