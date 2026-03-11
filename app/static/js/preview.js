// preview.js - Enhanced Live Preview Functionality
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const previewIframe = document.getElementById('sitePreview');
    const refreshBtn = document.getElementById('refreshPreview');
    const fullscreenBtn = document.getElementById('fullscreenPreview');
    const styleForm = document.getElementById('styleForm');
    const navbarForm = document.getElementById('navbarForm');

    // Check if preview elements exist
    if (!previewIframe) {
        console.error('Preview iframe not found');
        return;
    }

    // Refresh Preview with loading indicator
    refreshBtn?.addEventListener('click', function() {
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing';
        
        previewIframe.src = previewIframe.src;
        showPreviewNotification('Preview refreshed');
        
        setTimeout(() => {
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
        }, 1000);
    });

    // Enhanced Fullscreen Handling
    fullscreenBtn?.addEventListener('click', function() {
        try {
            if (document.fullscreenElement) {
                document.exitFullscreen();
                fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i> Fullscreen';
            } else {
                previewIframe.requestFullscreen()
                    .then(() => {
                        fullscreenBtn.innerHTML = '<i class="fas fa-compress"></i> Exit';
                    })
                    .catch(err => {
                        console.error('Fullscreen error:', err);
                        showPreviewNotification('Fullscreen not supported');
                    });
            }
        } catch (err) {
            console.error('Fullscreen error:', err);
            showPreviewNotification('Fullscreen not supported');
        }
    });

    // Auto-refresh when forms are submitted
    [styleForm, navbarForm].forEach(form => {
        form?.addEventListener('submit', function() {
            setTimeout(() => {
                previewIframe.src = previewIframe.src;
                showPreviewNotification('Preview updated with changes');
            }, 1000);
        });
    });

    // Iframe load event handler
    previewIframe.addEventListener('load', function() {
        try {
            // Adjust iframe height to content
            const body = previewIframe.contentDocument.body;
            const html = previewIframe.contentDocument.documentElement;
            const height = Math.max(
                body.scrollHeight,
                body.offsetHeight,
                html.clientHeight,
                html.scrollHeight,
                html.offsetHeight
            );
            previewIframe.style.height = height + 'px';
        } catch (e) {
            console.log('Preview load adjustment error:', e);
        }
    });

    // Show notification function
    function showPreviewNotification(message) {
        const existingNotif = document.querySelector('.preview-notification');
        if (existingNotif) existingNotif.remove();

        const notification = document.createElement('div');
        notification.className = 'preview-notification';
        notification.textContent = message;
        document.querySelector('.preview-container').appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 300);
        }, 2000);
    }

    // Device emulation (optional)
    function initDeviceEmulation() {
        const deviceButtons = `
            <div class="device-buttons mt-2">
                <button class="btn btn-sm btn-outline-secondary device-btn" data-width="375">
                    <i class="fas fa-mobile"></i> Mobile
                </button>
                <button class="btn btn-sm btn-outline-secondary device-btn" data-width="768">
                    <i class="fas fa-tablet"></i> Tablet
                </button>
                <button class="btn btn-sm btn-outline-secondary device-btn" data-width="100%">
                    <i class="fas fa-desktop"></i> Desktop
                </button>
            </div>
        `;
        
        document.querySelector('.preview-controls')?.insertAdjacentHTML('beforeend', deviceButtons);
        
        document.querySelectorAll('.device-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                previewIframe.style.width = this.dataset.width;
                previewIframe.style.maxWidth = 'none';
                showPreviewNotification(`Viewport: ${this.dataset.width}`);
            });
        });
    }

    // Uncomment to enable device emulation
    // initDeviceEmulation();
});