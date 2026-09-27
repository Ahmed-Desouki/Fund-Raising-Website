from django.db import migrations

CATEGORIES = ['Education', 'Health', 'Charity', 'Environment', 'Technology', 'Community', 'Art & Culture']


def seed(apps, schema_editor):
    Category = apps.get_model('projects', 'Category')
    for name in CATEGORIES:
        Category.objects.get_or_create(name=name)


def unseed(apps, schema_editor):
    apps.get_model('projects', 'Category').objects.filter(name__in=CATEGORIES, projects__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
