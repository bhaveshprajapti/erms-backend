# Generated migration for plain_password field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='plain_password',
            field=models.CharField(blank=True, help_text='Plain text password for admin viewing', max_length=128, null=True),
        ),
    ]