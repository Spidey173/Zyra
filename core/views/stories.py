from django.shortcuts import redirect
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
