# Generated migration for adding folder_path field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='folder_path',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
    ]
