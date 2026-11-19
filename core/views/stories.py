from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from ..models import Story
from ..utils.rate_limit import rate_limit
from ..utils.media import validate_media_file, compress_and_optimize_image

@login_required
@rate_limit('create_story', limit=20, period=300)
def create_story_view(request):
    """Handles story creation with image or video and optional background music."""
    if request.method == 'POST':
        image = request.FILES.get('image')
        video = request.FILES.get('video')
        music = request.FILES.get('music')
        caption = request.POST.get('caption', '').strip()

        if image or video:
            try:
                if image:
                    validate_media_file(image, media_types=('image',), max_size_mb=15)
                    image = compress_and_optimize_image(image, max_dimension=1600, quality=85)
                if video:
                    validate_media_file(video, media_types=('video',), max_size_mb=50)
                if music:
                    validate_media_file(music, media_types=('audio',), max_size_mb=20)

                Story.objects.create(
                    user=request.user,
                    image=image,
                    video=video,
                    music=music,
                    caption=caption
                )
                messages.success(request, "Story shared successfully!")
            except ValidationError as e:
                messages.error(request, str(e))
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
