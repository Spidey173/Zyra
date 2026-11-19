/**
 * Zyra Base UI Module
 * Global modals, toast notifications, confirmation popups, and share dialogs.
 */
import { getCookie } from '../utils/api.js';

export function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Universal Custom Confirmation Dialog (Replaces browser confirm)
export function showConfirmPopup({
    title = 'Delete item?',
    message = 'Are you sure you want to delete this? This action cannot be undone.',
    confirmText = 'Delete',
    confirmType = 'danger',
    icon = 'bi-trash3-fill',
    onConfirm = () => {}
}) {
    const modalEl = document.getElementById('zyraConfirmModal');
    if (!modalEl) {
        if (window.confirm(message)) onConfirm();
        return;
    }

    document.getElementById('confirmModalTitle').textContent = title;
    document.getElementById('confirmModalMessage').textContent = message;

    const iconEl = document.getElementById('confirmModalIcon');
    if (iconEl) iconEl.className = `bi ${icon}`;

    const proceedBtn = document.getElementById('proceedConfirmBtn');
    if (proceedBtn) {
        proceedBtn.textContent = confirmText;
        proceedBtn.className = `btn btn-${confirmType} rounded-pill px-4 py-2 small fw-semibold flex-fill shadow`;
    }

    const confirmModal = window.bootstrap ? window.bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    if (!confirmModal) return;

    const newProceedBtn = proceedBtn.cloneNode(true);
    proceedBtn.parentNode.replaceChild(newProceedBtn, proceedBtn);

    newProceedBtn.addEventListener('click', function() {
        confirmModal.hide();
        if (typeof onConfirm === 'function') {
            onConfirm();
        }
    });

    confirmModal.show();
}

// Universal Toast Notification (Replaces browser alert)
export function showToast(message, type = 'info') {
    const container = document.getElementById('zyraToastContainer');
    if (!container) return;

    const icons = {
        success: 'bi-check-circle-fill text-success',
        error: 'bi-exclamation-triangle-fill text-danger',
        warning: 'bi-exclamation-circle-fill text-warning',
        info: 'bi-info-circle-fill text-info'
    };

    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white border-0 mb-2 shadow-lg';
    toast.style.background = '#1e1e24';
    toast.style.border = '1px solid #363644';
    toast.style.borderRadius = '14px';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    toast.innerHTML = `
        <div class="d-flex p-3 align-items-center">
            <i class="bi ${icons[type] || icons.info} fs-5 me-3"></i>
            <div class="toast-body p-0 small fw-medium text-white flex-grow-1">${escapeHtml(message)}</div>
            <button type="button" class="btn-close btn-close-white ms-3 p-1" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    container.appendChild(toast);
    if (window.bootstrap) {
        const bsToast = new window.bootstrap.Toast(toast, { delay: 3500 });
        bsToast.show();
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }
}

// Post Creator Modal
export function toggleCreateModal(show) {
    const createPostModal = document.getElementById('createPostModal');
    if (!createPostModal) return;
    createPostModal.style.display = show ? 'flex' : 'none';
}

// Story Creator Modal
export function toggleStoryModal(show) {
    const createStoryModal = document.getElementById('createStoryModal');
    if (!createStoryModal) return;
    if (show) toggleCreateModal(false);
    createStoryModal.style.display = show ? 'flex' : 'none';
}

// Share Post / Reel to DM Modal Logic
let shareModalInstance = null;
export function openSharePostModal(postId) {
    const modalEl = document.getElementById('sharePostModal');
    if (!modalEl) return;
    document.getElementById('sharePostIdInput').value = postId;
    if (!shareModalInstance && window.bootstrap) {
        shareModalInstance = new window.bootstrap.Modal(modalEl);
    }
    if (shareModalInstance) shareModalInstance.show();
    searchShareUsers('');
}

export function searchShareUsers(query) {
    const resultsContainer = document.getElementById('shareUserSearchResults');
    if (!resultsContainer) return;
    resultsContainer.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-primary" role="status"></div></div>';

    fetch(`/direct/api/search-users/?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
            const users = (data && data.users) ? data.users : [];
            resultsContainer.innerHTML = '';
            if (users.length === 0) {
                resultsContainer.innerHTML = '<p class="text-white-50 small text-center py-3 mb-0">No users found.</p>';
                return;
            }
            users.forEach(u => {
                const item = document.createElement('div');
                item.className = 'd-flex align-items-center justify-content-between p-2 rounded-3';
                item.style.background = 'var(--bg-surface-2, #24242a)';
                item.innerHTML = `
                    <div class="d-flex align-items-center gap-2 overflow-hidden">
                        ${u.profile_pic ? `<img src="${u.profile_pic}" class="rounded-circle" style="width: 36px; height: 36px; object-fit: cover; flex-shrink: 0;">` : `<div class="rounded-circle text-white fw-bold d-flex align-items-center justify-content-center" style="width: 36px; height: 36px; font-size: 0.85rem; background: var(--story-gradient); flex-shrink: 0;">${u.username.charAt(0).toUpperCase()}</div>`}
                        <div class="overflow-hidden">
                            <span class="text-white small fw-bold d-block text-truncate">${escapeHtml(u.username)}</span>
                            ${u.first_name ? `<span class="text-white-50 small d-block text-truncate" style="font-size: 0.72rem;">${escapeHtml(u.first_name)} ${escapeHtml(u.last_name || '')}</span>` : ''}
                        </div>
                    </div>
                    <button type="button" class="btn btn-sm btn-grad rounded-pill px-3 py-1 send-share-btn flex-shrink-0" data-username="${u.username}">Send</button>
                `;
                resultsContainer.appendChild(item);
            });

            resultsContainer.querySelectorAll('.send-share-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const targetUsername = this.dataset.username;
                    const postId = document.getElementById('sharePostIdInput').value;
                    const note = document.getElementById('shareNoteInput') ? document.getElementById('shareNoteInput').value : '';
                    this.disabled = true;
                    this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Sending...';

                    const formData = new FormData();
                    formData.append('username', targetUsername);
                    formData.append('post_id', postId);
                    formData.append('note', note);

                    fetch('/direct/api/share-post/', {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: formData
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.success) {
                            this.className = 'btn btn-sm btn-success rounded-pill px-3 py-1';
                            this.textContent = 'Sent ✓';
                            showToast(`Shared to @${targetUsername}!`, 'success');
                            setTimeout(() => { 
                                if (shareModalInstance) shareModalInstance.hide(); 
                                if (document.getElementById('shareNoteInput')) document.getElementById('shareNoteInput').value = '';
                            }, 800);
                        } else {
                            this.disabled = false;
                            this.textContent = 'Send';
                            showToast(data.error || 'Failed to send post', 'error');
                        }
                    })
                    .catch(() => {
                        this.disabled = false;
                        this.textContent = 'Send';
                        showToast('Network error sharing post', 'error');
                    });
                });
            });
        })
        .catch(() => {
            resultsContainer.innerHTML = '<p class="text-danger small text-center py-2">Failed to load users.</p>';
        });
}

