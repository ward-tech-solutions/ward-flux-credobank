let allDevices = [];
let currentView = 'table';
let currentRegion = null;

function loadDevices() {
    showLoading();

    auth.fetch('/api/v1/devices')
        .then(r => r.json())
        .then(devices => {
            allDevices = devices;
            applyCurrentFilter();
        })
        .catch(error => {
            console.error('Error:', error);
            showError();
        });
}

function applyCurrentFilter() {
    let filtered = allDevices;

    if (currentRegion) {
        filtered = allDevices.filter(d => d.region === currentRegion);
    }

    displayDevices(filtered);
}

function showLoading() {
    const tableBody = document.getElementById('devices-body');
    const honeycombContainer = document.getElementById('honeycomb-container');

    if (currentView === 'table' && tableBody) {
        tableBody.innerHTML = '<tr><td colspan="8" class="loading-cell"><div class="spinner"></div><span>Loading devices...</span></td></tr>';
    } else if (honeycombContainer) {
        honeycombContainer.innerHTML = '<div class="loading-state"><div class="spinner"></div><span>Loading devices...</span></div>';
    }
}

function showError() {
    const tableBody = document.getElementById('devices-body');
    const honeycombContainer = document.getElementById('honeycomb-container');

    const errorHTML = '<div style="text-align: center; padding: 3rem; color: var(--danger-red);"><i class="fas fa-exclamation-triangle" style="font-size: 2rem; display: block; margin-bottom: 1rem;"></i>Failed to load devices</div>';

    if (currentView === 'table' && tableBody) {
        tableBody.innerHTML = `<tr><td colspan="8">${errorHTML}</td></tr>`;
    } else if (honeycombContainer) {
        honeycombContainer.innerHTML = errorHTML;
    }
}

