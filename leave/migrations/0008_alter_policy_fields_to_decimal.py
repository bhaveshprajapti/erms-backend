# Generated migration to change policy fields from PositiveIntegerField to DecimalField
# This allows half-day values like 1.5 for max_per_week, max_per_month, etc.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leave', '0007_add_monthly_occurrences'),
    ]

    operations = [
        # Change max_per_week from PositiveIntegerField to DecimalField
        migrations.AlterField(
            model_name='leavetypepolicy',
            name='max_per_week',
            field=models.DecimalField(
                max_digits=5, 
                decimal_places=2, 
                null=True, 
                blank=True, 
                help_text='Maximum days per week (supports half-day like 1.5)'
            ),
        ),
        # Change max_per_month from PositiveIntegerField to DecimalField
        migrations.AlterField(
            model_name='leavetypepolicy',
            name='max_per_month',
            field=models.DecimalField(
                max_digits=5, 
                decimal_places=2, 
                null=True, 
                blank=True, 
                help_text='Maximum days per month (supports half-day like 1.5)'
            ),
        ),
        # Change max_per_year from PositiveIntegerField to DecimalField
        migrations.AlterField(
            model_name='leavetypepolicy',
            name='max_per_year',
            field=models.DecimalField(
                max_digits=5, 
                decimal_places=2, 
                null=True, 
                blank=True, 
                help_text='Maximum days per year (supports half-day like 1.5)'
            ),
        ),
        # Change max_consecutive_days from PositiveIntegerField to DecimalField
        migrations.AlterField(
            model_name='leavetypepolicy',
            name='max_consecutive_days',
            field=models.DecimalField(
                max_digits=5, 
                decimal_places=2, 
                null=True, 
                blank=True, 
                help_text='Maximum consecutive days (supports half-day like 1.5)'
            ),
        ),
        # Update max_occurrences_per_month help text
        migrations.AlterField(
            model_name='leavetypepolicy',
            name='max_occurrences_per_month',
            field=models.DecimalField(
                max_digits=5, 
                decimal_places=2, 
                null=True, 
                blank=True, 
                help_text='Maximum number of leave requests per month (supports half-day like 1.5)'
            ),
        ),
    ]
