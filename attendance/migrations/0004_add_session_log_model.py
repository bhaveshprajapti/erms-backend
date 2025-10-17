# Generated manually for session log model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0003_merge_0002_add_break_and_day_end_fields_0002_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SessionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[('login', 'User Login'), ('logout', 'User Logout'), ('check_in', 'Check In'), ('check_out', 'Check Out'), ('start_break', 'Start Break'), ('end_break', 'End Break'), ('end_of_day', 'End of Day'), ('auto_end_day', 'Auto End Day (Session Timeout)'), ('admin_reset', 'Admin Reset Day')], max_length=20)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('date', models.DateField()),
                ('session_count', models.PositiveIntegerField(blank=True, null=True)),
                ('location', models.JSONField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('last_activity', models.DateTimeField(blank=True, null=True)),
                ('is_session_active', models.BooleanField(default=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.user')),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='sessionlog',
            index=models.Index(fields=['user', 'date', 'event_type'], name='attendance_s_user_id_b8e8c5_idx'),
        ),
        migrations.AddIndex(
            model_name='sessionlog',
            index=models.Index(fields=['user', 'is_session_active'], name='attendance_s_user_id_0c7b4a_idx'),
        ),
        migrations.AddIndex(
            model_name='sessionlog',
            index=models.Index(fields=['last_activity'], name='attendance_s_last_ac_4b5c8d_idx'),
        ),
    ]