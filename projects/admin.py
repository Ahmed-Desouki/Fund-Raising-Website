from django.contrib import admin

from .models import Category, Comment, CommentReport, Donation, Project, ProjectImage, ProjectReport, Rating, Tag


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'owner', 'category', 'total_target', 'end_time', 'is_featured', 'is_cancelled']
    list_editable = ['is_featured']
    list_filter = ['is_featured', 'is_cancelled', 'category']
    search_fields = ['title', 'owner__email']
    inlines = [ProjectImageInline]


@admin.register(ProjectReport, CommentReport)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'user', 'created_at']


admin.site.register([Category, Tag, Donation, Comment, Rating])
