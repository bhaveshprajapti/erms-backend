# Generated migration to add default value to total_days field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leave', '0003_flexibletimingtype_flexibletimingpolicy_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='leaveapplication',
            name='total_days',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
    ]
