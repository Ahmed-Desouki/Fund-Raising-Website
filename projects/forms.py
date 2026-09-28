from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Category, Donation, Project, ProjectImage, Tag


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleImageInput(attrs={'accept': 'image/*'}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(d, initial) for d in data]
        return [single_clean(data, initial)] if data else []


class ProjectForm(forms.ModelForm):
    tags = forms.CharField(
        required=False,
        help_text=_('Separate tags with commas, e.g. health, children, education'),
    )
    images = MultipleImageField(required=True)

    class Meta:
        model = Project
        fields = ['title', 'details', 'title_ar', 'details_ar', 'category', 'total_target', 'start_time', 'end_time']
        widgets = {
            'details': forms.Textarea(attrs={'rows': 6}),
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all()

    def clean_tags(self):
        raw = self.cleaned_data.get('tags', '')
        names = {t.strip().lower() for t in raw.split(',') if t.strip()}
        return sorted(names)

    def clean(self):
        cleaned_data = super().clean()
        start, end = cleaned_data.get('start_time'), cleaned_data.get('end_time')
        if start and end and end <= start:
            self.add_error('end_time', _('End time must be after the start time.'))
        return cleaned_data

    def save(self, owner):
        project = super().save(commit=False)
        project.owner = owner
        project.save()
        project.tags.set([Tag.objects.get_or_create(name=name)[0] for name in self.cleaned_data['tags']])
        for image in self.cleaned_data['images']:
            ProjectImage.objects.create(project=project, image=image)
        return project


class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ['amount']
        widgets = {'amount': forms.NumberInput(attrs={'min': 1, 'step': '1', 'placeholder': 'Amount (EGP)'})}


class CommentForm(forms.Form):
    content = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write a comment…'}))
    parent_id = forms.IntegerField(required=False, widget=forms.HiddenInput)


class ReportForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Why are you reporting this?'}))


class RatingForm(forms.Form):
    value = forms.IntegerField(min_value=1, max_value=5)
