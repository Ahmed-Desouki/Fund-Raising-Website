from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Sum
from django.urls import reverse
from django.utils.translation import get_language
from django.utils import timezone


CATEGORY_ICONS = {
    'education': 'fa-graduation-cap',
    'health': 'fa-heart-pulse',
    'charity': 'fa-hands-holding-child',
    'environment': 'fa-leaf',
    'technology': 'fa-laptop-code',
    'community': 'fa-people-roof',
    'art & culture': 'fa-palette',
}


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def icon(self):
        # Font Awesome icon for the home page; admin-added categories get a generic one
        return CATEGORY_ICONS.get(self.name.lower(), 'fa-hand-holding-heart')


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=200)
    details = models.TextField()
    # Optional Arabic version of the campaign text, shown when the site is in Arabic
    title_ar = models.CharField(max_length=200, blank=True)
    details_ar = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='projects')
    tags = models.ManyToManyField(Tag, blank=True, related_name='projects')
    total_target = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('1'))])
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    # Chosen by the site admin from the Django admin panel
    is_featured = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('project_detail', args=[self.pk])

    def _in_current_language(self, english, arabic):
        return arabic if arabic and (get_language() or '').startswith('ar') else english

    @property
    def display_title(self):
        return self._in_current_language(self.title, self.title_ar)

    @property
    def display_details(self):
        return self._in_current_language(self.details, self.details_ar)

    @property
    def total_donations(self):
        return self.donations.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    @property
    def progress_percent(self):
        return min(int(self.total_donations / self.total_target * 100), 100)

    @property
    def donor_count(self):
        return self.donations.values('user').distinct().count()

    @property
    def days_left(self):
        return max((self.end_time - timezone.now()).days, 0)

    @property
    def average_rating(self):
        return self.ratings.aggregate(avg=Avg('value'))['avg'] or 0

    @property
    def is_running(self):
        now = timezone.now()
        return not self.is_cancelled and self.start_time <= now <= self.end_time

    @property
    def can_be_cancelled(self):
        # Owners may only cancel while donations are still under 25% of the target
        return not self.is_cancelled and self.total_donations < self.total_target * Decimal('0.25')

    @property
    def cover_image(self):
        return self.images.first()


class ProjectImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='project_pics/')

    def __str__(self):
        return f'Image for {self.project}'


class Donation(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='donations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donations')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('1'))])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} donated {self.amount} to {self.project}'


class Comment(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    # A reply points at its parent comment; top-level comments have no parent
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.email} on {self.project}'


class Rating(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    value = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['project', 'user'], name='one_rating_per_user_per_project'),
        ]

    def __str__(self):
        return f'{self.value}/5 for {self.project}'


class ProjectReport(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='reports')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_reports')
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Report on {self.project}'


class CommentReport(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reports')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_reports')
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Report on comment #{self.comment_id}'
