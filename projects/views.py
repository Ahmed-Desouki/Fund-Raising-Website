from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CommentForm, DonationForm, ProjectForm, RatingForm, ReportForm
from .models import Category, Comment, CommentReport, Project, ProjectReport, Rating


def active_projects():
    return Project.objects.filter(is_cancelled=False).select_related('category').prefetch_related('images')


def home(request):
    now = timezone.now()
    top_rated = (
        active_projects()
        .filter(start_time__lte=now, end_time__gte=now)
        .annotate(avg_rating=Avg('ratings__value'))
        .filter(avg_rating__isnull=False)
        .order_by('-avg_rating')[:5]
    )
    context = {
        'top_rated': top_rated,
        'latest': active_projects().order_by('-created_at')[:5],
        'featured': active_projects().filter(is_featured=True).order_by('-created_at')[:5],
        'categories': Category.objects.annotate(project_count=Count('projects', filter=Q(projects__is_cancelled=False))),
    }
    return render(request, 'projects/home.html', context)


def category_projects(request, pk):
    category = get_object_or_404(Category, pk=pk)
    projects = active_projects().filter(category=category)
    return render(request, 'projects/project_list.html', {'projects': projects, 'heading': category.name})


def search(request):
    query = request.GET.get('q', '').strip()
    projects = Project.objects.none()
    if query:
        projects = active_projects().filter(Q(title__icontains=query) | Q(tags__name__iexact=query)).distinct()
    return render(request, 'projects/project_list.html', {
        'projects': projects,
        'heading': f'Results for “{query}”' if query else 'Search',
        'query': query,
    })


@login_required
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save(owner=request.user)
            messages.success(request, 'Your campaign is live.')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, 'projects/project_form.html', {'form': form})


def project_detail(request, pk):
    project = get_object_or_404(
        Project.objects.select_related('owner', 'category').prefetch_related('images', 'tags'), pk=pk
    )
    similar = (
        active_projects()
        .filter(tags__in=project.tags.all())
        .exclude(pk=project.pk)
        .annotate(shared_tags=Count('tags'))
        .order_by('-shared_tags', '-created_at')
        .distinct()[:4]
    )
    user_rating = None
    if request.user.is_authenticated:
        user_rating = Rating.objects.filter(project=project, user=request.user).values_list('value', flat=True).first()

    context = {
        'project': project,
        'comments': project.comments.filter(parent__isnull=True).select_related('user').prefetch_related('replies__user'),
        'similar': similar,
        'donation_form': DonationForm(),
        'comment_form': CommentForm(),
        'report_form': ReportForm(),
        'user_rating': user_rating,
        'rating_range': range(1, 6),
        'recent_donations': project.donations.select_related('user')[:5],
        'preset_amounts': [50, 100, 250, 500],
        'share_url': request.build_absolute_uri(),
    }
    return render(request, 'projects/project_detail.html', context)


@login_required
@require_POST
def donate(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not project.is_running:
        messages.error(request, 'This campaign is not accepting donations.')
        return redirect('project_detail', pk=pk)

    form = DonationForm(request.POST)
    if form.is_valid():
        donation = form.save(commit=False)
        donation.project = project
        donation.user = request.user
        donation.save()
        messages.success(request, f'Thank you for donating {donation.amount} EGP!')
    else:
        messages.error(request, 'Please enter a valid donation amount.')
    return redirect('project_detail', pk=pk)


@login_required
@require_POST
def add_comment(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        parent = None
        if form.cleaned_data['parent_id']:
            parent = get_object_or_404(Comment, pk=form.cleaned_data['parent_id'], project=project)
        Comment.objects.create(project=project, user=request.user, parent=parent, content=form.cleaned_data['content'])
    return redirect(f"{project.get_absolute_url()}#comments")


@login_required
@require_POST
def rate_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = RatingForm(request.POST)
    if form.is_valid():
        Rating.objects.update_or_create(project=project, user=request.user, defaults={'value': form.cleaned_data['value']})
        messages.success(request, 'Thanks for rating this campaign.')
    return redirect('project_detail', pk=pk)


@login_required
@require_POST
def report_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = ReportForm(request.POST)
    if form.is_valid():
        ProjectReport.objects.create(project=project, user=request.user, reason=form.cleaned_data['reason'])
        messages.success(request, 'Report submitted. Our team will review it.')
    return redirect('project_detail', pk=pk)


@login_required
@require_POST
def report_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    form = ReportForm(request.POST)
    if form.is_valid():
        CommentReport.objects.create(comment=comment, user=request.user, reason=form.cleaned_data['reason'])
        messages.success(request, 'Comment reported. Our team will review it.')
    return redirect('project_detail', pk=comment.project_id)


@login_required
@require_POST
def cancel_project(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    if project.can_be_cancelled:
        project.is_cancelled = True
        project.save(update_fields=['is_cancelled'])
        messages.success(request, 'Your campaign has been cancelled.')
    else:
        messages.error(request, 'Campaigns can only be cancelled while donations are under 25% of the target.')
    return redirect('project_detail', pk=pk)


@login_required
def my_projects(request):
    projects = request.user.projects.select_related('category').prefetch_related('images')
    return render(request, 'projects/project_list.html', {'projects': projects, 'heading': 'My campaigns'})


@login_required
def my_donations(request):
    donations = request.user.donations.select_related('project')
    return render(request, 'projects/my_donations.html', {'donations': donations})
