// Theme Switcher with System Preference Detection
class ThemeSwitcher {
    constructor() {
        this.theme = this.getStoredTheme() || this.getSystemPreference();
        this.init();
    }

    init() {
        // Apply theme on load
        this.applyTheme(this.theme);

        // Set up toggle button
        const toggleBtn = document.getElementById('theme-toggle');
        const themeIcon = document.getElementById('theme-icon');

        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                this.toggleTheme();
            });
        }

        // Update icon based on current theme
        this.updateIcon();

        // Listen for system theme changes
        this.watchSystemPreference();
    }

    getSystemPreference() {
        // Check if user's system prefers dark mode
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }

    getStoredTheme() {
        // Get theme from localStorage
        return localStorage.getItem('ward-theme');
    }

    setStoredTheme(theme) {
        // Store theme preference in localStorage
        localStorage.setItem('ward-theme', theme);
    }

    applyTheme(theme) {
        // Apply theme by setting data-theme attribute on document element
        document.documentElement.setAttribute('data-theme', theme);
        this.theme = theme;
        this.updateIcon();
    }

    toggleTheme() {
        // Toggle between light and dark themes
        const newTheme = this.theme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme);
        this.setStoredTheme(newTheme);

        // Smooth transition effect
        document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
        setTimeout(() => {
            document.body.style.transition = '';
        }, 300);
    }

    updateIcon() {
        const themeIcon = document.getElementById('theme-icon');
        if (themeIcon) {
            if (this.theme === 'dark') {
                themeIcon.classList.remove('fa-moon');
                themeIcon.classList.add('fa-sun');
            } else {
                themeIcon.classList.remove('fa-sun');
                themeIcon.classList.add('fa-moon');
            }
        }
    }

    watchSystemPreference() {
        // Watch for system theme changes
        if (window.matchMedia) {
            const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');

            // Modern browsers
            if (darkModeQuery.addEventListener) {
                darkModeQuery.addEventListener('change', (e) => {
                    // Only auto-switch if user hasn't manually set a preference
                    if (!this.getStoredTheme()) {
                        const newTheme = e.matches ? 'dark' : 'light';
                        this.applyTheme(newTheme);
                    }
                });
            }
            // Older browsers
            else if (darkModeQuery.addListener) {
                darkModeQuery.addListener((e) => {
                    if (!this.getStoredTheme()) {
                        const newTheme = e.matches ? 'dark' : 'light';
                        this.applyTheme(newTheme);
                    }
                });
            }
        }
    }
}

// Initialize theme switcher when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new ThemeSwitcher();
});
