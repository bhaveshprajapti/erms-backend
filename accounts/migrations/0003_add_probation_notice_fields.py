# Generated migration for adding probation and notice period fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_add_folder_path'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_on_probation',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='probation_months',
            field=models.PositiveIntegerField(blank=True, help_text='Number of months for probation period', null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='is_on_notice_period',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='notice_period_end_date',
            field=models.DateField(blank=True, help_text='End date of notice period', null=True),
        ),
    ]