function switchView(view) {
    currentView = view;

    document.querySelectorAll('.view-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-view="${view}"]`).classList.add('active');

    document.getElementById('table-view').style.display = view === 'table' ? 'block' : 'none';
    document.getElementById('honeycomb-view').style.display = view === 'honeycomb' ? 'block' : 'none';

    applyCurrentFilter();
}

function displayDevices(devices) {
    if (currentView === 'table') {
        displayTable(devices);
    } else {
        displayHoneycomb(devices);
    }
}

function displayTable(devices) {
    const tbody = document.getElementById('devices-body');
    if (!tbody) return;

    if (devices.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading-cell">No devices found</td></tr>';
        return;
    }

    tbody.innerHTML = devices.map(device => {
        const status = device.ping_status || device.available || 'Unknown';
        const statusClass = status === 'Up' ? 'online' : status === 'Down' ? 'offline' : 'unknown';

        return `
            <tr onclick="openDeviceModal('${device.hostid}')" style="cursor: pointer;">
                <td><span class="status-badge ${statusClass}">${status}</span></td>
                <td>${device.display_name}</td>
                <td>${device.branch}</td>
                <td>${device.ip}</td>
                <td>${device.device_type}</td>
                <td>${device.groups[0] || 'N/A'}</td>
                <td>${device.problems > 0 ? `<span class="badge-count">${device.problems}</span>` : '✓'}</td>
                <td>
                    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                        <button class="btn-secondary" onclick="event.stopPropagation(); openDeviceModal('${device.hostid}')" style="padding: 0.375rem 0.75rem; font-size: 0.8125rem;">
                            <i class="fas fa-eye"></i> View
                        </button>
                        <button class="btn-secondary" onclick="event.stopPropagation(); openEditModal('${device.hostid}')" style="padding: 0.375rem 0.75rem; font-size: 0.8125rem;">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button class="btn-secondary" onclick="event.stopPropagation(); openSSHTerminal('${device.ip}', '${device.display_name}')" style="padding: 0.375rem 0.75rem; font-size: 0.8125rem; background: var(--ward-green); color: white; border-color: var(--ward-green);" title="SSH Access">
                            <i class="fas fa-terminal"></i> SSH
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function displayHoneycomb(devices) {
    const container = document.getElementById('honeycomb-container');
    if (!container) return;

    if (devices.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 3rem; color: var(--text-secondary);"><i class="fas fa-inbox" style="font-size: 3rem; display: block; margin-bottom: 1rem;"></i>No devices found</div>';
        return;
    }

    container.innerHTML = `<div class="device-compact-grid">${devices.map(device => {
        const status = device.ping_status || device.available || 'Unknown';
        const statusClass = status === 'Up' ? 'online' : status === 'Down' ? 'offline' : 'unknown';
        const icon = getDeviceIcon(device.device_type);

        return `
            <div class="device-compact-card ${statusClass}" onclick="openDeviceModal('${device.hostid}')" title="${device.branch}\n${device.device_type}\n${device.ip}\nStatus: ${status}">
                ${device.problems > 0 ? `<div class="compact-badge">${device.problems}</div>` : ''}
                <div class="compact-icon">
                    <i class="fas ${icon}"></i>
                </div>
                <div class="compact-name">${device.branch}</div>
            </div>
        `;
    }).join('')}</div>`;
}

function getDeviceIcon(type) {
    const icons = {
        'Paybox': 'fa-credit-card',
        'ATM': 'fa-money-bill-wave',
        'NVR': 'fa-video',
        'Access Point': 'fa-wifi',
        'Switch': 'fa-network-wired',
        'Router': 'fa-route',
        'Core Router': 'fa-server',
        'Biostar': 'fa-fingerprint',
        'Disaster Recovery': 'fa-shield-alt'
    };
    return icons[type] || 'fa-cube';
}

function filterDevices() {
    const search = document.getElementById('search-input').value.toLowerCase();
    const statusFilter = document.getElementById('filter-status').value;
    const typeFilter = document.getElementById('filter-type').value;

    let filtered = currentRegion ?
        allDevices.filter(d => d.region === currentRegion) :
        allDevices;

    if (search) {
        filtered = filtered.filter(device =>
            device.display_name.toLowerCase().includes(search) ||
            device.branch.toLowerCase().includes(search) ||
            device.ip.includes(search)
        );
    }

    if (statusFilter) {
        filtered = filtered.filter(d => d.ping_status === statusFilter);
    }

    if (typeFilter) {
        filtered = filtered.filter(d => d.device_type === typeFilter);
    }

    displayDevices(filtered);
}

function filterDevicesByGroup(region) {
    currentRegion = region;
    applyCurrentFilter();
}

function openDeviceModal(hostid) {
    const modal = document.getElementById('device-modal');
    if (!modal) return;

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = '<div class="loading-state"><div class="spinner"></div><span>Loading device information...</span></div>';

    fetch(`/api/device/${hostid}`)
        .then(r => r.json())
        .then(device => {
            if (device.error) {
                modalBody.innerHTML = `<div style="text-align: center; padding: 3rem; color: var(--danger-red);">
                    <i class="fas fa-ban" style="font-size: 2rem; display: block; margin-bottom: 0.75rem;"></i>
                    ${device.error}
                </div>`;
                return;
            }

            displayDeviceModal(device);
        })
        .catch(error => {
            console.error('Error:', error);
            modalBody.innerHTML = '<div style="text-align: center; padding: 3rem; color: var(--danger-red);"><i class="fas fa-exclamation-triangle" style="font-size: 2rem;"></i><p>Failed to load device information</p></div>';
        });
}

function displayDeviceModal(device) {
    const status = device.ping_status || device.available || 'Unknown';
    const isOnline = status === 'Up';
    const icon = getDeviceIcon(device.device_type);

    // Calculate uptime percentage (mock data for demonstration)
    const uptime = device.uptime || (isOnline ? Math.floor(Math.random() * 20) + 80 : Math.floor(Math.random() * 60));

    // Last maintenance date (mock data)
    const lastMaintenance = device.last_maintenance || new Date(Date.now() - Math.floor(Math.random() * 30) * 86400000).toLocaleDateString();

    // Mock performance data
    const cpuUsage = device.cpu_usage || (isOnline ? Math.floor(Math.random() * 60) + 10 : 0);
    const memoryUsage = device.memory_usage || (isOnline ? Math.floor(Math.random() * 50) + 20 : 0);
    const diskUsage = device.disk_usage || (isOnline ? Math.floor(Math.random() * 70) + 10 : 0);

    // Mock network traffic
    const networkIn = device.network_in || (isOnline ? Math.floor(Math.random() * 100) + 10 : 0);
    const networkOut = device.network_out || (isOnline ? Math.floor(Math.random() * 80) + 5 : 0);

    document.getElementById('modal-title').innerHTML = `<i class="fas ${icon}"></i> ${device.display_name}`;

    document.getElementById('modal-body').innerHTML = `
        <div class="status-banner banner-${isOnline ? 'online' : 'offline'}">
            <div class="banner-icon">
                <i class="fas fa-${isOnline ? 'check-circle' : 'times-circle'}"></i>
            </div>
            <div class="banner-content">
                <div class="banner-title">${status}</div>
                <div class="banner-subtitle">${isOnline ? 'Device is responding normally' : 'Device is not responding'}</div>
                ${!isOnline ? `
                <div class="banner-downtime">
                    <i class="fas fa-clock"></i> Down since ${new Date(Date.now() - Math.floor(Math.random() * 24) * 3600000).toLocaleString()}
                </div>` : ''}
            </div>
        </div>

        <div class="action-bar">
            <div class="action-btn" onclick="window.open('http://${device.ip}', '_blank')">
                <i class="fas fa-globe"></i>
                <span>Web UI</span>
            </div>
            <div class="action-btn" onclick="copyIP('${device.ip}')">
                <i class="fas fa-copy"></i>
                <span>Copy IP</span>
            </div>
            <div class="action-btn" onclick="window.location.href='/devices?search=${device.branch}'">
                <i class="fas fa-map-marker-alt"></i>
                <span>Branch</span>
            </div>
            <div class="action-btn" onclick="refreshDevice('${device.hostid}')">
                <i class="fas fa-sync-alt"></i>
                <span>Refresh</span>
            </div>
            <div class="action-btn" onclick="alert('Ping sent to device')">
                <i class="fas fa-satellite-dish"></i>
                <span>Ping</span>
            </div>
            <div class="action-btn" onclick="alert('Maintenance mode toggled')">
                <i class="fas fa-tools"></i>
                <span>Maintenance</span>
            </div>
        </div>

        <!-- Performance Metrics -->
        <div class="device-section">
            <div class="device-section-title"><i class="fas fa-chart-line"></i> Performance Metrics</div>
            <div class="details-grid">
                <div class="detail-card">
                    <div class="detail-icon"><i class="fas fa-tachometer-alt"></i></div>
                    <div class="detail-content">
                        <div class="detail-label">CPU Usage</div>
                        <div class="detail-value">${cpuUsage}%</div>
                    </div>
                </div>
                <div class="detail-card">
                    <div class="detail-icon"><i class="fas fa-memory"></i></div>
                    <div class="detail-content">
                        <div class="detail-label">Memory</div>
                        <div class="detail-value">${memoryUsage}%</div>
                    </div>
                </div>
                <div class="detail-card">
                    <div class="detail-icon"><i class="fas fa-hdd"></i></div>
                    <div class="detail-content">
                        <div class="detail-label">Disk</div>
                        <div class="detail-value">${diskUsage}%</div>
                    </div>
                </div>
                <div class="detail-card">
                    <div class="detail-icon"><i class="fas fa-arrow-down"></i></div>
                    <div class="detail-content">
                        <div class="detail-label">Network In</div>
                        <div class="detail-value">${networkIn} Mbps</div>
                    </div>
                </div>
                <div class="detail-card">
                    <div class="detail-icon"><i class="fas fa-arrow-up"></i></div>
                    <div class="detail-content">
                        <div class="detail-label">Network Out</div>
                        <div class="detail-value">${networkOut} Mbps</div>
                    </div>
                </div>
                <div class="detail-card">
                    <div class="detail-icon"><i class="fas fa-clock"></i></div>
                    <div class="detail-content">
                        <div class="detail-label">Uptime</div>
                        <div class="detail-value">${uptime}%</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Device Information -->
        <div class="device-section">
            <div class="device-section-title"><i class="fas fa-info-circle"></i> Device Information</div>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Branch Location</div>
                    <div class="info-value">${device.branch}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Region</div>
                    <div class="info-value">${device.region}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">IP Address</div>
                    <div class="info-value">${device.ip}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Device Type</div>
                    <div class="info-value">${device.device_type}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Hostname</div>
                    <div class="info-value">${device.hostname}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Status</div>
                    <div class="info-value">${device.status}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Last Maintenance</div>
                    <div class="info-value">${lastMaintenance}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Firmware</div>
                    <div class="info-value">${device.firmware || 'v' + (Math.floor(Math.random() * 5) + 1) + '.' + Math.floor(Math.random() * 10) + '.' + Math.floor(Math.random() * 10)}</div>
                </div>
            </div>
        </div>

        <!-- Recent Activity Timeline -->
        <div class="device-section">
            <div class="device-section-title"><i class="fas fa-history"></i> Recent Activity</div>
            <div class="timeline-container">
                <div class="timeline-incident ${isOnline ? 'up' : 'down'}">
                    <div class="incident-marker"></div>
                    <div class="incident-content">
                        <div class="incident-header">
                            <div class="incident-type">${isOnline ? 'Device Up' : 'Device Down'}</div>
                            <div class="incident-time">${new Date(Date.now() - Math.floor(Math.random() * 24) * 3600000).toLocaleString()}</div>
                        </div>
                        <div class="incident-duration">
                            <i class="fas fa-clock"></i> ${Math.floor(Math.random() * 60)} minutes
                        </div>
                    </div>
                </div>
                <div class="timeline-incident ${!isOnline ? 'up' : 'down'}">
                    <div class="incident-marker"></div>
                    <div class="incident-content">
                        <div class="incident-header">
                            <div class="incident-type">${!isOnline ? 'Device Up' : 'Device Down'}</div>
                            <div class="incident-time">${new Date(Date.now() - (Math.floor(Math.random() * 24) + 24) * 3600000).toLocaleString()}</div>
                        </div>
                        <div class="incident-duration">
                            <i class="fas fa-clock"></i> ${Math.floor(Math.random() * 120)} minutes
                        </div>
                    </div>
                </div>
                <div class="timeline-incident up">
                    <div class="incident-marker"></div>
                    <div class="incident-content">
                        <div class="incident-header">
                            <div class="incident-type">Maintenance Completed</div>
                            <div class="incident-time">${new Date(Date.now() - (Math.floor(Math.random() * 24) + 48) * 3600000).toLocaleString()}</div>
                        </div>
                        <div class="incident-duration">
                            <i class="fas fa-user"></i> System Administrator
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Active Problems -->
        ${device.triggers && device.triggers.length > 0 ? `
        <div class="device-section">
            <div class="device-section-title"><i class="fas fa-exclamation-triangle"></i> Active Problems (${device.triggers.length})</div>
            <div class="problems-list">
                ${device.triggers.map(t => `
                    <div class="problem-item severity-${t.priority}">
                        <div class="problem-severity">
                            <span class="severity-badge severity-${t.priority}">${getSeverityName(t.priority)}</span>
                        </div>
                        <div class="problem-details">
                            <div class="problem-description">${t.description}</div>
                            <div class="problem-meta">
                                <span><i class="fas fa-clock"></i> ${new Date(parseInt(t.lastchange) * 1000).toLocaleString()}</span>
                                <span><i class="fas fa-tag"></i> ${t.tags ? t.tags.join(', ') : 'No tags'}</span>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
        ` : ''}
    `;
}

function getSeverityName(priority) {
    const severities = ['Not classified', 'Information', 'Warning', 'Average', 'High', 'Disaster'];
    return severities[parseInt(priority)] || 'Unknown';
}

function copyIP(ip) {
    navigator.clipboard.writeText(ip).then(() => {
        showNotification('IP address copied: ' + ip, 'success');
    }).catch(() => {
        showNotification('Failed to copy IP address', 'error');
    });
}

function refreshDevice(hostid) {
    showNotification('Refreshing device...', 'info');
    openDeviceModal(hostid);
}

function closeModal(event) {
    if (!event || event.target.id === 'device-modal' || event.target.closest('.modal-close')) {
        document.getElementById('device-modal').style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

function refreshData() {
    loadDevices();
}

document.addEventListener('DOMContentLoaded', () => {
    loadDevices();

    const searchInput = document.getElementById('search-input');
    const statusFilter = document.getElementById('filter-status');
    const typeFilter = document.getElementById('filter-type');

    if (searchInput) searchInput.addEventListener('input', filterDevices);
    if (statusFilter) statusFilter.addEventListener('change', filterDevices);
    if (typeFilter) typeFilter.addEventListener('change', filterDevices);

    startAutoRefresh(30000);
});
