/**
 * Zyra Reels Module
 * Handles video playback, snap-scrolling, double-tap hearts, and AJAX actions.
 */
import { getCookie, fetchJson } from '../utils/api.js';

export function initReels() {
    let globalMuted = true;

    // AJAX Like Handlers
    document.querySelectorAll('.like-ajax-form').forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            const button = this.querySelector('button');
            const icon = button ? button.querySelector('i') : null;
            const item = this.closest('.reel-item');
            const countSpan = item ? item.querySelector('.likes-count') : null;
            const url = this.getAttribute('action');

            try {
                const data = await fetchJson(url, { method: 'POST' });
                if (countSpan && data.likes_count !== undefined) {
                    countSpan.textContent = data.likes_count;
                }
                if (data.liked) {
                    if (button) {
                        button.classList.add('liked');
                        button.style.transform = 'scale(1.25)';
                        setTimeout(() => button.style.transform = '', 200);
                    }
                    if (icon) icon.className = 'bi bi-heart-fill text-danger';
                } else {
                    if (button) button.classList.remove('liked');
                    if (icon) icon.className = 'bi bi-heart text-white';
                }
            } catch (err) {
                console.error("Reel like error:", err);
            }
        });
    });

    // AJAX Bookmark Handlers
    document.querySelectorAll('.bookmark-ajax-form').forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            const button = this.querySelector('button');
            const icon = button ? button.querySelector('i') : null;
            const url = this.getAttribute('action');

            try {
                const data = await fetchJson(url, { method: 'POST' });
                if (data.bookmarked) {
                    if (button) {
                        button.classList.add('saved');
                        button.style.transform = 'scale(1.2)';
                        setTimeout(() => button.style.transform = '', 200);
                    }
                    if (icon) icon.className = 'bi bi-bookmark-fill text-warning';
                } else {
                    if (button) button.classList.remove('saved');
                    if (icon) icon.className = 'bi bi-bookmark text-white';
                }
            } catch (err) {
                console.error("Reel bookmark error:", err);
            }
        });
    });

    // Follow AJAX Handler
    document.querySelectorAll('.follow-ajax-form').forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            const button = this.querySelector('button');
            const url = this.getAttribute('action');

            try {
                const data = await fetchJson(url, { method: 'POST' });
                if (data.following) {
                    button.textContent = 'Following';
                    button.classList.remove('reel-follow-btn');
                    button.className = 'btn btn-sm btn-outline-secondary';
                } else {
                    button.textContent = 'Follow';
                    button.className = 'btn btn-sm reel-follow-btn';
                }
            } catch (err) {
                console.error("Reel follow error:", err);
            }
        });
    });

    // Share Post Button Listener
    document.querySelectorAll('.reel-share-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const postId = this.dataset.postId;
            if (postId && typeof window.openSharePostModal === 'function') {
                window.openSharePostModal(postId);
            }
        });
    });

    // Video Play/Pause & Mute Toggle
    const videos = document.querySelectorAll('.reel-video');
    videos.forEach(video => {
        const item = video.closest('.reel-item');
        const audioBtn = item ? item.querySelector('.video-audio-toggle') : null;

        // Click to play/pause
        video.addEventListener('click', function() {
            if (video.paused) {
                video.play().catch(() => {});
            } else {
                video.pause();
            }
        });

        // Double click to like with particle burst
        video.addEventListener('dblclick', function() {
            const heart = item ? item.querySelector('.double-tap-heart') : null;
            const likeForm = item ? item.querySelector('.like-ajax-form') : null;
            if (heart) {
                heart.classList.add('animate');
                setTimeout(() => heart.classList.remove('animate'), 750);
            }
            if (likeForm) {
                const likeBtn = likeForm.querySelector('button');
                if (likeBtn && !likeBtn.classList.contains('liked')) {
                    likeBtn.click();
                }
            }
        });

        if (audioBtn) {
            audioBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                globalMuted = !globalMuted;
                document.querySelectorAll('.reel-video').forEach(v => {
                    v.muted = globalMuted;
                    const icon = v.closest('.reel-item')?.querySelector('.video-audio-toggle i');
                    if (icon) {
                        icon.className = globalMuted ? 'bi bi-volume-mute-fill fs-6 text-white' : 'bi bi-volume-up-fill fs-6 text-white';
                    }
                });
            });
        }
    });

    // 60fps Autoplay snap logic using IntersectionObserver
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const video = entry.target;
                if (entry.isIntersecting) {
                    video.muted = globalMuted;
                    video.play().catch(err => console.log("Reels autoplay block:", err));
                } else {
                    video.pause();
                }
            });
        }, { threshold: 0.6 });

        videos.forEach(video => observer.observe(video));
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initReels);
} else {
    initReels();
}
