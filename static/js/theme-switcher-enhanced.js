// Enhanced Theme Switcher with System Preference Detection and Server Sync
class ThemeSwitcher {
    constructor() {
        this.theme = this.getStoredTheme() || this.getSystemPreference();
        this.syncedWithServer = false;
        this.init();
    }

    init() {
        // Apply theme on load with transition prevention
        this.applyTheme(this.theme, false);

        // Sync with server preference if user is logged in
        this.syncWithServerPreference();

        // Set up toggle button
        const toggleBtn = document.getElementById('theme-toggle');

        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                this.toggleTheme();
            });
        }

        // Update icon based on current theme
        this.updateIcon();

        // Listen for system theme changes
        this.watchSystemPreference();

        // Enable transitions after initial load
        setTimeout(() => {
            document.documentElement.classList.add('theme-transition-enabled');
        }, 100);
    }

    async syncWithServerPreference() {
        // Try to get user's saved preference from server
        try {
            const response = await fetch('/api/v1/user/preferences', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.theme_preference && data.theme_preference !== 'auto') {
                    this.theme = data.theme_preference;
                    this.applyTheme(this.theme, false);
                    this.setStoredTheme(this.theme);
                    this.syncedWithServer = true;
                }
            }
        } catch (error) {
            console.debug('Using local theme preference');
        }
    }

    async saveToServer(theme) {
        try {
            await fetch('/api/v1/user/preferences', {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({ theme_preference: theme })
            });
        } catch (error) {
            console.debug('Could not save theme to server');
        }
    }

    getSystemPreference() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }

    getStoredTheme() {
        return localStorage.getItem('ward-theme');
    }

    setStoredTheme(theme) {
        localStorage.setItem('ward-theme', theme);
    }

    applyTheme(theme, withTransition = true) {
        const root = document.documentElement;

        if (!withTransition) {
            root.classList.remove('theme-transition-enabled');
        }

        root.setAttribute('data-theme', theme);
        this.theme = theme;
        this.updateIcon();

        if (!withTransition) {
            setTimeout(() => {
                root.classList.add('theme-transition-enabled');
            }, 50);
        }

        this.updateMetaThemeColor(theme);
    }

    updateMetaThemeColor(theme) {
        let metaTheme = document.querySelector('meta[name="theme-color"]');
        if (!metaTheme) {
            metaTheme = document.createElement('meta');
            metaTheme.name = 'theme-color';
            document.head.appendChild(metaTheme);
        }
        metaTheme.content = theme === 'dark' ? '#1a1d23' : '#5EBBA8';
    }

    toggleTheme() {
        const newTheme = this.theme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme, true);
        this.setStoredTheme(newTheme);
        this.saveToServer(newTheme);
        this.animateToggle();
    }

    animateToggle() {
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            toggleBtn.style.transform = 'scale(0.9)';
            setTimeout(() => {
                toggleBtn.style.transform = 'scale(1)';
            }, 150);
        }
    }

    updateIcon() {
        const themeIcon = document.getElementById('theme-icon');
        if (themeIcon) {
            if (this.theme === 'dark') {
                themeIcon.classList.remove('fa-moon');
                themeIcon.classList.add('fa-sun');
                themeIcon.setAttribute('title', 'Switch to light mode');
            } else {
                themeIcon.classList.remove('fa-sun');
                themeIcon.classList.add('fa-moon');
                themeIcon.setAttribute('title', 'Switch to dark mode');
            }
        }
    }

    watchSystemPreference() {
        if (window.matchMedia) {
            const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');

            const handler = (e) => {
                if (!this.getStoredTheme() && !this.syncedWithServer) {
                    const newTheme = e.matches ? 'dark' : 'light';
                    this.applyTheme(newTheme, true);
                }
            };

            if (darkModeQuery.addEventListener) {
                darkModeQuery.addEventListener('change', handler);
            } else if (darkModeQuery.addListener) {
                darkModeQuery.addListener(handler);
            }
        }
    }
}

// Initialize theme switcher when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.themeSwitcher = new ThemeSwitcher();
});

// Prevent flash of unstyled content (FOUC)
(function() {
    const theme = localStorage.getItem('ward-theme') ||
                  (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
})();
