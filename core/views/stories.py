from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Story

@login_required
def create_story_view(request):
    """Handles story creation with image or video and optional background music."""
    if request.method == 'POST':
        image = request.FILES.get('image')
        video = request.FILES.get('video')
        music = request.FILES.get('music')
        caption = request.POST.get('caption', '').strip()

        if image or video:
            Story.objects.create(
                user=request.user,
                image=image,
                video=video,
                music=music,
                caption=caption
            )
            messages.success(request, "Story shared successfully!")
        else:
            messages.error(request, "Please upload either a photo or video to share a story.")
    return redirect('home')


@login_required
def delete_story_view(request, story_id):
    """Allows the story author to delete their active story."""
    if request.method == 'POST':
        story = get_object_or_404(Story, id=story_id)
        if story.user != request.user:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
            return HttpResponseForbidden("You are not allowed to delete this story.")

        story.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'story_id': story_id})
        messages.success(request, "Story deleted successfully.")
        return redirect('home')
    return redirect('home')
