/**
 * Zyra Home & Feed Module
 * Handles feed interactions (likes, bookmarks, comments, video autoplay),
 * story viewer carousel, and infinite scroll pagination.
 */
import { getCookie } from '../utils/api.js';

export function initHome() {
    const feedContainer = document.getElementById('posts-feed-container');
    const skeletonLoader = document.getElementById('skeleton-loader');
    const endOfFeed = document.getElementById('end-of-feed');
    let page = 2;
    let loading = false;
    let emptyPage = false;

    // Active Stories Data from view context (parsed from json_script)
    const _sbDataEl = document.getElementById('story-bubbles-data');
    try {
        window.activeStoriesData = _sbDataEl ? JSON.parse(_sbDataEl.textContent || '[]') : [];
    } catch {
        window.activeStoriesData = [];
    }

    // Current Username (parsed from json_script)
    const _userEl = document.getElementById('current-user-data');
    let currentUsername = '';
    try {
        currentUsername = _userEl ? JSON.parse(_userEl.textContent || '""') : '';
    } catch {
        currentUsername = '';
    }

    let currentUserIndex = -1;
    let currentStoryIndex = -1;
    let storyTimer = null;
    let storyProgressInterval = null;
    let storyProgressPercent = 0;
    let isStoryPaused = false;
    let isStoryMuted = true; // Start muted by default to comply with browser autoplay

    const storyViewer = document.getElementById('storyViewer');
    const closeStoryViewerBtn = document.getElementById('closeStoryViewerBtn');
    const storyPrevBtn = document.getElementById('story-prev-btn');
    const storyNextBtn = document.getElementById('story-next-btn');
    const storyProgressBarsContainer = document.getElementById('story-progress-bars');
    const storyUserAvatar = document.getElementById('story-user-avatar');
    const storyUserName = document.getElementById('story-user-name');
    const storyMediaContainer = document.getElementById('story-media-container');
    const storyCaption = document.getElementById('story-viewer-caption');
    const storyAudio = document.getElementById('story-audio-element');
    const storyVolumeBtn = document.getElementById('story-volume-btn');

    // AJAX Like Handlers
    function bindLikeForms(container) {
        if (!container) return;
        container.querySelectorAll('.like-ajax-form').forEach(form => {
            if (form.dataset.bound) return;
            form.dataset.bound = "true";

            form.addEventListener('submit', function(e) {
                e.preventDefault();
                const button = this.querySelector('button');
                const icon = button ? button.querySelector('i') : null;
                const postCard = this.closest('.post-card');
                const countSpan = postCard ? postCard.querySelector('.likes-count') : null;
                const url = this.getAttribute('action');

                fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': getCookie('csrftoken'),
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (countSpan && data.likes_count !== undefined) countSpan.textContent = data.likes_count;
                    if (data.liked) {
                        if (button) button.classList.add('liked');
                        if (icon) icon.className = 'bi bi-heart-fill text-danger';
                    } else {
                        if (button) button.classList.remove('liked');
                        if (icon) icon.className = 'bi bi-heart text-white';
                    }
                })
                .catch(error => console.error('Error:', error));
            });
        });
    }

    // AJAX Bookmark Handlers
    function bindBookmarkForms(container) {
        if (!container) return;
        container.querySelectorAll('.bookmark-ajax-form').forEach(form => {
            if (form.dataset.bound) return;
            form.dataset.bound = "true";

            form.addEventListener('submit', function(e) {
                e.preventDefault();
                const button = this.querySelector('button');
                const icon = button ? button.querySelector('i') : null;
                const url = this.getAttribute('action');

                fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': getCookie('csrftoken'),
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.bookmarked) {
                        if (button) button.classList.add('saved');
                        if (icon) icon.className = 'bi bi-bookmark-fill text-warning';
                    } else {
                        if (button) button.classList.remove('saved');
                        if (icon) icon.className = 'bi bi-bookmark text-white';
                    }
                })
                .catch(error => console.error('Error:', error));
            });
        });
    }

    // AJAX Comment Handlers
    function bindCommentForms(container) {
        if (!container) return;
        container.querySelectorAll('.comment-ajax-form').forEach(form => {
            if (form.dataset.bound) return;
            form.dataset.bound = "true";

            form.addEventListener('submit', function(e) {
                e.preventDefault();
                const input = this.querySelector('input[name="content"]');
                const url = this.getAttribute('action');

                if (!input || !input.value.trim()) return;
                const formData = new FormData(this);

                fetch(url, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        input.value = '';
                        window.showToast && window.showToast('Comment posted!', 'success');
                    }
                })
                .catch(error => console.error('Error:', error));
            });
        });
    }

    // AJAX Delete Handlers
    function bindDeleteForms(container) {
        if (!container) return;
        container.querySelectorAll('.delete-post-ajax-form').forEach(form => {
            if (form.dataset.bound) return;
            form.dataset.bound = "true";

            form.addEventListener('submit', function(e) {
                e.preventDefault();
                const url = this.getAttribute('action');
                const postCard = this.closest('.post-card');

                if (typeof window.showConfirmPopup === 'function') {
                    window.showConfirmPopup({
                        title: 'Delete Post?',
                        message: 'Are you sure you want to delete this post? This action cannot be undone.',
                        confirmText: 'Delete Post',
                        confirmType: 'danger',
                        icon: 'bi-trash3-fill',
                        onConfirm: () => {
                            fetch(url, {
                                method: 'POST',
                                headers: {
                                    'X-Requested-With': 'XMLHttpRequest',
                                    'X-CSRFToken': getCookie('csrftoken'),
                                }
                            })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success && postCard) {
                                    postCard.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                                    postCard.style.opacity = '0';
                                    postCard.style.transform = 'scale(0.95)';
                                    setTimeout(() => {
                                        postCard.remove();
                                    }, 300);
                                    window.showToast && window.showToast('Post deleted', 'success');
                                } else {
                                    window.showToast && window.showToast(data.error || 'Failed to delete post', 'error');
                                }
                            })
                            .catch(error => {
                                console.error('Error:', error);
                                window.showToast && window.showToast('Network error deleting post', 'error');
                            });
                        }
                    });
                }
            });
        });
    }

    // Double-Tap to Like Handler
    function bindDoubleTapLikes(container) {
        if (!container) return;
        container.querySelectorAll('.post-body').forEach(body => {
            if (body.dataset.boundDoubleTap) return;
            body.dataset.boundDoubleTap = "true";

            body.addEventListener('dblclick', function() {
                const postCard = this.closest('.post-card');
                const heart = this.querySelector('.double-tap-heart');
                const likeForm = postCard ? postCard.querySelector('.like-ajax-form') : null;

                if (heart) {
                    heart.classList.add('animate');
                    setTimeout(() => {
                        heart.classList.remove('animate');
                    }, 800);
                }

                if (likeForm) {
                    const likeBtn = likeForm.querySelector('button');
                    if (likeBtn && !likeBtn.classList.contains('liked')) {
                        likeBtn.click();
                    }
                }
            });
        });
    }

    // Video Controllers
    let globalMuted = true;
    function bindVideoControllers(container) {
        if (!container) return;
        const videos = container.querySelectorAll('.post-video');

        videos.forEach(video => {
            if (video.dataset.bound) return;
            video.dataset.bound = "true";

            const videoContainer = video.closest('.post-video-container');
            const audioBtn = videoContainer ? videoContainer.querySelector('.video-audio-toggle') : null;

            video.addEventListener('click', function() {
                if (video.paused) {
                    video.play().catch(() => {});
                } else {
                    video.pause();
                }
            });

            if (audioBtn) {
                audioBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    globalMuted = !globalMuted;
                    document.querySelectorAll('.post-video').forEach(vid => {
                        vid.muted = globalMuted;
                        const btnIcon = vid.closest('.post-video-container')?.querySelector('.video-audio-toggle i');
                        if (btnIcon) {
                            btnIcon.className = globalMuted ? 'bi bi-volume-mute-fill' : 'bi bi-volume-up-fill';
                        }
                    });
                });
            }
        });

        if ('IntersectionObserver' in window) {
            const videoObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    const video = entry.target;
                    if (entry.isIntersecting && entry.intersectionRatio >= 0.35) {
                        video.muted = globalMuted;
                        video.play().catch(err => console.log("Feed video autoplay:", err));
                    } else if (!entry.isIntersecting || entry.intersectionRatio < 0.2) {
                        video.pause();
                    }
                });
            }, { threshold: [0.2, 0.35, 0.5] });

            videos.forEach(video => {
                videoObserver.observe(video);
                const rect = video.getBoundingClientRect();
                if (rect.top >= 0 && rect.top < window.innerHeight) {
                    video.muted = globalMuted;
                    video.play().catch(() => {});
                }
            });
        }
    }

    // Story Viewer Logic
    window.openStoryViewer = function(username) {
        currentUserIndex = window.activeStoriesData.findIndex(u => u.username === username);
        if (currentUserIndex === -1) return;
        currentStoryIndex = 0;
        if (storyViewer) {
            storyViewer.style.display = 'flex';
            showStory();
        }
    };

    function closeStoryViewer() {
        if (storyViewer) storyViewer.style.display = 'none';
        clearStoryTimers();
        const musicBadge = document.getElementById('story-music-badge');
        if (musicBadge) musicBadge.classList.add('d-none');
        if (storyAudio) {
            storyAudio.pause();
            storyAudio.src = "";
        }
        if (storyMediaContainer) {
            const activeVideo = storyMediaContainer.querySelector('video');
            if (activeVideo) {
                activeVideo.pause();
            }
        }
    }

    if (closeStoryViewerBtn) {
        closeStoryViewerBtn.addEventListener('click', closeStoryViewer);
    }

    function clearStoryTimers() {
        if (storyTimer) clearTimeout(storyTimer);
        if (storyProgressInterval) clearInterval(storyProgressInterval);
    }

    function showStory() {
        clearStoryTimers();

        const userData = window.activeStoriesData[currentUserIndex];
        if (!userData) return;
        const stories = userData.stories;
        const story = stories[currentStoryIndex];
        if (!story) return;

        // Header info
        if (userData.profile_pic) {
            storyUserAvatar.src = userData.profile_pic;
            storyUserAvatar.style.display = 'inline-block';
        } else {
            storyUserAvatar.style.display = 'none';
        }
        storyUserName.textContent = userData.username;

        // Music Visualizer status
        const musicBadge = document.getElementById('story-music-badge');
        if (musicBadge) {
            if (story.music_url) {
                musicBadge.classList.remove('d-none');
                if (isStoryMuted) {
                    musicBadge.classList.add('visualizer-muted');
                } else {
                    musicBadge.classList.remove('visualizer-muted');
                }
            } else {
                musicBadge.classList.add('d-none');
            }
        }

        // Toggle delete button for current user's own story
        const storyDeleteBtn = document.getElementById('story-delete-btn');
        if (storyDeleteBtn) {
            const isOwnStory = userData.username.toLowerCase() === currentUsername.toLowerCase();
            if (isOwnStory) {
                storyDeleteBtn.classList.remove('d-none');
            } else {
                storyDeleteBtn.classList.add('d-none');
            }
        }

        // Render progress bars
        storyProgressBarsContainer.innerHTML = '';
        stories.forEach((s, idx) => {
            const bar = document.createElement('div');
            bar.className = 'story-progress-bar';
            const fill = document.createElement('div');
            fill.className = 'story-progress-fill';
            if (idx < currentStoryIndex) {
                fill.style.width = '100%';
            } else if (idx === currentStoryIndex) {
                fill.id = 'active-story-progress-fill';
                fill.style.width = '0%';
            } else {
                fill.style.width = '0%';
            }
            bar.appendChild(fill);
            storyProgressBarsContainer.appendChild(bar);
        });

        // Caption
        if (story.caption) {
            storyCaption.textContent = story.caption;
            storyCaption.style.display = 'block';
        } else {
            storyCaption.style.display = 'none';
        }

        // Media content
        storyMediaContainer.innerHTML = '';
        if (storyAudio) {
            storyAudio.pause();
            storyAudio.src = "";
        }

        let duration = 5000;

        if (story.video_url) {
            const video = document.createElement('video');
            video.src = story.video_url;
            video.className = 'story-viewer-media';
            video.playsInline = true;
            video.autoplay = true;
            video.muted = isStoryMuted;
            storyMediaContainer.appendChild(video);

            video.onloadedmetadata = function() {
                duration = Math.min(video.duration * 1000, 15000);
                startStoryTimer(duration);
            };

            video.onerror = function() {
                startStoryTimer(5000);
            };
        } else if (story.image_url) {
            const img = document.createElement('img');
            img.src = story.image_url;
            img.className = 'story-viewer-media';
            storyMediaContainer.appendChild(img);

            if (story.music_url && storyAudio) {
                storyAudio.src = story.music_url;
                storyAudio.muted = isStoryMuted;
                storyAudio.play().catch(err => console.log("Audio play blocked until interaction:", err));
            }

            startStoryTimer(5000);
        }
    }

    function startStoryTimer(duration) {
        storyProgressPercent = 0;
        const fillElement = document.getElementById('active-story-progress-fill');
        const intervalTime = 50;
        const increment = (intervalTime / duration) * 100;

        storyProgressInterval = setInterval(() => {
            if (!isStoryPaused) {
                storyProgressPercent += increment;
                if (storyProgressPercent >= 100) {
                    storyProgressPercent = 100;
                    clearInterval(storyProgressInterval);
                }
                if (fillElement) {
                    fillElement.style.width = storyProgressPercent + '%';
                }
            }
        }, intervalTime);

        storyTimer = setTimeout(() => {
            nextStory();
        }, duration);
    }

    function nextStory() {
        const userData = window.activeStoriesData[currentUserIndex];
        if (!userData) return;
        if (currentStoryIndex < userData.stories.length - 1) {
            currentStoryIndex++;
            showStory();
        } else {
            if (currentUserIndex < window.activeStoriesData.length - 1) {
                currentUserIndex++;
                currentStoryIndex = 0;
                showStory();
            } else {
                closeStoryViewer();
            }
        }
    }

    function prevStory() {
        if (currentStoryIndex > 0) {
            currentStoryIndex--;
            showStory();
        } else {
            if (currentUserIndex > 0) {
                currentUserIndex--;
                currentStoryIndex = window.activeStoriesData[currentUserIndex].stories.length - 1;
                showStory();
            } else {
                showStory();
            }
        }
    }

    if (storyNextBtn) storyNextBtn.addEventListener('click', nextStory);
    if (storyPrevBtn) storyPrevBtn.addEventListener('click', prevStory);

    const storyTapNext = document.getElementById('story-tap-next');
    const storyTapPrev = document.getElementById('story-tap-prev');
    if (storyTapNext) storyTapNext.addEventListener('click', (e) => { e.stopPropagation(); nextStory(); });
    if (storyTapPrev) storyTapPrev.addEventListener('click', (e) => { e.stopPropagation(); prevStory(); });

    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (!storyViewer || storyViewer.style.display === 'none') return;
        if (e.key === 'ArrowRight' || e.key === ' ') {
            nextStory();
        } else if (e.key === 'ArrowLeft') {
            prevStory();
        } else if (e.key === 'Escape') {
            closeStoryViewer();
        }
    });

    // Story Delete Handler
    const storyDeleteBtn = document.getElementById('story-delete-btn');
    if (storyDeleteBtn) {
        storyDeleteBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            if (currentUserIndex < 0 || !window.activeStoriesData[currentUserIndex]) return;
            const userData = window.activeStoriesData[currentUserIndex];
            const story = userData.stories[currentStoryIndex];
            if (!story) return;

            isStoryPaused = true;
            if (typeof window.showConfirmPopup === 'function') {
                window.showConfirmPopup({
                    title: 'Delete Story?',
                    message: 'Are you sure you want to delete this story? It will disappear for all viewers.',
                    confirmText: 'Delete Story',
                    confirmType: 'danger',
                    icon: 'bi-trash3-fill',
                    onConfirm: () => {
                        fetch(`/story/delete/${story.id}/`, {
                            method: 'POST',
                            headers: {
                                'X-Requested-With': 'XMLHttpRequest',
                                'X-CSRFToken': getCookie('csrftoken'),
                            }
                        })
                        .then(res => res.json())
                        .then(data => {
                            if (data.success) {
                                userData.stories.splice(currentStoryIndex, 1);
                                window.showToast && window.showToast('Story deleted', 'success');
                                if (userData.stories.length === 0) {
                                    window.activeStoriesData.splice(currentUserIndex, 1);
                                    const bubble = document.querySelector(`.story-bubble[onclick*="${userData.username}"]`);
                                    if (bubble) bubble.remove();
                                    if (window.activeStoriesData.length === 0) {
                                        closeStoryViewer();
                                    } else {
                                        if (currentUserIndex >= window.activeStoriesData.length) {
                                            currentUserIndex = window.activeStoriesData.length - 1;
                                        }
                                        currentStoryIndex = 0;
                                        showStory();
                                    }
                                } else {
                                    if (currentStoryIndex >= userData.stories.length) {
                                        currentStoryIndex = userData.stories.length - 1;
                                    }
                                    showStory();
                                }
                            } else {
                                window.showToast && window.showToast(data.error || 'Failed to delete story', 'error');
                                isStoryPaused = false;
                            }
                        })
                        .catch(err => {
                            console.error('Delete story error:', err);
                            window.showToast && window.showToast('Network error deleting story', 'error');
                            isStoryPaused = false;
                        });
                    }
                });
            }
        });
    }

    // Story Heart Reaction
    const storyHeartBtn = document.getElementById('story-heart-reaction');
    if (storyHeartBtn) {
        storyHeartBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            this.style.transform = 'scale(1.4)';
            setTimeout(() => { this.style.transform = 'scale(1)'; }, 250);

            if (currentUserIndex >= 0 && window.activeStoriesData[currentUserIndex]) {
                const authorUsername = window.activeStoriesData[currentUserIndex].username;
                fetch(`/direct/t/${authorUsername}/send/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({ message: "❤️ Liked your story!" })
                }).catch(() => {});
            }
        });
    }

    // Story Reply Submission
    const storyReplyInput = document.getElementById('story-reply-input');
    const storySendReplyBtn = document.getElementById('story-send-reply-btn');
    function sendStoryReply() {
        if (!storyReplyInput || !storyReplyInput.value.trim()) return;
        const replyText = storyReplyInput.value.trim();
        if (currentUserIndex >= 0 && window.activeStoriesData[currentUserIndex]) {
            const authorUsername = window.activeStoriesData[currentUserIndex].username;
            fetch(`/direct/t/${authorUsername}/send/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ message: `Replied to story: "${replyText}"` })
            }).then(() => {
                storyReplyInput.value = '';
                storyReplyInput.placeholder = 'Message sent! ✓';
                setTimeout(() => { storyReplyInput.placeholder = 'Reply to story...'; }, 2000);
            }).catch(() => {});
        }
    }
    if (storySendReplyBtn) storySendReplyBtn.addEventListener('click', sendStoryReply);
    if (storyReplyInput) {
        storyReplyInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendStoryReply();
            }
        });
        storyReplyInput.addEventListener('focus', () => { isStoryPaused = true; });
        storyReplyInput.addEventListener('blur', () => { isStoryPaused = false; });
    }

    // Story volume mute/unmute action
    if (storyVolumeBtn) {
        storyVolumeBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            isStoryMuted = !isStoryMuted;
            const volumeIcon = storyVolumeBtn.querySelector('i');
            if (volumeIcon) {
                volumeIcon.className = isStoryMuted ? 'bi bi-volume-mute-fill fs-5' : 'bi bi-volume-up-fill fs-5';
            }
            const musicBadge = document.getElementById('story-music-badge');
            if (musicBadge) {
                if (isStoryMuted) {
                    musicBadge.classList.add('visualizer-muted');
                } else {
                    musicBadge.classList.remove('visualizer-muted');
                }
            }
            if (storyAudio) storyAudio.muted = isStoryMuted;
            if (storyMediaContainer) {
                const video = storyMediaContainer.querySelector('video');
                if (video) video.muted = isStoryMuted;
            }
        });
    }

    // Pause on press/hold media container, resume on release
    if (storyMediaContainer) {
        const pauseMedia = () => {
            isStoryPaused = true;
            const video = storyMediaContainer.querySelector('video');
            if (video) video.pause();
            if (storyAudio && storyAudio.src && !storyAudio.paused) storyAudio.pause();
        };
        const resumeMedia = () => {
            isStoryPaused = false;
            const video = storyMediaContainer.querySelector('video');
            if (video) video.play().catch(() => {});
            if (storyAudio && storyAudio.src && storyAudio.paused) storyAudio.play().catch(() => {});
        };

        storyMediaContainer.addEventListener('mousedown', pauseMedia);
        storyMediaContainer.addEventListener('mouseup', resumeMedia);
        storyMediaContainer.addEventListener('touchstart', pauseMedia);
        storyMediaContainer.addEventListener('touchend', resumeMedia);
    }

    // Bind all initial forms
    bindLikeForms(feedContainer);
    bindBookmarkForms(feedContainer);
    bindCommentForms(feedContainer);
    bindDeleteForms(feedContainer);
    bindDoubleTapLikes(feedContainer);
    bindVideoControllers(feedContainer);

    // Follow AJAX suggestions
    document.querySelectorAll('.follow-ajax-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const button = this.querySelector('button');
            const url = this.getAttribute('action');

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCookie('csrftoken'),
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.following) {
                    button.textContent = 'Following';
                    button.className = 'btn btn-link text-muted text-decoration-none fw-bold p-0 small';
                } else {
                    button.textContent = 'Follow';
                    button.className = 'btn btn-link text-primary text-decoration-none fw-bold p-0 small';
                }
            });
        });
    });

    // Infinite Scroll Logic
    window.addEventListener('scroll', function() {
        if (loading || emptyPage) return;

        const scrollPosition = window.innerHeight + window.scrollY;
        const pageBottom = document.documentElement.offsetHeight - 300;

        if (scrollPosition >= pageBottom) {
            loading = true;
            if (skeletonLoader) skeletonLoader.style.display = 'block';

            fetch(`?page=${page}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                if (response.headers.get('Content-Type')?.includes('application/json')) {
                    emptyPage = true;
                    if (skeletonLoader) skeletonLoader.style.display = 'none';
                    if (endOfFeed) endOfFeed.style.display = 'block';
                    return null;
                }
                return response.text();
            })
            .then(html => {
                if (!html) return;

                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = html;

                const newPosts = tempDiv.querySelectorAll('.post-card');
                if (newPosts.length === 0) {
                    emptyPage = true;
                    if (endOfFeed) endOfFeed.style.display = 'block';
                } else {
                    newPosts.forEach(card => {
                        feedContainer.appendChild(card);
                    });

                    bindLikeForms(feedContainer);
                    bindBookmarkForms(feedContainer);
                    bindCommentForms(feedContainer);
                    bindDeleteForms(feedContainer);
                    bindDoubleTapLikes(feedContainer);
                    bindVideoControllers(feedContainer);
                    page++;
                }

                loading = false;
                if (skeletonLoader) skeletonLoader.style.display = 'none';
            })
            .catch(error => {
                console.error("Infinite scroll error:", error);
                loading = false;
                if (skeletonLoader) skeletonLoader.style.display = 'none';
            });
        }
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHome);
} else {
    initHome();
}
