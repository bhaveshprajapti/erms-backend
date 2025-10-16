# Generated migration for new attendance fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='total_break_time',
            field=models.DurationField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='attendance',
            name='break_start_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='attendance',
            name='day_ended',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='attendance',
            name='day_end_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='attendance',
            name='day_status',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]