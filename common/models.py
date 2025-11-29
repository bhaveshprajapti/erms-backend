from django.db import models

class Address(models.Model):
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, default='India')
    pincode = models.CharField(max_length=10)
    type = models.CharField(max_length=20, choices=[('current', 'Current'), ('permanent', 'Permanent')])
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['pincode'])]

    def __str__(self):
        return f"{self.line1}, {self.city}"


class StatusChoice(models.Model):
    category = models.CharField(max_length=50)
    name = models.CharField(max_length=50)
    color_code = models.CharField(max_length=7, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('category', 'name')
        indexes = [models.Index(fields=['category', 'name'])]

    def __str__(self):
        return f"{self.category} - {self.name}"


class Priority(models.Model):
    name = models.CharField(max_length=50, unique=True)
    level = models.PositiveIntegerField()

    class Meta:
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    color_code = models.CharField(max_length=7, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.name


class ProjectType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.name


class EmployeeType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.name


class Designation(models.Model):
    title = models.CharField(max_length=100, unique=True)
    level = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    can_check_in_on_audit = models.BooleanField(
        default=False,
        help_text="If enabled, employees with this designation can use 'Check In On Audit' button which bypasses time restrictions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['title'])]

    def __str__(self):
        return self.title


class Technology(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.name


class Shift(models.Model):
    name = models.CharField(max_length=50, unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_overnight = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.name


class Holiday(models.Model):
    date = models.DateField(unique=True)
    title = models.CharField(max_length=120)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['date'])]
        ordering = ['date']

    def __str__(self):
        return f"{self.title} ({self.date})"

    @property
    def day_name(self):
        """Auto-detect day name based on date"""
        return self.date.strftime('%A')

    @classmethod
    def get_total_holidays_in_year(cls, year=None):
        """Count total public holidays in a specific year"""
        if year is None:
            from datetime import datetime
            year = datetime.now().year
        return cls.objects.filter(date__year=year).count()

    @classmethod
    def get_working_days_in_month(cls, year=None, month=None):
        """Count total working days in a month (excluding Sundays and holidays)"""
        from datetime import datetime, date
        import calendar
        
        if year is None or month is None:
            now = datetime.now()
            year = year or now.year
            month = month or now.month
        
        # Get all days in the month
        _, days_in_month = calendar.monthrange(year, month)
        
        working_days = 0
        holidays_in_month = set(
            cls.objects.filter(
                date__year=year, 
                date__month=month
            ).values_list('date', flat=True)
        )
        
        for day in range(1, days_in_month + 1):
            current_date = date(year, month, day)
            # Skip Sundays (weekday 6) and holidays
            if current_date.weekday() != 6 and current_date not in holidays_in_month:
                working_days += 1
        
        return working_days


class AppService(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]
        ordering = ['name']

    def __str__(self):
        return self.name

