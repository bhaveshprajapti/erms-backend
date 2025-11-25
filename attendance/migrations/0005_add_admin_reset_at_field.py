# Generated manually for admin reset tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0004_add_session_log_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='admin_reset_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]