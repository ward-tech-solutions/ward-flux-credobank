// Common JavaScript utilities

// Real-time SSE connection
let eventSource = null;
let sseConnected = false;

function initializeSSE() {
    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource('/stream/updates');

    eventSource.onopen = function() {
        sseConnected = true;
        console.log('✓ Real-time updates connected');
        updateConnectionStatus(true);
    };

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);

        if (data.type === 'status_change') {
            handleStatusChanges(data.changes);
        } else if (data.type === 'heartbeat') {
            console.log('💓 Heartbeat:', data.active_devices, 'devices');
        }
    };

    eventSource.onerror = function(error) {
        sseConnected = false;
        console.error('SSE Error:', error);
        updateConnectionStatus(false);

        // Reconnect after 5 seconds
        setTimeout(() => {
            if (!sseConnected) {
                initializeSSE();
            }
        }, 5000);
    };
}

function handleStatusChanges(changes) {
    changes.forEach(change => {
        const message = `${change.hostname}: ${change.old_status} → ${change.new_status}`;
        const type = change.new_status === 'Up' ? 'success' : 'error';
        showNotification(message, type);
    });

    // Refresh data on pages that need it
    if (typeof refreshData === 'function') {
        setTimeout(refreshData, 1000);
    }
}

function updateConnectionStatus(connected) {
    let indicator = document.getElementById('sse-indicator');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'sse-indicator';
        indicator.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s ease;
        `;
        document.body.appendChild(indicator);
    }

    if (connected) {
        indicator.style.background = 'var(--success-green)';
        indicator.style.color = 'white';
        indicator.innerHTML = '<i class="fas fa-circle" style="font-size: 8px;"></i> Live';
    } else {
        indicator.style.background = 'var(--danger-red)';
        indicator.style.color = 'white';
        indicator.innerHTML = '<i class="fas fa-circle" style="font-size: 8px;"></i> Reconnecting...';
    }
}

function startAutoRefresh(interval) {
    setInterval(() => {
        if (typeof refreshData === 'function') {
            refreshData();
        }
    }, interval);
}

// Initialize SSE on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeSSE();
});

function updateTimestamp() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });

    const element = document.getElementById('last-update');
    if (element) {
        element.textContent = `Last updated: ${timeString}`;
    }
}

// Update timestamp every second
setInterval(updateTimestamp, 1000);
updateTimestamp();

// Handle modal escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modal = document.getElementById('device-modal');
        if (modal && modal.style.display !== 'none') {
            closeModal();
        }
    }
});

// Notification system
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;

    const colors = {
        success: 'var(--success-green)',
        error: 'var(--danger-red)',
        info: 'var(--primary-blue)',
        warning: 'var(--warning-orange)'
    };

    notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 24px;
        padding: 1rem 1.5rem;
        background: ${colors[type]};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 99999;
        font-weight: 600;
        font-size: 0.875rem;
        animation: slideInRight 0.3s ease-out;
    `;

    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Enhanced Loading Indicator
function showLoadingOverlay(message = 'Loading...') {
    let overlay = document.getElementById('loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-content">
                <div class="loading-spinner"></div>
                <div class="loading-message">${message}</div>
            </div>
        `;
        document.body.appendChild(overlay);
    }
    overlay.querySelector('.loading-message').textContent = message;
    overlay.style.display = 'flex';
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

// Better error handler with user-friendly messages
function handleError(error, context = '') {
    console.error(`Error in ${context}:`, error);

    let userMessage = 'An unexpected error occurred';

    if (error.message) {
        if (error.message.includes('fetch')) {
            userMessage = 'Connection error. Please check your network.';
        } else if (error.message.includes('401') || error.message.includes('Unauthorized')) {
            userMessage = 'Session expired. Please log in again.';
            setTimeout(() => window.location.href = '/login', 2000);
        } else if (error.message.includes('403') || error.message.includes('Forbidden')) {
            userMessage = 'You don\'t have permission to perform this action.';
        } else if (error.message.includes('404')) {
            userMessage = 'Requested resource not found.';
        } else if (error.message.includes('500')) {
            userMessage = 'Server error. Please try again later.';
        }
    }

    showNotification(userMessage, 'error');
    hideLoadingOverlay();
    return userMessage;
}

// Add animation and loading styles (only if not already added)
if (!document.getElementById('common-styles')) {
    const style = document.createElement('style');
    style.id = 'common-styles';
    style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }

    #loading-overlay {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(15, 15, 15, 0.85);
        backdrop-filter: blur(4px);
        z-index: 999999;
        align-items: center;
        justify-content: center;
    }

    .loading-content {
        text-align: center;
        color: white;
    }

    .loading-spinner {
        width: 48px;
        height: 48px;
        border: 4px solid rgba(94, 187, 168, 0.2);
        border-top-color: var(--ward-green);
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
        margin: 0 auto 1rem;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    .loading-message {
        font-size: 1rem;
        font-weight: 600;
        color: var(--ward-green);
    }
`;
    document.head.appendChild(style);
}

// Make functions globally available
window.showLoadingOverlay = showLoadingOverlay;
window.hideLoadingOverlay = hideLoadingOverlay;
window.handleError = handleError;