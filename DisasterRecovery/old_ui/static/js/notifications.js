// Real-time Notification System
class NotificationManager {
    constructor() {
        this.notifications = [];
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.enabled = this.getNotificationPreference();
        this.unreadCount = 0;
        this.hasShownConnectedToast = false; // Track if we've shown the initial connection toast

        this.init();
    }

    init() {
        // Set up UI event listeners
        this.setupUI();

        // Load notification preference
        this.applyNotificationPreference();

        // Connect to WebSocket if enabled
        if (this.enabled) {
            this.connectWebSocket();
        }

        // Poll for problems periodically as fallback
        this.startPolling();
    }

    setupUI() {
        // Toggle notification dropdown
        const toggleBtn = document.getElementById('notification-toggle');
        const dropdown = document.getElementById('notification-dropdown');

        if (toggleBtn && dropdown) {
            toggleBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleDropdown();
            });

            // Close dropdown when clicking outside
            document.addEventListener('click', (e) => {
                if (!e.target.closest('.notification-wrapper')) {
                    dropdown.style.display = 'none';
                }
            });
        }

        // Enable/disable notifications toggle
        const enableToggle = document.getElementById('notification-enabled');
        if (enableToggle) {
            enableToggle.checked = this.enabled;
            enableToggle.addEventListener('change', (e) => {
                this.toggleNotifications(e.target.checked);
            });
        }
    }

    toggleDropdown() {
        const dropdown = document.getElementById('notification-dropdown');
        if (dropdown.style.display === 'none') {
            dropdown.style.display = 'block';
            this.markAllAsRead();
        } else {
            dropdown.style.display = 'none';
        }
    }

    getNotificationPreference() {
        const pref = localStorage.getItem('ward-notifications-enabled');
        return pref === null ? true : pref === 'true';
    }

    setNotificationPreference(enabled) {
        localStorage.setItem('ward-notifications-enabled', enabled);
        this.enabled = enabled;
    }

    applyNotificationPreference() {
        const toggle = document.getElementById('notification-enabled');
        if (toggle) {
            toggle.checked = this.enabled;
        }
    }

    toggleNotifications(enabled) {
        this.setNotificationPreference(enabled);

        if (enabled) {
            this.connectWebSocket();
            this.showToast('Notifications enabled', 'success');
        } else {
            this.disconnectWebSocket();
            this.showToast('Notifications disabled', 'info');
        }
    }

    connectWebSocket() {
        if (!this.enabled) return;

        try {
            // Connect to WebSocket endpoint
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/notifications`;

            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;

                // Only show toast on first connection, not on every page navigation
                if (!this.hasShownConnectedToast) {
                    this.showToast('Real-time notifications connected', 'success');
                    this.hasShownConnectedToast = true;
                }
            };

            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);

                // Ignore connection and pong messages - don't show as notifications
                if (data.type === 'connection' || data.type === 'pong') {
                    console.log('WebSocket status:', data.message || data.type);
                    return;
                }

                // Only handle actual problem/alert notifications
                this.handleNotification(data);
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');

                // Attempt to reconnect
                if (this.enabled && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
                    setTimeout(() => this.connectWebSocket(), this.reconnectDelay);
                }
            };
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
            // Fallback to polling only
        }
    }

    disconnectWebSocket() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    startPolling() {
        // Poll for new problems every 30 seconds as fallback
        setInterval(() => {
            if (this.enabled) {
                this.fetchProblems();
            }
        }, 30000);

        // Initial fetch
        if (this.enabled) {
            this.fetchProblems();
        }
    }

    async fetchProblems() {
        try {
            const response = await auth.fetch('/api/v1/problems');
            const data = await response.json();

            if (data.problems && data.problems.length > 0) {
                // Check for new problems
                data.problems.forEach(problem => {
                    const exists = this.notifications.find(n => n.id === problem.eventid);
                    if (!exists) {
                        this.addNotification({
                            id: problem.eventid,
                            type: this.getProblemSeverity(problem.severity),
                            title: problem.name,
                            message: `${problem.hostname} - ${problem.description || 'Issue detected'}`,
                            timestamp: new Date(parseInt(problem.clock) * 1000),
                            link: `/devices?hostid=${problem.hostid}`,
                            unread: true
                        });
                    }
                });
            }
        } catch (error) {
            console.error('Failed to fetch problems:', error);
        }
    }

    getProblemSeverity(severity) {
        // Zabbix severity: 0=Not classified, 1=Info, 2=Warning, 3=Average, 4=High, 5=Disaster
        if (severity >= 4) return 'critical';
        if (severity >= 2) return 'warning';
        return 'info';
    }

    handleNotification(data) {
        this.addNotification({
            id: data.id || Date.now(),
            type: data.type || 'info',
            title: data.title,
            message: data.message,
            timestamp: new Date(data.timestamp || Date.now()),
            link: data.link,
            unread: true
        });
    }

    addNotification(notification) {
        // Add to beginning of array
        this.notifications.unshift(notification);

        // Limit to 50 notifications
        if (this.notifications.length > 50) {
            this.notifications = this.notifications.slice(0, 50);
        }

        // Update UI
        this.renderNotifications();
        this.updateBadge();

        // Show browser notification if supported
        this.showBrowserNotification(notification);

        // Play sound (optional)
        if (notification.type === 'critical') {
            this.playNotificationSound();
        }
    }

    renderNotifications() {
        const list = document.getElementById('notification-list');
        if (!list) return;

        if (this.notifications.length === 0) {
            list.innerHTML = `
                <div class="notification-empty">
                    <i class="fas fa-inbox"></i>
                    <p>No new notifications</p>
                </div>
            `;
            return;
        }

        list.innerHTML = this.notifications.map(n => this.createNotificationHTML(n)).join('');
    }

    createNotificationHTML(notification) {
        const timeAgo = this.getTimeAgo(notification.timestamp);
        const icon = this.getNotificationIcon(notification.type);

        return `
            <div class="notification-item ${notification.unread ? 'unread' : ''} ${notification.type}"
                 data-id="${notification.id}"
                 onclick="notificationManager.handleNotificationClick('${notification.id}', '${notification.link || ''}')">
                <button class="notification-close" onclick="event.stopPropagation(); notificationManager.removeNotification('${notification.id}')">
                    <i class="fas fa-times"></i>
                </button>
                <div class="notification-content">
                    <div class="notification-icon ${notification.type}">
                        <i class="${icon}"></i>
                    </div>
                    <div class="notification-body">
                        <h4 class="notification-title">${this.escapeHtml(notification.title)}</h4>
                        <p class="notification-message">${this.escapeHtml(notification.message)}</p>
                        <div class="notification-meta">
                            <span class="notification-time">
                                <i class="fas fa-clock"></i> ${timeAgo}
                            </span>
                            ${notification.link ? '<span class="notification-action">View Details →</span>' : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    getNotificationIcon(type) {
        const icons = {
            critical: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle',
            success: 'fas fa-check-circle'
        };
        return icons[type] || icons.info;
    }

    handleNotificationClick(id, link) {
        this.markAsRead(id);
        if (link) {
            window.location.href = link;
        }
    }

    removeNotification(id) {
        this.notifications = this.notifications.filter(n => n.id !== id);
        this.renderNotifications();
        this.updateBadge();
    }

    markAsRead(id) {
        const notification = this.notifications.find(n => n.id === id);
        if (notification && notification.unread) {
            notification.unread = false;
            this.updateBadge();
        }
    }

    markAllAsRead() {
        this.notifications.forEach(n => n.unread = false);
        this.updateBadge();
    }

    updateBadge() {
        const badge = document.getElementById('notification-badge');
        if (!badge) return;

        this.unreadCount = this.notifications.filter(n => n.unread).length;

        if (this.unreadCount > 0) {
            badge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
            badge.style.display = 'block';
        } else {
            badge.style.display = 'none';
        }
    }

    showBrowserNotification(notification) {
        if (!('Notification' in window)) return;

        if (Notification.permission === 'granted') {
            new Notification(notification.title, {
                body: notification.message,
                icon: '/static/img/logo-ward.svg',
                tag: notification.id
            });
        } else if (Notification.permission !== 'denied') {
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    this.showBrowserNotification(notification);
                }
            });
        }
    }

    playNotificationSound() {
        // Optional: Play a notification sound
        try {
            const audio = new Audio('/static/sounds/notification.mp3');
            audio.volume = 0.3;
            audio.play().catch(() => {
                // Silently fail if audio doesn't play
            });
        } catch (error) {
            // Ignore audio errors
        }
    }

    showToast(message, type = 'info') {
        // Simple toast notification
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: ${type === 'success' ? '#10B981' : type === 'critical' ? '#EF4444' : '#3B82F6'};
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    getTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);

        if (seconds < 60) return 'Just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;

        return date.toLocaleDateString();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Global function for clear all button
function clearAllNotifications() {
    if (confirm('Clear all notifications?')) {
        notificationManager.notifications = [];
        notificationManager.renderNotifications();
        notificationManager.updateBadge();
    }
}

// Initialize notification manager
let notificationManager;
document.addEventListener('DOMContentLoaded', () => {
    notificationManager = new NotificationManager();
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
