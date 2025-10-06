// Authentication utilities
class AuthManager {
    constructor() {
        this.token = localStorage.getItem('access_token');
        this.user = null;
    }

    isAuthenticated() {
        return !!this.token;
    }

    getToken() {
        return this.token;
    }

    async getCurrentUser() {
        if (!this.isAuthenticated()) {
            return null;
        }

        if (this.user) {
            return this.user;
        }

        try {
            const response = await fetch('/api/v1/auth/me', {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            if (response.ok) {
                this.user = await response.json();
                return this.user;
            } else {
                // Token invalid
                this.logout();
                return null;
            }
        } catch (error) {
            console.error('Error fetching current user:', error);
            return null;
        }
    }

    async login(username, password) {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch('/api/v1/auth/login', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            this.token = data.access_token;
            localStorage.setItem('access_token', this.token);
            return { success: true };
        } else {
            const error = await response.json();
            return { success: false, error: error.detail };
        }
    }

    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('access_token');
        window.location.href = '/login';
    }

    // Check authentication and redirect if needed
    async requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = '/login';
            return false;
        }

        const user = await this.getCurrentUser();
        if (!user) {
            window.location.href = '/login';
            return false;
        }

        return true;
    }

    // Fetch with authentication
    async fetch(url, options = {}) {
        if (!this.isAuthenticated()) {
            throw new Error('Not authenticated');
        }

        const headers = {
            ...options.headers,
            'Authorization': `Bearer ${this.token}`
        };

        const response = await fetch(url, {
            ...options,
            headers
        });

        if (response.status === 401) {
            this.logout();
            throw new Error('Authentication expired');
        }

        return response;
    }
}

// Global auth instance
const auth = new AuthManager();

// Check authentication on page load (except login page)
if (window.location.pathname !== '/login') {
    auth.requireAuth().then(async (authenticated) => {
        if (authenticated) {
            const user = await auth.getCurrentUser();
            updateUserInfo(user);
        }
    });
}

// Update user info in UI
function updateUserInfo(user) {
    // Update user display in header/sidebar if elements exist
    const userNameEl = document.getElementById('user-name');
    const userRoleEl = document.getElementById('user-role');
    const userEmailEl = document.getElementById('user-email');

    if (userNameEl) userNameEl.textContent = user.full_name;
    if (userRoleEl) userRoleEl.textContent = user.role.replace('_', ' ').toUpperCase();
    if (userEmailEl) userEmailEl.textContent = user.email;

    // Show/hide admin-only elements
    const adminElements = document.querySelectorAll('[data-role="admin"]');
    adminElements.forEach(el => {
        if (user.role === 'admin') {
            el.style.display = 'flex';
        } else {
            el.style.display = 'none';
        }
    });

    // Show Users link for admin
    const usersLink = document.getElementById('users-link');
    if (usersLink && user.role === 'admin') {
        usersLink.style.display = 'flex';
    }

    // Show Config link for admin
    const configLink = document.getElementById('config-link');
    if (configLink && user.role === 'admin') {
        configLink.style.display = 'flex';
    }
}
