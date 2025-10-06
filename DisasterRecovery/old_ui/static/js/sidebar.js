// Sidebar - East/West with regions only (no device type expansion)
async function initSidebar() {
    const container = document.getElementById('sidebar-content');
    if (!container) return;

    // Check if user is admin - only show sidebar for admins
    try {
        const user = await auth.getCurrentUser();
        if (user && user.role !== 'admin') {
            // Hide sidebar for non-admin users
            const sidebar = document.querySelector('.sidebar');
            const mainContent = document.querySelector('.main-content');
            if (sidebar) sidebar.style.display = 'none';
            if (mainContent) mainContent.classList.add('no-sidebar');
            return;
        }
    } catch (error) {
        console.error('Error checking user role:', error);
    }

    const structure = {
        'East': ['Kakheti', 'Kvemo Kartli', 'Mtskheta-Mtianeti', 'Samtskhe-Javakheti', 'Shida Kartli', 'Tbilisi'],
        'West': ['Achara', 'Guria', 'Imereti', 'Samegrelo']
    };

    let html = '';

    for (const [group, regions] of Object.entries(structure)) {
        html += `
            <div class="tree-group">
                <div class="tree-group-header" onclick="toggleGroup(this)">
                    <i class="tree-toggle fas fa-chevron-down expanded"></i>
                    <i class="tree-icon fas fa-folder-open"></i>
                    <span class="tree-label">${group}</span>
                </div>
                <div class="tree-group-children">
        `;

        regions.forEach(region => {
            html += `
                <div class="tree-region-item" data-region="${region}" onclick="selectRegion(this, '${region}')">
                    <i class="region-icon fas fa-map-marker-alt"></i>
                    <span class="region-label">${region}</span>
                    <span class="region-count">0</span>
                </div>
            `;
        });

        html += `</div></div>`;
    }

    container.innerHTML = html;
    updateRegionCounts();
}

function toggleGroup(header) {
    const children = header.nextElementSibling;
    const toggle = header.querySelector('.tree-toggle');
    const icon = header.querySelector('.tree-icon');

    const isExpanded = children.style.display !== 'none';
    children.style.display = isExpanded ? 'none' : 'block';
    toggle.classList.toggle('expanded', !isExpanded);
    icon.className = isExpanded ? 'tree-icon fas fa-folder' : 'tree-icon fas fa-folder-open';
}

function selectRegion(element, region) {
    document.querySelectorAll('.tree-region-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');

    if (typeof filterDevicesByGroup === 'function') {
        filterDevicesByGroup(region);
    }
}

function updateRegionCounts() {
    auth.fetch('/api/v1/devices')
        .then(r => r.json())
        .then(devices => {
            const counts = {};
            devices.forEach(d => {
                counts[d.region] = (counts[d.region] || 0) + 1;
            });

            document.querySelectorAll('[data-region]').forEach(item => {
                const region = item.getAttribute('data-region');
                const count = counts[region] || 0;
                const badge = item.querySelector('.region-count');
                if (badge) badge.textContent = count;
            });
        });
}

document.addEventListener('DOMContentLoaded', initSidebar);
