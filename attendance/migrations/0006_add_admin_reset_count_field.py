# Generated manually for admin reset count tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0005_add_admin_reset_at_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='admin_reset_count',
            field=models.PositiveIntegerField(default=0),
        ),
    ]