// Expose helpers on window immediately upon script evaluation
if (typeof window !== 'undefined') {
    window.getCookie = getCookie;
    window.escapeHtml = escapeHtml;
    window.showConfirmPopup = showConfirmPopup;
    window.showToast = showToast;
    window.toggleCreateModal = toggleCreateModal;
    window.toggleStoryModal = toggleStoryModal;
    window.openSharePostModal = openSharePostModal;
}

export function initBase() {
    // Expose helpers globally for legacy template handlers
    window.getCookie = getCookie;
    window.escapeHtml = escapeHtml;
    window.showConfirmPopup = showConfirmPopup;
    window.showToast = showToast;
    window.toggleCreateModal = toggleCreateModal;
    window.toggleStoryModal = toggleStoryModal;
    window.openSharePostModal = openSharePostModal;

    // Post modal listeners
    const openCreateModalBtn = document.getElementById('openCreateModalBtn');
    const openCreateModalMobileBtn = document.getElementById('openCreateModalMobileBtn');
    const closeCreateModalBtn = document.getElementById('closeCreateModalBtn');
    const cancelCreateModalBtn = document.getElementById('cancelCreateModalBtn');

    if (openCreateModalBtn) openCreateModalBtn.addEventListener('click', (e) => { e.preventDefault(); toggleCreateModal(true); });
    if (openCreateModalMobileBtn) openCreateModalMobileBtn.addEventListener('click', (e) => { e.preventDefault(); toggleCreateModal(true); });
    if (closeCreateModalBtn) closeCreateModalBtn.addEventListener('click', () => toggleCreateModal(false));
    if (cancelCreateModalBtn) cancelCreateModalBtn.addEventListener('click', () => toggleCreateModal(false));

    // Story modal listeners
    const closeStoryModalBtn = document.getElementById('closeStoryModalBtn');
    const cancelStoryModalBtn = document.getElementById('cancelStoryModalBtn');

    if (closeStoryModalBtn) closeStoryModalBtn.addEventListener('click', () => toggleStoryModal(false));
    if (cancelStoryModalBtn) cancelStoryModalBtn.addEventListener('click', () => toggleStoryModal(false));

    // Share modal search input
    const shareSearchInput = document.getElementById('shareUserSearchInput');
    if (shareSearchInput) {
        let searchTimeout = null;
        shareSearchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                searchShareUsers(this.value.trim());
            }, 200);
        });
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBase);
} else {
    initBase();
}

