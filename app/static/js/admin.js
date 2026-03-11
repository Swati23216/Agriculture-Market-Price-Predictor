document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('saveStyles').addEventListener('click', saveStyles);
});

function saveStyles() {
    const data = {
        primary_color: document.getElementById('primaryColor').value,
        background_color: document.getElementById('backgroundColor').value
    };
    
    fetch('/admin/save-styles', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    }).then(showSuccessMessage);
}

function showSuccessMessage() {
    // Add visual feedback
}
// Preview functionality for admin CSS editor
document.addEventListener('DOMContentLoaded', function() {
    // Initialize preview iframe
    const previewIframe = document.getElementById('sitePreview');
    
    // Refresh button
    document.getElementById('refreshPreview')?.addEventListener('click', function() {
        previewIframe.src = previewIframe.src; // Reload iframe
        showPreviewNotification('Preview refreshed');
    });

    // Fullscreen button
    document.getElementById('fullscreenPreview')?.addEventListener('click', function() {
        if (previewIframe.requestFullscreen) {
            previewIframe.requestFullscreen();
        } else if (previewIframe.webkitRequestFullscreen) { /* Safari */
            previewIframe.webkitRequestFullscreen();
        } else if (previewIframe.msRequestFullscreen) { /* IE11 */
            previewIframe.msRequestFullscreen();
        }
    });

    // Auto-refresh preview when forms are submitted
    const styleForm = document.getElementById('styleForm');
    const navbarForm = document.getElementById('navbarForm');
    
    [styleForm, navbarForm].forEach(form => {
        form?.addEventListener('submit', function() {
            setTimeout(() => {
                previewIframe.src = previewIframe.src;
                showPreviewNotification('Preview updated with changes');
            }, 1000);
        });
    });

    // Handle iframe load events
    previewIframe.addEventListener('load', function() {
        try {
            // Adjust iframe content height
            previewIframe.style.height = previewIframe.contentWindow.document.body.scrollHeight + 'px';
        } catch (e) {
            console.log('Preview load error:', e);
        }
    });

    // Show notification function
    function showPreviewNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'preview-notification';
        notification.textContent = message;
        document.querySelector('.preview-container').appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 500);
        }, 2000);
    }
});