/**
 * Zyra Direct Messaging Module
 * Handles WebSockets, optimistic chat rendering, voice notes, audio waveforms,
 * reactions, themes, message edits, unsending, and real-time typing indicators.
 */
import { getCookie } from '../utils/api.js';

export function initDirect() {
    const configEl = document.getElementById('direct-config-data');
    const config = configEl ? JSON.parse(configEl.textContent || '{}') : {};
    const activeConvId = config.activeConvId || '';
    const currentUsername = config.currentUsername || '';
    const activePartnerUsername = config.activePartnerUsername || '';
    const activePartnerAvatar = config.activePartnerAvatar || '';

    const messagesContainer = document.getElementById('messagesContainer');
    const messageInput = document.getElementById('messageTextInput');
    const sendBtn = document.getElementById('sendBtn');
    const themePickerBtn = document.getElementById('themePickerBtn');
    const attachBtn = document.getElementById('attachImageBtn');
    const imageInput = document.getElementById('imageFileInput');
    const chatForm = document.getElementById('chatMessageForm');
    const imagePreviewBanner = document.getElementById('imagePreviewBanner');
    const imagePreviewImg = document.getElementById('imagePreviewImg');
    const cancelImageBtn = document.getElementById('cancelImageBtn');
    const replyBanner = document.getElementById('replyContextBanner');
    const replyToUserSpan = document.getElementById('replyToUser');
    const replyToTextP = document.getElementById('replyToText');
    const replyToInput = document.getElementById('replyToInput');
    const cancelReplyBtn = document.getElementById('cancelReplyBtn');
    const editBanner = document.getElementById('editContextBanner');
    const editOriginalTextP = document.getElementById('editOriginalText');
    const cancelEditBtn = document.getElementById('cancelEditBtn');
    const emojiToggleBtn = document.getElementById('emojiToggleBtn');
    const emojiPopup = document.getElementById('emojiPickerPopup');
    const convSearchInput = document.getElementById('convSearchInput');
    const clearConvSearch = document.getElementById('clearConvSearch');
    const userSearchModalInput = document.getElementById('userSearchModalInput');
    const userSearchResults = document.getElementById('userSearchResults');
    const toggleDetailsBtn = document.getElementById('toggleDetailsBtn');
    const closeDetailsBtn = document.getElementById('closeDetailsBtn');
    const chatDetailsDrawer = document.getElementById('chatDetailsDrawer');

    // Voice Recording & Preview DOM elements
    const micBtn = document.getElementById('micBtn');
    const normalInputPill = document.getElementById('normalInputPill');
    const voiceRecordingBar = document.getElementById('voiceRecordingBar');
    const voiceRecordTimer = document.getElementById('voiceRecordTimer');
    const cancelVoiceRecordBtn = document.getElementById('cancelVoiceRecordBtn');
    const stopVoiceRecordBtn = document.getElementById('stopVoiceRecordBtn');
    const voicePreviewBar = document.getElementById('voicePreviewBar');
    const previewVoicePlayBtn = document.getElementById('previewVoicePlayBtn');
    const previewPlayIcon = document.getElementById('previewPlayIcon');
    const previewVoiceSeekBar = document.getElementById('previewVoiceSeekBar');
    const previewVoiceCurrentTime = document.getElementById('previewVoiceCurrentTime');
    const previewVoiceTotalDuration = document.getElementById('previewVoiceTotalDuration');
    const discardVoicePreviewBtn = document.getElementById('discardVoicePreviewBtn');
    const confirmSendVoiceBtn = document.getElementById('confirmSendVoiceBtn');

    let mediaRecorder = null;
    let audioStream = null;
    let audioChunks = [];
    let recordedAudioBlob = null;
    let previewAudio = null;
    let recordTimerInterval = null;
    let recordSeconds = 0;

    let highestMessageId = 0;
    const renderedMessageIds = new Set();
    window.zyraMessagesMap = new Map();
    let isPolling = false;
    let selectedImageFile = null;
    let activeReplyMsg = null;
    let activeEditingMsgId = null;

    // Index any server-rendered message DOM elements
    document.querySelectorAll('.message-bubble-wrapper[data-msg-id]').forEach(el => {
        const id = parseInt(el.getAttribute('data-msg-id'), 10);
        if (id) {
            renderedMessageIds.add(id);
            if (id > highestMessageId) highestMessageId = id;
        }
    });

    // Helper: format audio seconds to M:SS
    function formatAudioTime(seconds) {
        if (isNaN(seconds) || seconds < 0 || !isFinite(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
    }

    // Helper: generate Instagram style waveform bars
    function generateWaveformBars() {
        const heights = [35, 60, 45, 90, 75, 40, 85, 100, 55, 70, 95, 45, 60, 80, 50, 90, 65, 40, 75, 90, 50, 70, 40, 60];
        return heights.map(h => `<div class="voice-waveform-bar" style="height: ${h}%;"></div>`).join('');
    }

    // Helper: CSRF Token
    function getCsrfToken() {
        const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (input) return input.value;
        if (typeof window.getCookie === 'function') return window.getCookie('csrftoken');
        return '';
    }

    // Helper: Escape HTML
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Auto Scroll directly to latest message
    function scrollToBottom(smooth = false) {
        if (!messagesContainer) return;
        if (smooth) {
            messagesContainer.scrollTo({
                top: messagesContainer.scrollHeight,
                behavior: 'smooth'
            });
        } else {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    function ensureScrolledToBottom() {
        scrollToBottom(false);
        requestAnimationFrame(() => scrollToBottom(false));
        setTimeout(() => scrollToBottom(false), 50);
        setTimeout(() => scrollToBottom(false), 200);
    }

    // Parse Initial Messages
    try {
        const dataEl = document.getElementById('initial-messages-data');
        if (dataEl && dataEl.textContent) {
            let initialMessages = JSON.parse(dataEl.textContent);
            if (typeof initialMessages === 'string') {
                initialMessages = JSON.parse(initialMessages);
            }
            if (Array.isArray(initialMessages)) {
                initialMessages.forEach(msg => {
                    if (msg && msg.id) {
                        window.zyraMessagesMap.set(Number(msg.id), msg);
                    }
                    appendMessageDOM(msg);
                });
                ensureScrolledToBottom();
            }
        }
    } catch (e) {
        console.error("Initial messages parse error:", e);
    }

    window.addEventListener('load', ensureScrolledToBottom);

    // =========================================================================
    // FULL-DUPLEX WEBSOCKET CLIENT (< 30ms INSTANT DELIVERY)
    // =========================================================================
    let chatSocket = null;
    let typingTimer = null;
    let isSocketOpen = false;

    let wsRetryCount = 0;
    const MAX_WS_RETRIES = 3;

    function initWebSocket() {
        if (!activeConvId || wsRetryCount >= MAX_WS_RETRIES) return;
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat/${activeConvId}/`;

        try {
            chatSocket = new WebSocket(wsUrl);
            window.zyraChatSocket = chatSocket;

            chatSocket.onopen = function() {
                isSocketOpen = true;
                wsRetryCount = 0;
                console.log("WebSocket opened successfully:", wsUrl);
                const statusBadge = document.getElementById('wsLiveStatus');
                if (statusBadge) statusBadge.classList.remove('d-none');

                // If reconnecting with known message history, sync any missed messages
                if (window.latestMessageId && chatSocket && chatSocket.readyState === WebSocket.OPEN) {
                    try {
                        chatSocket.send(JSON.stringify({
                            action: 'reconnect',
                            last_message_id: window.latestMessageId
                        }));
                    } catch (e) {}
                }
            };

            chatSocket.onmessage = function(e) {
                try {
                    const data = JSON.parse(e.data);
                    handleSocketEvent(data);
                } catch (err) {
                    console.error("Socket message parse error:", err);
                }
            };

            chatSocket.onclose = function() {
                isSocketOpen = false;
                const statusBadge = document.getElementById('wsLiveStatus');
                if (statusBadge) statusBadge.classList.add('d-none');
                wsRetryCount++;
                if (wsRetryCount < MAX_WS_RETRIES) {
                    setTimeout(initWebSocket, Math.min(2500 * wsRetryCount, 10000));
                }
            };

            chatSocket.onerror = function() {
                chatSocket.close();
            };
        } catch (err) {
            console.error("WebSocket init error:", err);
        }
    }

    function handleSocketEvent(data) {
        if (!data || !data.type) return;

        if (data.type === 'sync_history' && Array.isArray(data.messages)) {
            data.messages.forEach(msg => {
                if (msg && msg.id) {
                    window.latestMessageId = Math.max(window.latestMessageId || 0, msg.id);
                    appendMessageDOM(msg, false);
                }
            });
            if (data.messages.length > 0) scrollToBottom(true);
            return;
        }

        if (data.type === 'new_message') {
            hideTypingIndicator();
            appendMessageDOM(data.message, false);
            scrollToBottom(true);
        } else if (data.type === 'message_edited') {
            const el = document.querySelector(`[data-msg-id="${data.message.id}"]`);
            if (el) {
                const textDiv = el.querySelector('.message-text-content');
                if (textDiv) textDiv.textContent = data.message.content;
                const metaDiv = el.querySelector('.message-meta');
                if (metaDiv && !metaDiv.querySelector('.message-edited-badge')) {
                    const span = document.createElement('span');
                    span.className = 'message-edited-badge me-1';
                    span.textContent = '(edited)';
                    metaDiv.prepend(span);
                }
            }
        } else if (data.type === 'message_deleted') {
            const el = document.querySelector(`[data-msg-id="${data.message_id}"]`);
            if (el) {
                el.style.opacity = '0';
                setTimeout(() => el.remove(), 200);
            }
        } else if (data.type === 'message_reaction') {
            updateMessageReactionsDOM(data.message.id, data.message.reactions);
        } else if (data.type === 'user_typing') {
            if (data.is_typing) {
                showTypingIndicator();
            } else {
                hideTypingIndicator();
            }
        } else if (data.type === 'user_status_changed') {
            if (data.username && data.username.toLowerCase() === activePartnerUsername.toLowerCase()) {
                const statusEl = document.getElementById('headerPartnerStatus');
                const headerDot = document.getElementById('headerPartnerOnlineDot');
                if (statusEl) {
                    if (data.is_online) {
                        statusEl.innerHTML = '<span class="active-pulse-indicator"></span> Active now';
                        if (headerDot) headerDot.classList.remove('d-none');
                    } else {
                        statusEl.innerHTML = `<span class="offline-dot"></span> ${data.status_text || 'Offline'}`;
                        if (headerDot) headerDot.classList.add('d-none');
                    }
                }
            }
            const convDot = document.getElementById(`convDot-${(data.username || '').toLowerCase()}`);
            if (convDot) {
                if (data.is_online) convDot.classList.remove('d-none');
                else convDot.classList.add('d-none');
            }
        } else if (data.type === 'messages_read') {
            document.querySelectorAll('.message-bubble-wrapper.sent .message-meta').forEach(meta => {
                if (!meta.textContent.includes('Seen')) {
                    meta.innerHTML += ' • Seen';
                }
            });
        } else if (data.type === 'theme_changed') {
            applyChatThemeDOM(data.theme_key, data.custom_theme_image_url);
        }
    }

    function showTypingIndicator() {
        let typingEl = document.getElementById('chatTypingIndicator');
        if (!typingEl && messagesContainer) {
            typingEl = document.createElement('div');
            typingEl.id = 'chatTypingIndicator';
            typingEl.className = 'typing-indicator-wrapper';
            typingEl.innerHTML = `
                ${activePartnerAvatar ? `<img src="${activePartnerAvatar}" class="message-bubble-avatar">` : `<div class="message-bubble-avatar text-white fw-bold d-flex align-items-center justify-content-center" style="background: var(--story-gradient); font-size: 0.75rem;">${activePartnerUsername.charAt(0).toUpperCase()}</div>`}
                <div class="typing-bubble">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </div>
            `;
            messagesContainer.appendChild(typingEl);
            scrollToBottom(true);
        }
    }

    function hideTypingIndicator() {
        const typingEl = document.getElementById('chatTypingIndicator');
        if (typingEl) typingEl.remove();
    }

    if (activeConvId) {
        initWebSocket();
    }

    // Input state listener (Toggle Send vs Theme Picker & Typing broadcast)
    function updateSendBtnState() {
        if (!messageInput) return;
        const hasText = messageInput.value.trim().length > 0;
        const hasImage = selectedImageFile !== null;

        if (activeEditingMsgId) {
            if (sendBtn) {
                sendBtn.textContent = 'Save';
                sendBtn.classList.remove('d-none');
            }
            if (themePickerBtn) themePickerBtn.classList.add('d-none');
            return;
        }

        if (sendBtn) sendBtn.textContent = 'Send';

        if (hasText || hasImage) {
            if (sendBtn) sendBtn.classList.remove('d-none');
            if (themePickerBtn) themePickerBtn.classList.add('d-none');
        } else {
            if (sendBtn) sendBtn.classList.add('d-none');
            if (themePickerBtn) themePickerBtn.classList.remove('d-none');
        }
    }

    if (messageInput) {
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 100) + 'px';
            updateSendBtnState();

            // Emit live typing indicator over WebSocket
            if (isSocketOpen && chatSocket) {
                chatSocket.send(JSON.stringify({ action: 'typing', is_typing: true }));
                clearTimeout(typingTimer);
                typingTimer = setTimeout(() => {
                    if (isSocketOpen && chatSocket) {
                        chatSocket.send(JSON.stringify({ action: 'typing', is_typing: false }));
                    }
                }, 1500);
            }
        });

        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (messageInput.value.trim().length > 0 || selectedImageFile || activeEditingMsgId) {
                    chatForm.dispatchEvent(new Event('submit'));
                }
            }
        });
    }

    // Image upload handler
    if (attachBtn && imageInput) {
        attachBtn.addEventListener('click', () => imageInput.click());
        imageInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                selectedImageFile = this.files[0];
                const reader = new FileReader();
                reader.onload = function(e) {
                    imagePreviewImg.src = e.target.result;
                    imagePreviewBanner.classList.remove('d-none');
                    updateSendBtnState();
                };
                reader.readAsDataURL(selectedImageFile);
            }
        });
    }

    if (cancelImageBtn) {
        cancelImageBtn.addEventListener('click', () => {
            selectedImageFile = null;
            if (imageInput) imageInput.value = '';
            imagePreviewBanner.classList.add('d-none');
            updateSendBtnState();
        });
    }

    // Emoji Picker
    if (emojiToggleBtn && emojiPopup) {
        emojiToggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            emojiPopup.classList.toggle('d-none');
        });
        emojiPopup.querySelectorAll('.emoji-grid span').forEach(el => {
            el.addEventListener('click', function() {
                if (messageInput) {
                    messageInput.value += this.textContent;
                    messageInput.dispatchEvent(new Event('input'));
                    messageInput.focus();
                }
            });
        });
        document.addEventListener('click', () => emojiPopup.classList.add('d-none'));
    }

    // Reply Handler
    window.initiateReply = function(msgId, username, content) {
        if (!replyBanner) return;
        if (cancelEditBtn) cancelEditBtn.click();
        activeReplyMsg = msgId;
        if (replyToInput) replyToInput.value = msgId;
        if (replyToUserSpan) replyToUserSpan.textContent = username;
        if (replyToTextP) replyToTextP.textContent = content || 'Message';
        replyBanner.classList.remove('d-none');
        if (messageInput) messageInput.focus();
    };

    // Scroll to Replied Message & Highlight Pulse
    window.scrollToMessage = function(targetId) {
        if (!targetId) return;
        const targetEl = document.querySelector(`[data-msg-id="${targetId}"]`);
        if (targetEl) {
            targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            const bubble = targetEl.querySelector('.message-bubble');
            if (bubble) {
                bubble.classList.remove('message-highlight-pulse');
                void bubble.offsetWidth; // trigger reflow
                bubble.classList.add('message-highlight-pulse');
                setTimeout(() => bubble.classList.remove('message-highlight-pulse'), 1300);
            }
        }
    };

    if (cancelReplyBtn) {
        cancelReplyBtn.addEventListener('click', () => {
            activeReplyMsg = null;
            if (replyToInput) replyToInput.value = '';
            replyBanner.classList.add('d-none');
        });
    }

    // Edit Handler (Within 5 mins)
    window.initiateEdit = function(msgId, currentText) {
        if (!editBanner) return;
        if (cancelReplyBtn) cancelReplyBtn.click();
        activeEditingMsgId = msgId;
        if (editOriginalTextP) editOriginalTextP.textContent = currentText;
        editBanner.classList.remove('d-none');
        if (messageInput) {
            messageInput.value = currentText;
            messageInput.focus();
            messageInput.dispatchEvent(new Event('input'));
        }
        updateSendBtnState();
    };

    if (cancelEditBtn) {
        cancelEditBtn.addEventListener('click', () => {
            activeEditingMsgId = null;
            editBanner.classList.add('d-none');
            if (messageInput) {
                messageInput.value = '';
                messageInput.dispatchEvent(new Event('input'));
            }
            updateSendBtnState();
        });
    }

    // Safe Reply Handler (Retrieves message data by ID to eliminate syntax errors with special chars)
    window.safeInitiateReply = function(msgId) {
        if (!msgId) return;
        const numId = Number(msgId);
        const msg = window.zyraMessagesMap ? window.zyraMessagesMap.get(numId) : null;
        if (!msg) {
            const el = document.querySelector(`[data-msg-id="${numId}"]`);
            if (el) {
                const text = el.querySelector('.message-text-content')?.textContent || 'Message';
                const isSent = el.classList.contains('sent');
                initiateReply(numId, isSent ? 'You' : (activePartnerUsername || 'User'), text);
            }
            return;
        }
        let replySnippet = msg.content || '';
        if (!replySnippet) {
            if (msg.voice_note_url) replySnippet = '🎙️ Voice note';
            else if (msg.image_url) replySnippet = '📷 Photo';
            else if (msg.shared_post) replySnippet = '📎 Shared post';
            else replySnippet = '💬 Message';
        }
        const username = msg.sender_username || (msg.is_mine ? 'You' : (activePartnerUsername || 'User'));
        initiateReply(numId, username, replySnippet);
    };

    // Safe Edit Handler (Retrieves message by ID)
    window.safeInitiateEdit = function(msgId) {
        if (!msgId) return;
        const numId = Number(msgId);
        const msg = window.zyraMessagesMap ? window.zyraMessagesMap.get(numId) : null;
        if (!msg) {
            const el = document.querySelector(`[data-msg-id="${numId}"]`);
            const text = el?.querySelector('.message-text-content')?.textContent || '';
            initiateEdit(numId, text);
            return;
        }
        initiateEdit(numId, msg.content || '');
    };

    // Floating Reaction Picker Toggle
    window.toggleReactionPicker = function(msgId, event) {
        event.stopPropagation();
        document.querySelectorAll('.floating-reaction-tray').forEach(t => t.remove());

        const wrapper = document.querySelector(`[data-msg-id="${msgId}"]`);
        if (!wrapper) return;

        const tray = document.createElement('div');
        tray.className = 'floating-reaction-tray';
        tray.innerHTML = `
            <span class="reaction-opt" onclick="reactEmoji(${msgId}, '❤️')">❤️</span>
            <span class="reaction-opt" onclick="reactEmoji(${msgId}, '🔥')">🔥</span>
            <span class="reaction-opt" onclick="reactEmoji(${msgId}, '😂')">😂</span>
            <span class="reaction-opt" onclick="reactEmoji(${msgId}, '😮')">😮</span>
            <span class="reaction-opt" onclick="reactEmoji(${msgId}, '😢')">😢</span>
            <span class="reaction-opt" onclick="reactEmoji(${msgId}, '👏')">👏</span>
            <span class="reaction-opt" onclick="reactEmoji(${msgId}, '👍')">👍</span>
        `;
        wrapper.appendChild(tray);

        const closeTray = () => {
            tray.remove();
            document.removeEventListener('click', closeTray);
        };
        setTimeout(() => document.addEventListener('click', closeTray), 50);
    };

    // React Emoji Action (WebSocket first + REST fallback)
    window.reactEmoji = function(msgId, emoji) {
        if (isSocketOpen && chatSocket) {
            chatSocket.send(JSON.stringify({
                action: 'react_message',
                message_id: msgId,
                emoji: emoji
            }));
            return;
        }

        fetch(`/direct/api/react/${msgId}/`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `emoji=${encodeURIComponent(emoji)}`
        })
        .then(res => res.json())
        .then(data => {
            if (data.success && data.message) {
                updateMessageReactionsDOM(msgId, data.message.reactions);
            }
        });
    };

    function updateMessageReactionsDOM(msgId, reactions) {
        const wrapper = document.querySelector(`[data-msg-id="${msgId}"]`);
        if (!wrapper) return;
        const bubble = wrapper.querySelector('.message-bubble');
        if (!bubble) return;

        let reactionsContainer = bubble.querySelector('.message-reactions-container');
        if (!reactions || reactions.length === 0) {
            if (reactionsContainer) reactionsContainer.remove();
            wrapper.classList.remove('has-reactions');
            return;
        }

        if (!reactionsContainer) {
            reactionsContainer = document.createElement('div');
            reactionsContainer.className = 'message-reactions-container';
            bubble.appendChild(reactionsContainer);
        }

        wrapper.classList.add('has-reactions');

        const reactionCounts = {};
        reactions.forEach(r => {
            reactionCounts[r.emoji] = (reactionCounts[r.emoji] || 0) + 1;
        });

        reactionsContainer.innerHTML = Object.entries(reactionCounts).map(([emoji, count]) => `
            <span class="reaction-pill-badge" onclick="reactEmoji(${msgId}, '${emoji}')">
                ${emoji} ${count > 1 ? `<span class="reaction-count">${count}</span>` : ''}
            </span>
        `).join('');
    }

    // Append Message DOM
    function appendMessageDOM(msg, isOptimistic = false) {
        if (!msg) return;
        // Ignore ghost/empty messages
        if (!msg.content && !msg.image_url && !msg.voice_note_url && !msg.shared_post) {
            return;
        }

        const numId = msg.id ? Number(msg.id) : null;
        if (numId) {
            window.zyraMessagesMap.set(numId, msg);

            if (renderedMessageIds.has(numId)) {
                const existing = document.querySelector(`[data-msg-id="${numId}"]`);
                if (existing) {
                    const textDiv = existing.querySelector('.message-text-content');
                    if (textDiv && msg.content && textDiv.textContent !== msg.content) {
                        textDiv.textContent = msg.content;
                    }
                    const editedBadge = existing.querySelector('.message-edited-badge');
                    if (msg.is_edited && !editedBadge) {
                        const metaDiv = existing.querySelector('.message-meta');
                        if (metaDiv) {
                            const span = document.createElement('span');
                            span.className = 'message-edited-badge ms-1';
                            span.textContent = '(edited)';
                            metaDiv.prepend(span);
                        }
                    }
                    updateMessageReactionsDOM(numId, msg.reactions || []);
                }
                return;
            }

            renderedMessageIds.add(numId);
            if (numId > highestMessageId) highestMessageId = numId;
        }

        // Remove empty state banner if present
        const emptyIntro = document.getElementById('emptyChatIntro');
        if (emptyIntro) emptyIntro.remove();

        const msgWrapper = document.createElement('div');
        msgWrapper.className = `message-bubble-wrapper ${msg.is_mine ? 'sent' : 'received'}`;
        if (numId) msgWrapper.setAttribute('data-msg-id', numId);
        if (msg._tempId) msgWrapper.setAttribute('data-temp-id', msg._tempId);

        let html = '';

        // Received Avatar
        let avatarHtml = '';
        if (!msg.is_mine) {
            const fallbackInitial = (activePartnerUsername || 'U').charAt(0).toUpperCase();
            if (activePartnerAvatar) {
                avatarHtml = `
                    <div class="position-relative flex-shrink-0">
                        <img src="${activePartnerAvatar}" class="message-bubble-avatar" alt="${activePartnerUsername}" onerror="this.onerror=null; this.style.display='none'; if(this.nextElementSibling) this.nextElementSibling.classList.remove('d-none');">
                        <div class="message-bubble-avatar text-white fw-bold d-flex align-items-center justify-content-center d-none" style="background: var(--story-gradient); font-size: 0.75rem;">${fallbackInitial}</div>
                    </div>
                `;
            } else {
                avatarHtml = `<div class="message-bubble-avatar text-white fw-bold d-flex align-items-center justify-content-center" style="background: var(--story-gradient); font-size: 0.75rem;">${fallbackInitial}</div>`;
            }
        }

        // Action Toolbar (uses safe ID lookups to eliminate syntax errors)
        const toolbarHtml = `
            <div class="message-actions-toolbar">
                <button type="button" class="msg-action-btn" onclick="toggleReactionPicker(${numId || 0}, event)" title="React"><i class="bi bi-emoji-smile"></i></button>
                <button type="button" class="msg-action-btn" onclick="safeInitiateReply(${numId || 0})" title="Reply"><i class="bi bi-reply"></i></button>
                ${msg.is_mine && (msg.can_edit !== false) ? `<button type="button" class="msg-action-btn" onclick="safeInitiateEdit(${numId || 0})" title="Edit (within 5m)"><i class="bi bi-pencil"></i></button>` : ''}
                ${msg.is_mine ? `<button type="button" class="msg-action-btn" onclick="unsendMessage(${numId || 0})" title="Delete"><i class="bi bi-trash"></i></button>` : ''}
            </div>
        `;

        // Bubble Inner Content
        let bubbleHtml = `<div class="message-bubble" ondblclick="reactEmoji(${numId || 0}, '❤️')">`;

        // Reply quote (clickable to jump to replied message)
        if (msg.reply_to) {
            bubbleHtml += `
                <div class="message-reply-preview" onclick="scrollToMessage(${msg.reply_to.id})" title="Jump to replied message">
                    <strong class="d-block">${escapeHtml(msg.reply_to.sender_username)}</strong>
                    <span class="text-truncate d-block">${escapeHtml(msg.reply_to.content || 'Message')}</span>
                </div>
            `;
        }

        // Shared Post or Reel
        if (msg.shared_post) {
            const authorInitial = (msg.shared_post.username || 'U').charAt(0).toUpperCase();
            const isReel = Boolean(msg.shared_post.is_reel || msg.shared_post.video_url);
            bubbleHtml += `
                <a href="/post/${msg.shared_post.id}/" class="shared-post-card d-block mb-2 text-white text-decoration-none" style="background: rgba(0,0,0,0.38); border: 1px solid rgba(255,255,255,0.15); border-radius: 12px; padding: 8px; max-width: 260px;">
                    <div class="d-flex align-items-center gap-2 mb-2">
                        ${msg.shared_post.user_avatar ? `<img src="${msg.shared_post.user_avatar}" class="rounded-circle" style="width: 24px; height: 24px; object-fit: cover;">` : `<div class="rounded-circle text-white fw-bold d-flex align-items-center justify-content-center" style="width: 24px; height: 24px; font-size: 0.65rem; background: var(--story-gradient);">${authorInitial}</div>`}
                        <strong class="small text-truncate" style="font-size: 0.82rem;">${escapeHtml(msg.shared_post.username)}</strong>
                        ${isReel ? '<span class="badge bg-danger ms-auto" style="font-size: 0.62rem;"><i class="bi bi-play-btn-fill me-1"></i>Reel</span>' : ''}
                    </div>
                    ${msg.shared_post.video_url ? `
                        <div class="position-relative w-100 rounded mb-1 overflow-hidden" style="max-height: 180px; background: #000;">
                            <video src="${msg.shared_post.video_url}" class="w-100 h-100 rounded" style="max-height: 180px; object-fit: cover;" muted loop playsinline preload="metadata" onmouseenter="this.play().catch(()=>{})" onmouseleave="this.pause()"></video>
                            <div class="position-absolute top-50 start-50 translate-middle rounded-circle d-flex align-items-center justify-content-center shadow" style="width: 38px; height: 38px; background: rgba(0,0,0,0.65); color: #fff; pointer-events: none;">
                                <i class="bi bi-play-fill fs-5" style="margin-left: 2px;"></i>
                            </div>
                        </div>
                    ` : (msg.shared_post.image_url ? `<img src="${msg.shared_post.image_url}" class="w-100 rounded mb-1 shadow-sm" style="max-height: 180px; object-fit: cover;">` : '')}
                    ${msg.shared_post.caption ? `<p class="small text-white-50 mb-0 text-truncate" style="font-size: 0.78rem;">${escapeHtml(msg.shared_post.caption)}</p>` : ''}
                </a>
            `;
        }

        // Image
        if (msg.image_url) {
            bubbleHtml += `<img src="${msg.image_url}" class="message-attached-img mb-1" onclick="openLightbox('${msg.image_url}')">`;
        }

        // Voice Note Audio Player Bubble
        if (msg.voice_note_url) {
            bubbleHtml += `
                <div class="voice-note-bubble d-flex align-items-center gap-2 py-1 mb-1">
                    <button type="button" class="voice-play-toggle-btn btn btn-sm rounded-circle d-flex align-items-center justify-content-center p-0" data-audio-src="${msg.voice_note_url}" style="width: 36px; height: 36px; background: rgba(255,255,255,0.2); border: none; color: #fff; flex-shrink: 0;">
                        <i class="bi bi-play-fill fs-5" style="margin-left: 2px;"></i>
                    </button>
                    <div class="voice-waveform-container flex-grow-1 position-relative" style="cursor: pointer;">
                        <div class="voice-waveform-bars d-flex align-items-center gap-1" style="height: 20px;">
                            ${generateWaveformBars()}
                        </div>
                        <div class="d-flex justify-content-between text-white-50 mt-1" style="font-size: 0.70rem;">
                            <span class="voice-current-time">0:00</span>
                            <span class="voice-total-duration">--:--</span>
                        </div>
                    </div>
                    <i class="bi bi-mic-fill text-white-50 small ms-1" style="font-size: 0.85rem;"></i>
                </div>
            `;
        }

        // Text
        if (msg.content) {
            bubbleHtml += `<div class="message-text-content">${escapeHtml(msg.content)}</div>`;
        }

        // Meta
        bubbleHtml += `
            <div class="message-meta">
                ${msg.is_edited ? '<span class="message-edited-badge me-1">(edited)</span>' : ''}
                ${msg.created_at_time || 'Just now'} ${msg.is_mine && msg.is_read ? '• Seen' : ''}
            </div>
        </div>`;

        if (msg.is_mine) {
            msgWrapper.innerHTML = bubbleHtml + toolbarHtml;
        } else {
            msgWrapper.innerHTML = avatarHtml + bubbleHtml + toolbarHtml;
        }

        // Append reactions if any
        if (msg.reactions && msg.reactions.length > 0) {
            let reactionsContainer = document.createElement('div');
            reactionsContainer.className = 'message-reactions-container';
            const reactionCounts = {};
            msg.reactions.forEach(r => {
                reactionCounts[r.emoji] = (reactionCounts[r.emoji] || 0) + 1;
            });
            let pillHtml = Object.entries(reactionCounts).map(([emoji, count]) => `
                <span class="reaction-pill">${emoji}${count > 1 ? ` ${count}` : ''}</span>
            `).join('');
            reactionsContainer.innerHTML = pillHtml;
            const bubbleEl = msgWrapper.querySelector('.message-bubble');
            if (bubbleEl) bubbleEl.appendChild(reactionsContainer);
            msgWrapper.classList.add('has-reactions');
        }

        if (messagesContainer) {
            messagesContainer.appendChild(msgWrapper);
        }
    }

    // Send Form Submission (WebSocket + REST fallback)
    if (chatForm && activeConvId) {
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const textContent = messageInput ? messageInput.value.trim() : '';

            // If Editing Message:
            if (activeEditingMsgId) {
                if (!textContent) return;
                if (isSocketOpen && chatSocket) {
                    chatSocket.send(JSON.stringify({
                        action: 'edit_message',
                        message_id: activeEditingMsgId,
                        content: textContent
                    }));
                    if (cancelEditBtn) cancelEditBtn.click();
                    return;
                }

                fetch(`/direct/api/edit/${activeEditingMsgId}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken(),
                        'X-Requested-With': 'XMLHttpRequest',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: `content=${encodeURIComponent(textContent)}`
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success && data.message) {
                        const el = document.querySelector(`[data-msg-id="${activeEditingMsgId}"]`);
                        if (el) {
                            const textDiv = el.querySelector('.message-text-content');
                            if (textDiv) textDiv.textContent = data.message.content;
                            const metaDiv = el.querySelector('.message-meta');
                            if (metaDiv && !metaDiv.querySelector('.message-edited-badge')) {
                                const span = document.createElement('span');
                                span.className = 'message-edited-badge me-1';
                                span.textContent = '(edited)';
                                metaDiv.prepend(span);
                            }
                        }
                    } else if (data.error) {
                        window.showToast && window.showToast(data.error, 'error');
                    }
                })
                .finally(() => {
                    if (cancelEditBtn) cancelEditBtn.click();
                });
                return;
            }

            if (!textContent && !selectedImageFile) return;

            // If text message with WebSocket open:
            if (isSocketOpen && chatSocket && !selectedImageFile) {
                chatSocket.send(JSON.stringify({
                    action: 'send_message',
                    content: textContent,
                    reply_to_id: activeReplyMsg
                }));

                if (messageInput) {
                    messageInput.value = '';
                    messageInput.style.height = 'auto';
                }
                if (cancelReplyBtn) cancelReplyBtn.click();
                updateSendBtnState();
                return;
            }

            // Fallback & Multipart Form for Images
            const tempId = 'temp_' + Date.now() + '_' + Math.floor(Math.random() * 1000);
            const optimisticMsg = {
                id: null,
                _tempId: tempId,
                content: textContent,
                is_mine: true,
                sender_username: currentUsername,
                created_at_time: 'Just now',
                image_url: selectedImageFile ? imagePreviewImg.src : null,
                reply_to: activeReplyMsg ? { sender_username: replyToUserSpan.textContent, content: replyToTextP.textContent } : null
            };
            appendMessageDOM(optimisticMsg, true);
            scrollToBottom(true);

            const formData = new FormData();
            formData.append('content', textContent);
            if (selectedImageFile) formData.append('image', selectedImageFile);
            if (activeReplyMsg) formData.append('reply_to_id', activeReplyMsg);

            if (messageInput) {
                messageInput.value = '';
                messageInput.style.height = 'auto';
            }
            if (cancelImageBtn) cancelImageBtn.click();
            if (cancelReplyBtn) cancelReplyBtn.click();
            updateSendBtnState();

            fetch(`/direct/api/send/${activeConvId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrfToken() },
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.success && data.message) {
                    const realMsg = data.message;
                    renderedMessageIds.add(realMsg.id);
                    highestMessageId = Math.max(highestMessageId, realMsg.id);
                    window.zyraMessagesMap.set(Number(realMsg.id), realMsg);

                    const tempEl = document.querySelector(`[data-temp-id="${tempId}"]`);
                    if (tempEl) {
                        tempEl.setAttribute('data-msg-id', realMsg.id);
                        tempEl.removeAttribute('data-temp-id');
                        const toolbar = tempEl.querySelector('.message-actions-toolbar');
                        if (toolbar) {
                            toolbar.innerHTML = `
                                <button type="button" class="msg-action-btn" onclick="toggleReactionPicker(${realMsg.id}, event)" title="React"><i class="bi bi-emoji-smile"></i></button>
                                <button type="button" class="msg-action-btn" onclick="safeInitiateReply(${realMsg.id})" title="Reply"><i class="bi bi-reply"></i></button>
                                <button type="button" class="msg-action-btn" onclick="safeInitiateEdit(${realMsg.id})" title="Edit (within 5m)"><i class="bi bi-pencil"></i></button>
                                <button type="button" class="msg-action-btn" onclick="unsendMessage(${realMsg.id})" title="Delete"><i class="bi bi-trash"></i></button>
                            `;
                        }
                        const bubble = tempEl.querySelector('.message-bubble');
                        if (bubble) {
                            bubble.setAttribute('ondblclick', `reactEmoji(${realMsg.id}, '❤️')`);
                        }
                    }
                }
            });
        });
    }

    // Quick Send Heart ❤️
    window.sendQuickHeart = function() {
        if (!activeConvId) return;

        if (isSocketOpen && chatSocket) {
            chatSocket.send(JSON.stringify({
                action: 'send_message',
                content: '❤️'
            }));
            return;
        }

        const formData = new FormData();
        formData.append('content', '❤️');

        const heartTempId = 'temp_' + Date.now();
        appendMessageDOM({
            id: null,
            _tempId: heartTempId,
            content: '❤️',
            is_mine: true,
            sender_username: currentUsername,
            created_at_time: 'Just now'
        }, true);
        scrollToBottom(true);

        fetch(`/direct/api/send/${activeConvId}/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.success && data.message) {
                const realMsg = data.message;
                renderedMessageIds.add(realMsg.id);
                highestMessageId = Math.max(highestMessageId, realMsg.id);
                window.zyraMessagesMap.set(Number(realMsg.id), realMsg);

                const tempEl = document.querySelector(`[data-temp-id="${heartTempId}"]`);
                if (tempEl) {
                    tempEl.setAttribute('data-msg-id', realMsg.id);
                    tempEl.removeAttribute('data-temp-id');
                    const toolbar = tempEl.querySelector('.message-actions-toolbar');
                    if (toolbar) {
                        toolbar.innerHTML = `
                            <button type="button" class="msg-action-btn" onclick="toggleReactionPicker(${realMsg.id}, event)" title="React"><i class="bi bi-emoji-smile"></i></button>
                            <button type="button" class="msg-action-btn" onclick="safeInitiateReply(${realMsg.id})" title="Reply"><i class="bi bi-reply"></i></button>
                            <button type="button" class="msg-action-btn" onclick="unsendMessage(${realMsg.id})" title="Delete"><i class="bi bi-trash"></i></button>
                        `;
                    }
                }
            }
        });
    };

    // Background Hybrid Polling (Acts as fallback when WS reconnecting)
    function pollNewMessages() {
        if (!activeConvId || isPolling || isSocketOpen) return;
        isPolling = true;

        fetch(`/direct/api/messages/${activeConvId}/?since_id=${highestMessageId}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(res => res.json())
        .then(data => {
            if (data.success && data.messages && data.messages.length > 0) {
                let hasNew = false;
                data.messages.forEach(msg => {
                    if (!renderedMessageIds.has(msg.id)) {
                        appendMessageDOM(msg, false);
                        hasNew = true;
                    }
                });
                if (hasNew) scrollToBottom(true);
            }
        })
        .finally(() => { isPolling = false; });
    }

    if (activeConvId) {
        setInterval(pollNewMessages, 2500);
    }

    // Unsend Message (WebSocket + REST fallback)
    window.unsendMessage = function(msgId) {
        if (!msgId) return;
        window.showConfirmPopup({
            title: 'Unsend Message?',
            message: 'This will remove the message for everyone in this chat.',
            confirmText: 'Unsend',
            confirmType: 'danger',
            icon: 'bi-trash3-fill',
            onConfirm: () => {
                if (isSocketOpen && chatSocket) {
                    chatSocket.send(JSON.stringify({
                        action: 'unsend_message',
                        message_id: msgId
                    }));
                    return;
                }

                fetch(`/direct/api/unsend/${msgId}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        const el = document.querySelector(`[data-msg-id="${msgId}"]`);
                        if (el) {
                            el.style.opacity = '0';
                            setTimeout(() => el.remove(), 200);
                        }
                    } else if (data.error) {
                        window.showToast && window.showToast(data.error, 'error');
                    }
                })
                .catch(() => {
                    window.showToast && window.showToast('Network error unsending message.', 'error');
                });
            }
        });
    };

    // Image Lightbox
    window.openLightbox = function(url) {
        const modalEl = document.getElementById('imageLightboxModal');
        const img = document.getElementById('lightboxImg');
        if (modalEl && img) {
            img.src = url;
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    };

    // Details Drawer Toggle
    if (toggleDetailsBtn && chatDetailsDrawer) {
        toggleDetailsBtn.addEventListener('click', () => {
            chatDetailsDrawer.classList.toggle('d-none');
        });
    }
    if (closeDetailsBtn && chatDetailsDrawer) {
        closeDetailsBtn.addEventListener('click', () => {
            chatDetailsDrawer.classList.add('d-none');
        });
    }

    // Hide Chat
    window.confirmHideChat = function() {
        if (!activeConvId) return;
        window.showConfirmPopup({
            title: 'Hide Conversation?',
            message: 'This conversation will be hidden from your inbox until a new message is received.',
            confirmText: 'Hide',
            confirmType: 'warning',
            icon: 'bi-archive-fill',
            onConfirm: () => {
                fetch(`/direct/api/hide/${activeConvId}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        window.location.href = '/direct/';
                    }
                });
            }
        });
    };

    // Conversations Search Client-Side Filter
    if (convSearchInput) {
        convSearchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase().trim();
            if (clearConvSearch) {
                clearConvSearch.classList.toggle('d-none', query.length === 0);
            }
            document.querySelectorAll('.conversation-item').forEach(item => {
                const username = item.getAttribute('data-username') || '';
                item.style.display = username.includes(query) ? 'flex' : 'none';
            });
        });

        if (clearConvSearch) {
            clearConvSearch.addEventListener('click', () => {
                convSearchInput.value = '';
                convSearchInput.dispatchEvent(new Event('input'));
                convSearchInput.focus();
            });
        }
    }

    // New Chat User Search Modal
    let searchTimeout = null;
    if (userSearchModalInput && userSearchResults) {
        userSearchModalInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();
            if (!query) {
                userSearchResults.innerHTML = '<p class="text-white-50 small text-center py-4 mb-0">Type a username to start chatting.</p>';
                return;
            }

            searchTimeout = setTimeout(() => {
                fetch(`/direct/api/search-users/?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.users && data.users.length > 0) {
                        userSearchResults.innerHTML = data.users.map(u => `
                            <a href="/direct/t/${u.username}/" class="d-flex align-items-center justify-content-between p-2 rounded text-decoration-none" style="transition: background 0.15s ease;" onmouseover="this.style.background='#262626'" onmouseout="this.style.background='transparent'">
                                <div class="d-flex align-items-center gap-3">
                                    ${u.profile_pic ? `<img src="${u.profile_pic}" class="rounded-circle" style="width: 40px; height: 40px; object-fit: cover;">` : `<div class="rounded-circle text-white fw-bold d-flex align-items-center justify-content-center" style="width: 40px; height: 40px; background: var(--story-gradient);">${u.username.charAt(0).toUpperCase()}</div>`}
                                    <div>
                                        <div class="fw-bold text-white small">${u.username}</div>
                                        <div class="text-white-50" style="font-size: 0.75rem;">${u.first_name || ''} ${u.last_name || ''}</div>
                                    </div>
                                </div>
                                <button class="btn btn-sm btn-primary rounded-pill px-3 py-1 fw-semibold" style="font-size: 0.8rem;">Chat</button>
                            </a>
                        `).join('');
                    } else {
                        userSearchResults.innerHTML = '<p class="text-white-50 small text-center py-4 mb-0">No users found.</p>';
                    }
                });
            }, 250);
        });
    }

    // =========================================================================
    // VOICE NOTE RECORDING, PREVIEW & PLAYBACK ENGINE
    // =========================================================================
    async function startVoiceRecording(e) {
        if (e && e.preventDefault) e.preventDefault();
        if (e && e.stopPropagation) e.stopPropagation();

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            window.showToast && window.showToast('Voice recording requires microphone permissions and an HTTPS connection.', 'warning');
            return;
        }

        if (typeof MediaRecorder === 'undefined') {
            window.showToast && window.showToast('Audio recording is not supported in this browser.', 'warning');
            return;
        }

        try {
            audioStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            audioChunks = [];

            // Probe best supported container
            let chosenMime = '';
            const candidates = [
                'audio/webm;codecs=opus',
                'audio/webm',
                'audio/mp4',
                'audio/aac',
                'audio/ogg;codecs=opus',
                'audio/ogg',
                'audio/wav'
            ];
            for (const c of candidates) {
                if (MediaRecorder.isTypeSupported(c)) {
                    chosenMime = c;
                    break;
                }
            }

            const recorderOptions = chosenMime ? { mimeType: chosenMime } : undefined;
            mediaRecorder = recorderOptions ? new MediaRecorder(audioStream, recorderOptions) : new MediaRecorder(audioStream);

            mediaRecorder.ondataavailable = function(evt) {
                if (evt.data && evt.data.size > 0) {
                    audioChunks.push(evt.data);
                }
            };

            mediaRecorder.onstop = function() {
                // Safely release media tracks after recording flushes
                if (audioStream) {
                    audioStream.getTracks().forEach(t => t.stop());
                    audioStream = null;
                }

                if (audioChunks.length > 0) {
                    const actualType = mediaRecorder.mimeType || chosenMime || 'audio/webm';
                    recordedAudioBlob = new Blob(audioChunks, { type: actualType });
                    setupVoicePreview(recordedAudioBlob);
                } else {
                    window.showToast && window.showToast('Voice note was too short or empty. Please try again.', 'warning');
                    cancelVoiceRecording();
                }
            };

            // Timeslice of 200ms ensures steady chunk accumulation
            mediaRecorder.start(200);

            // Update UI to recording state
            recordSeconds = 0;
            if (voiceRecordTimer) voiceRecordTimer.textContent = '0:00';
            if (recordTimerInterval) clearInterval(recordTimerInterval);
            recordTimerInterval = setInterval(() => {
                recordSeconds++;
                if (voiceRecordTimer) voiceRecordTimer.textContent = formatAudioTime(recordSeconds);
            }, 1000);

            if (normalInputPill) normalInputPill.classList.add('d-none');
            if (voicePreviewBar) voicePreviewBar.classList.add('d-none');
            if (voiceRecordingBar) voiceRecordingBar.classList.remove('d-none');
        } catch (err) {
            console.error('Microphone access error:', err);
            if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
                window.showToast && window.showToast('Microphone permission denied. Please allow microphone in your browser settings.', 'warning');
            } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
                window.showToast && window.showToast('No microphone found on this device.', 'warning');
            } else if (err.name === 'NotReadableError') {
                window.showToast && window.showToast('Microphone is busy or in use by another app.', 'warning');
            } else {
                window.showToast && window.showToast('Unable to access microphone: ' + (err.message || 'error'), 'warning');
            }
        }
    }

    function stopVoiceRecording(e) {
        if (e && e.preventDefault) e.preventDefault();
        if (recordTimerInterval) {
            clearInterval(recordTimerInterval);
            recordTimerInterval = null;
        }
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            try {
                if (typeof mediaRecorder.requestData === 'function') {
                    mediaRecorder.requestData();
                }
            } catch (err) {}
            mediaRecorder.stop();
        }
    }

    function cancelVoiceRecording(e) {
        if (e && e.preventDefault) e.preventDefault();
        if (recordTimerInterval) {
            clearInterval(recordTimerInterval);
            recordTimerInterval = null;
        }
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.onstop = null;
            mediaRecorder.stop();
        }
        if (audioStream) {
            audioStream.getTracks().forEach(t => t.stop());
            audioStream = null;
        }
        audioChunks = [];
        recordedAudioBlob = null;
        if (voiceRecordingBar) voiceRecordingBar.classList.add('d-none');
        if (voicePreviewBar) voicePreviewBar.classList.add('d-none');
        if (normalInputPill) normalInputPill.classList.remove('d-none');
    }

    function setupVoicePreview(blob) {
        if (voiceRecordingBar) voiceRecordingBar.classList.add('d-none');
        if (normalInputPill) normalInputPill.classList.add('d-none');
        if (voicePreviewBar) voicePreviewBar.classList.remove('d-none');

        if (previewAudio) {
            previewAudio.pause();
            previewAudio = null;
        }

        const audioUrl = URL.createObjectURL(blob);
        previewAudio = new Audio(audioUrl);
        if (previewPlayIcon) previewPlayIcon.className = 'bi bi-play-fill fs-5';
        if (previewVoiceSeekBar) previewVoiceSeekBar.value = 0;
        if (previewVoiceCurrentTime) previewVoiceCurrentTime.textContent = '0:00';
        if (previewVoiceTotalDuration) previewVoiceTotalDuration.textContent = formatAudioTime(recordSeconds || 0);

        previewAudio.addEventListener('loadedmetadata', function() {
            if (previewAudio.duration && isFinite(previewAudio.duration)) {
                if (previewVoiceTotalDuration) previewVoiceTotalDuration.textContent = formatAudioTime(previewAudio.duration);
            }
        });

        previewAudio.addEventListener('timeupdate', function() {
            if (previewAudio.duration && isFinite(previewAudio.duration)) {
                const progress = (previewAudio.currentTime / previewAudio.duration) * 100;
                if (previewVoiceSeekBar) previewVoiceSeekBar.value = progress;
                if (previewVoiceCurrentTime) previewVoiceCurrentTime.textContent = formatAudioTime(previewAudio.currentTime);
            }
        });

        previewAudio.addEventListener('ended', function() {
            if (previewPlayIcon) previewPlayIcon.className = 'bi bi-play-fill fs-5';
            if (previewVoiceSeekBar) previewVoiceSeekBar.value = 0;
            if (previewVoiceCurrentTime) previewVoiceCurrentTime.textContent = '0:00';
        });

        previewAudio.addEventListener('error', function(err) {
            console.warn('Audio preview note:', err);
        });
    }

    if (micBtn) {
        micBtn.addEventListener('click', startVoiceRecording);
    }
    if (stopVoiceRecordBtn) {
        stopVoiceRecordBtn.addEventListener('click', stopVoiceRecording);
    }
    if (cancelVoiceRecordBtn) {
        cancelVoiceRecordBtn.addEventListener('click', cancelVoiceRecording);
    }
    if (discardVoicePreviewBtn) {
        discardVoicePreviewBtn.addEventListener('click', function(e) {
            if (e && e.preventDefault) e.preventDefault();
            if (previewAudio) {
                previewAudio.pause();
                previewAudio = null;
            }
            recordedAudioBlob = null;
            if (voicePreviewBar) voicePreviewBar.classList.add('d-none');
            if (voiceRecordingBar) voiceRecordingBar.classList.add('d-none');
            if (normalInputPill) normalInputPill.classList.remove('d-none');
        });
    }

    if (previewVoicePlayBtn) {
        previewVoicePlayBtn.addEventListener('click', function(e) {
            if (e && e.preventDefault) e.preventDefault();
            if (!previewAudio) return;
            if (previewAudio.paused) {
                previewAudio.play().then(() => {
                    if (previewPlayIcon) previewPlayIcon.className = 'bi bi-pause-fill fs-5';
                }).catch(err => {
                    console.error('Preview play error:', err);
                    if (previewPlayIcon) previewPlayIcon.className = 'bi bi-play-fill fs-5';
                });
            } else {
                previewAudio.pause();
                if (previewPlayIcon) previewPlayIcon.className = 'bi bi-play-fill fs-5';
            }
        });
    }

    if (previewVoiceSeekBar) {
        previewVoiceSeekBar.addEventListener('input', function() {
            if (!previewAudio || !previewAudio.duration || !isFinite(previewAudio.duration)) return;
            previewAudio.currentTime = (this.value / 100) * previewAudio.duration;
        });
    }

    if (confirmSendVoiceBtn) {
        confirmSendVoiceBtn.addEventListener('click', function(e) {
            if (e && e.preventDefault) e.preventDefault();
            const convId = activeConvId || (window.activeConversationId || '');
            if (!convId) {
                window.showToast && window.showToast('Please select a conversation first.', 'warning');
                return;
            }
            if (!recordedAudioBlob || recordedAudioBlob.size === 0) {
                window.showToast && window.showToast('No audio recorded to send.', 'warning');
                return;
            }
            if (previewAudio) previewAudio.pause();

            confirmSendVoiceBtn.disabled = true;
            confirmSendVoiceBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span> Sending...';

            let ext = 'webm';
            const blobType = (recordedAudioBlob.type || '').toLowerCase();
            if (blobType.includes('mp4') || blobType.includes('m4a') || blobType.includes('aac')) {
                ext = 'm4a';
            } else if (blobType.includes('ogg')) {
                ext = 'ogg';
            } else if (blobType.includes('wav')) {
                ext = 'wav';
            } else {
                ext = 'webm';
            }

            const formData = new FormData();
            formData.append('voice_note', recordedAudioBlob, `voice_note_${Date.now()}.${ext}`);
            if (activeReplyMsg) {
                formData.append('reply_to_id', activeReplyMsg);
            }

            fetch(`/direct/api/send/${convId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.success && data.message) {
                    appendMessageDOM(data.message);
                    scrollToBottom(true);
                    if (discardVoicePreviewBtn) discardVoicePreviewBtn.click();
                    if (cancelReplyBtn) cancelReplyBtn.click();
                    window.showToast && window.showToast('Voice message sent!', 'success');
                } else {
                    window.showToast && window.showToast(data.error || 'Failed to send voice note.', 'error');
                }
            })
            .catch(err => {
                console.error('Error sending voice note:', err);
                window.showToast && window.showToast('Network error sending voice note.', 'error');
            })
            .finally(() => {
                confirmSendVoiceBtn.disabled = false;
                confirmSendVoiceBtn.innerHTML = '<i class="bi bi-send-fill text-white small"></i> Send';
            });
        });
    }

    // Chat Message Audio Playback Event Delegation
    let currentPlayingAudio = null;
    let currentPlayingBtn = null;
    let currentPlayingBubble = null;

    if (messagesContainer) {
        messagesContainer.addEventListener('click', function(e) {
            const playBtn = e.target.closest('.voice-play-toggle-btn');
            const bubble = e.target.closest('.voice-note-bubble');

            if (!playBtn || !bubble) return;
            const audioSrc = playBtn.getAttribute('data-audio-src');
            if (!audioSrc) {
                window.showToast && window.showToast('Audio file not found.', 'warning');
                return;
            }

            if (currentPlayingAudio && currentPlayingBtn === playBtn) {
                if (currentPlayingAudio.paused) {
                    currentPlayingAudio.play().then(() => {
                        playBtn.querySelector('i').className = 'bi bi-pause-fill fs-5';
                    }).catch(err => {
                        console.error('Play resume error:', err);
                        playBtn.querySelector('i').className = 'bi bi-play-fill fs-5';
                    });
                } else {
                    currentPlayingAudio.pause();
                    playBtn.querySelector('i').className = 'bi bi-play-fill fs-5';
                }
                return;
            }

            // Pause previous playing audio if any
            if (currentPlayingAudio) {
                currentPlayingAudio.pause();
                if (currentPlayingBtn) {
                    currentPlayingBtn.querySelector('i').className = 'bi bi-play-fill fs-5';
                }
                if (currentPlayingBubble) {
                    currentPlayingBubble.querySelectorAll('.voice-waveform-bar').forEach(b => b.classList.remove('played'));
                }
            }

            // Start new audio playback
            currentPlayingAudio = new Audio(audioSrc);
            currentPlayingBtn = playBtn;
            currentPlayingBubble = bubble;
            playBtn.querySelector('i').className = 'bi bi-pause-fill fs-5';

            const currentTimeSpan = bubble.querySelector('.voice-current-time');
            const totalDurationSpan = bubble.querySelector('.voice-total-duration');
            const bars = bubble.querySelectorAll('.voice-waveform-bar');
            const waveformContainer = bubble.querySelector('.voice-waveform-container');

            if (waveformContainer && !waveformContainer._hasSeekListener) {
                waveformContainer._hasSeekListener = true;
                waveformContainer.addEventListener('click', function(evt) {
                    if (evt.target.closest('.voice-play-toggle-btn')) return;
                    if (currentPlayingAudio && currentPlayingBtn === playBtn && currentPlayingAudio.duration && isFinite(currentPlayingAudio.duration)) {
                        const rect = waveformContainer.getBoundingClientRect();
                        const clickX = evt.clientX - rect.left;
                        const pct = Math.max(0, Math.min(1, clickX / rect.width));
                        currentPlayingAudio.currentTime = pct * currentPlayingAudio.duration;
                    }
                });
            }

            const updateDurationDisplay = () => {
                if (currentPlayingAudio && currentPlayingAudio.duration && isFinite(currentPlayingAudio.duration)) {
                    if (totalDurationSpan) totalDurationSpan.textContent = formatAudioTime(currentPlayingAudio.duration);
                }
            };

            currentPlayingAudio.addEventListener('loadedmetadata', updateDurationDisplay);
            currentPlayingAudio.addEventListener('durationchange', updateDurationDisplay);

            currentPlayingAudio.addEventListener('timeupdate', function() {
                if (currentPlayingAudio.duration && isFinite(currentPlayingAudio.duration)) {
                    if (currentTimeSpan) currentTimeSpan.textContent = formatAudioTime(currentPlayingAudio.currentTime);
                    const progress = currentPlayingAudio.currentTime / currentPlayingAudio.duration;
                    const playedCount = Math.floor(progress * bars.length);
                    bars.forEach((bar, idx) => {
                        bar.classList.toggle('played', idx < playedCount);
                    });
                }
            });

            currentPlayingAudio.addEventListener('ended', function() {
                playBtn.querySelector('i').className = 'bi bi-play-fill fs-5';
                if (currentTimeSpan) currentTimeSpan.textContent = '0:00';
                bars.forEach(b => b.classList.remove('played'));
                currentPlayingAudio = null;
                currentPlayingBtn = null;
                currentPlayingBubble = null;
            });

            currentPlayingAudio.play().catch(err => {
                console.error('Audio playback error:', err);
                playBtn.querySelector('i').className = 'bi bi-play-fill fs-5';
                window.showToast && window.showToast('Unable to stream voice note. Please try again.', 'warning');
            });
        });
    }

    // =========================================================================
    // THEMES & CUSTOM WALLPAPER CLIENT ENGINE
    // =========================================================================
    const CHAT_THEMES = [
        { key: 'default', name: 'Classic Dark', previewGradient: 'linear-gradient(135deg, #000000, #3797f0)', desc: 'OLED Pitch Black & Accent Blue' },
        { key: 'cyberpunk', name: 'Cyberpunk Neon', previewGradient: 'linear-gradient(135deg, #f72585, #7209b7)', desc: 'Vibrant Magenta & Violet Electric' },
        { key: 'sunset', name: 'Sunset Romance', previewGradient: 'linear-gradient(135deg, #ff0844, #ffb199)', desc: 'Warm Peach & Sunset Coral' },
        { key: 'ocean', name: 'Ocean Breeze', previewGradient: 'linear-gradient(135deg, #00c6ff, #0072ff)', desc: 'Deep Sea Blue & Aquamarine' },
        { key: 'aurora', name: 'Emerald Aurora', previewGradient: 'linear-gradient(135deg, #11998e, #38ef7d)', desc: 'Northern Lights Emerald Glow' },
        { key: 'galaxy', name: 'Cosmic Galaxy', previewGradient: 'linear-gradient(135deg, #654ea3, #eaafc8)', desc: 'Nebula Violet & Stardust Lilac' },
        { key: 'gold', name: 'Golden Royalty', previewGradient: 'linear-gradient(135deg, #f12711, #f5af19)', desc: 'Champagne Gold & Amber Flame' },
        { key: 'cherry', name: 'Cherry Blossom', previewGradient: 'linear-gradient(135deg, #ff758c, #ff7eb3)', desc: 'Sakura Petal & Soft Rose' },
        { key: 'lofi', name: 'Lofi Twilight', previewGradient: 'linear-gradient(135deg, #4b6cb7, #182848)', desc: 'Retro Slate & Midnight Indigo' },
        { key: 'matrix', name: 'Matrix Terminal', previewGradient: 'linear-gradient(135deg, #00b09b, #96c93d)', desc: 'Cyber Phosphor & Lime Green' },
        { key: 'crimson', name: 'Crimson Flame', previewGradient: 'linear-gradient(135deg, #f85032, #e73827)', desc: 'Fiery Ruby & Scarlet Glow' },
        { key: 'candy', name: 'Cotton Candy', previewGradient: 'linear-gradient(135deg, #ee9ca7, #ffdde1)', desc: 'Bubblegum Pink & Pastel Sky' },
        { key: 'tokyo', name: 'Tokyo Night', previewGradient: 'linear-gradient(135deg, #b224ef, #7579ff)', desc: 'Shinjuku Ultraviolet & Purple' },
        { key: 'forest', name: 'Misty Forest', previewGradient: 'linear-gradient(135deg, #134e5e, #71b280)', desc: 'Evergreen Pine & Sage Jade' },
        { key: 'midnight', name: 'Midnight Sapphire', previewGradient: 'linear-gradient(135deg, #1e3c72, #2a5298)', desc: 'Royal Navy & Sapphire Depths' }
    ];

    let currentThemeKey = config.currentThemeKey || 'default';
    let currentCustomThemeImage = config.currentCustomThemeImage || '';

    const chatWindow = document.getElementById('directChatWindow');
    const themePresetsGrid = document.getElementById('themePresetsGrid');
    const customWallpaperInput = document.getElementById('customWallpaperInput');
    const customWallpaperFileName = document.getElementById('customWallpaperFileName');
    const applyWallpaperBtn = document.getElementById('applyWallpaperBtn');
    const customWallpaperForm = document.getElementById('customWallpaperForm');
    const currentThemeNameDisplay = document.getElementById('currentThemeNameDisplay');

    function renderThemePresetCards() {
        if (!themePresetsGrid) return;
        themePresetsGrid.innerHTML = CHAT_THEMES.map(theme => `
            <div class="col-12 col-sm-6">
                <div class="theme-preset-card ${currentThemeKey === theme.key ? 'active' : ''}" onclick="selectChatTheme('${theme.key}')" data-theme-key="${theme.key}">
                    <div class="theme-preview-circle shadow-sm" style="background: ${theme.previewGradient};"></div>
                    <div class="flex-grow-1 overflow-hidden">
                        <strong class="d-block text-white small text-truncate">${theme.name}</strong>
                        <span class="text-white-50 small d-block text-truncate" style="font-size: 0.72rem;">${theme.desc}</span>
                    </div>
                    ${currentThemeKey === theme.key ? '<i class="bi bi-check-circle-fill text-primary ms-auto fs-5"></i>' : ''}
                </div>
            </div>
        `).join('');
    }

    function applyChatThemeDOM(themeKey, customImageUrl = null) {
        if (!chatWindow || !messagesContainer) return;

        // Remove all previous theme classes
        const themeClasses = Array.from(chatWindow.classList).filter(c => c.startsWith('theme-'));
        themeClasses.forEach(c => chatWindow.classList.remove(c));

        chatWindow.classList.add(`theme-${themeKey}`);
        chatWindow.dataset.theme = themeKey;
        currentThemeKey = themeKey;

        if (themeKey === 'custom' && customImageUrl) {
            messagesContainer.style.backgroundImage = `url('${customImageUrl}')`;
            if (currentThemeNameDisplay) currentThemeNameDisplay.textContent = 'Custom Wallpaper';
        } else {
            messagesContainer.style.backgroundImage = '';
            const t = CHAT_THEMES.find(th => th.key === themeKey);
            if (currentThemeNameDisplay) currentThemeNameDisplay.textContent = t ? t.name : 'Preset';
        }

        renderThemePresetCards();
    }

    window.selectChatTheme = async function(themeKey) {
        if (!activeConvId) return;

        // Apply immediately in local DOM for zero latency
        applyChatThemeDOM(themeKey, null);

        // Close modal
        const modalEl = document.getElementById('chatThemeModal');
        if (modalEl && bootstrap.Modal.getInstance(modalEl)) {
            bootstrap.Modal.getInstance(modalEl).hide();
        }

        // Try WebSocket first
        if (isSocketOpen && chatSocket) {
            chatSocket.send(JSON.stringify({
                action: 'change_theme',
                theme_key: themeKey
            }));
        }

        // Also persist via REST API for fallback/assurance
        try {
            const formData = new FormData();
            formData.append('theme_key', themeKey);
            await fetch(`/direct/api/theme/${activeConvId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrfToken() },
                body: formData
            });
        } catch (e) {
            console.error('Failed to persist theme via API:', e);
        }
    };

    if (customWallpaperInput) {
        customWallpaperInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const file = this.files[0];
                if (customWallpaperFileName) customWallpaperFileName.textContent = file.name;
                if (applyWallpaperBtn) applyWallpaperBtn.classList.remove('d-none');
            }
        });
    }

    if (customWallpaperForm) {
        customWallpaperForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            if (!activeConvId || !customWallpaperInput.files || !customWallpaperInput.files[0]) return;

            const file = customWallpaperInput.files[0];
            const formData = new FormData();
            formData.append('theme_key', 'custom');
            formData.append('custom_theme_image', file);

            if (applyWallpaperBtn) {
                applyWallpaperBtn.disabled = true;
                applyWallpaperBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Applying...';
            }

            try {
                const res = await fetch(`/direct/api/theme/${activeConvId}/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCsrfToken() },
                    body: formData
                });
                const data = await res.json();
                if (data.success) {
                    applyChatThemeDOM('custom', data.custom_theme_image_url);
                    const modalEl = document.getElementById('chatThemeModal');
                    if (modalEl && bootstrap.Modal.getInstance(modalEl)) {
                        bootstrap.Modal.getInstance(modalEl).hide();
                    }
                    window.showToast && window.showToast('Custom wallpaper applied!', 'success');
                } else {
                    window.showToast && window.showToast(data.error || 'Failed to upload custom wallpaper.', 'error');
                }
            } catch (err) {
                console.error(err);
                window.showToast && window.showToast('Network error while uploading wallpaper.', 'error');
            } finally {
                if (applyWallpaperBtn) {
                    applyWallpaperBtn.disabled = false;
                    applyWallpaperBtn.innerHTML = '<i class="bi bi-check-lg me-1"></i> Apply Wallpaper';
                }
            }
        });
    }

    // Initialize preset cards on page load
    renderThemePresetCards();

}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDirect);
} else {
    initDirect();
}
