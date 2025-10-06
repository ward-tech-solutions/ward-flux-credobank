// Dashboard functionality
function loadDashboardStats() {
    console.log('Loading dashboard stats...');
    auth.fetch('/api/v1/dashboard/stats')
        .then(response => {
            console.log('Dashboard stats response:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('Dashboard stats data:', data);
            // Update KPI cards
            document.getElementById('total-devices').textContent = data.total_devices || 0;
            document.getElementById('online-devices').textContent = data.online_devices || 0;
            document.getElementById('offline-devices').textContent = data.offline_devices || 0;
            document.getElementById('uptime-percentage').textContent = (data.uptime_percentage || 0) + '%';
            document.getElementById('active-alerts').textContent = data.active_alerts || 0;
            document.getElementById('critical-alerts').textContent = data.critical_alerts || 0;

            // Load device types
            if (data.device_types) {
                displayDeviceTypes(data.device_types);
            }

            // Load regional stats
            if (data.regions_stats) {
                displayRegionalStats(data.regions_stats);
            }
        })
        .catch(error => {
            console.error('Error loading dashboard stats:', error);
            // Show error state
            document.getElementById('total-devices').textContent = '0';
            document.getElementById('online-devices').textContent = '0';
            document.getElementById('offline-devices').textContent = '0';
            document.getElementById('uptime-percentage').textContent = '0%';
            document.getElementById('active-alerts').textContent = '0';
            document.getElementById('critical-alerts').textContent = '0';
        });
}

function displayDeviceTypes(deviceTypes) {
    const container = document.getElementById('device-types-container');
    if (!container) return;

    const icons = {
        'Paybox': 'fa-credit-card',
        'ATM': 'fa-money-bill-wave',
        'NVR': 'fa-video',
        'Access Point': 'fa-wifi',
        'Switch': 'fa-network-wired',
        'Router': 'fa-router',
        'Core Router': 'fa-server',
        'Biostar': 'fa-fingerprint',
        'Disaster Recovery': 'fa-shield-alt'
    };

    container.innerHTML = Object.entries(deviceTypes).map(([type, stats]) => {
        const uptime = stats.total > 0 ? Math.round((stats.online / stats.total) * 100) : 0;
        return `
            <div class="device-type-card" onclick="showUptimeChart('${type}', 'device_type')" style="cursor: pointer;">
                <h4><i class="fas ${icons[type] || 'fa-cube'}"></i> ${type}</h4>
                <div class="device-type-stats">
                    <div><strong>${stats.total}</strong><small>Total</small></div>
                    <div style="color: var(--success-green);"><strong>${stats.online}</strong><small>Online</small></div>
                    <div style="color: var(--danger-red);"><strong>${stats.offline}</strong><small>Offline</small></div>
                </div>
                <div style="margin-top: 0.75rem; font-weight: 600; color: var(--text-secondary);">
                    ${uptime}% Uptime
                </div>
                <div style="margin-top: 0.5rem; font-size: 0.75rem; color: var(--primary-blue);">
                    <i class="fas fa-chart-line"></i> View Chart
                </div>
            </div>
        `;
    }).join('');
}

function displayRegionalStats(regionsStats) {
    const section = document.getElementById('regional-stats-section');
    const container = document.getElementById('regional-stats-grid');
    if (!section || !container) return;

    section.style.display = 'block';
    container.innerHTML = Object.entries(regionsStats).map(([region, stats]) => {
        if (region === 'Other') return '';
        const uptime = stats.total > 0 ? Math.round((stats.online / stats.total) * 100) : 0;
        return `
            <div class="region-card" onclick="showUptimeChart('${region}', 'region')">
                <h4>${region}</h4>
                <div style="font-size: 1.5rem; font-weight: 700; margin: 0.5rem 0;">${stats.total}</div>
                <div style="font-size: 0.875rem; color: var(--text-secondary);">
                    <span style="color: var(--success-green);">↑ ${stats.online} online</span> ·
                    <span style="color: var(--danger-red);">↓ ${stats.offline} offline</span>
                </div>
                <div style="margin-top: 0.5rem; font-weight: 600;">${uptime}% uptime</div>
                <div style="margin-top: 0.5rem; font-size: 0.75rem; color: var(--primary-blue); cursor: pointer;">
                    <i class="fas fa-chart-line"></i> View Chart
                </div>
            </div>
        `;
    }).join('');
}

let allAlerts = [];

function loadAlerts() {
    auth.fetch('/api/v1/alerts')
        .then(response => response.json())
        .then(alerts => {
            allAlerts = alerts;
            filterAndDisplayAlerts();
        })
        .catch(error => console.error('Error loading alerts:', error));
}

function filterAndDisplayAlerts() {
    const severityFilter = document.getElementById('severity-filter');
    const selectedSeverity = severityFilter ? severityFilter.value : '';

    let filtered = allAlerts;
    if (selectedSeverity) {
        // Case-insensitive comparison
        filtered = allAlerts.filter(alert => alert.severity.toUpperCase() === selectedSeverity.toUpperCase());
    }

    const tbody = document.getElementById('alerts-body');
    const alertCount = document.getElementById('alert-count');

    if (alertCount) alertCount.textContent = filtered.length;

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="loading-cell">No alerts for this severity</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.slice(0, 100).map(alert => `
        <tr>
            <td><span class="severity-badge severity-${alert.severity.toLowerCase()}">${alert.severity}</span></td>
            <td><a href="/device/${alert.hostid}" style="color: var(--ward-green); text-decoration: none; font-weight: 500;">${alert.host}</a></td>
            <td>${alert.description}</td>
            <td>${alert.time}</td>
        </tr>
    `).join('');
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Add event listener for severity filter
    const severityFilter = document.getElementById('severity-filter');
    if (severityFilter) {
        severityFilter.addEventListener('change', filterAndDisplayAlerts);
    }

    // Load initial data
    loadDashboardStats();
    loadAlerts();
    loadRecentDevices();

    // Update timestamp
    updateTimestamp();
    setInterval(updateTimestamp, 1000);
});

function loadRecentDevices() {
    auth.fetch('/api/v1/devices')
        .then(response => response.json())
        .then(devices => {
            const tbody = document.getElementById('devices-body');

            if (devices.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="loading-cell">No devices found</td></tr>';
                return;
            }

            const sorted = devices.sort((a, b) => b.problems - a.problems).slice(0, 20);

            tbody.innerHTML = sorted.map(device => {
                const pingStatus = device.ping_status || device.available || 'Unknown';
                const statusClass = pingStatus === 'Up' || pingStatus === 'Available' ? 'online' :
                                  pingStatus === 'Down' || pingStatus === 'Unavailable' ? 'offline' : 'unknown';

                return `
                    <tr onclick="openDeviceModal('${device.hostid}')" style="cursor: pointer;">
                        <td><span class="status-badge ${statusClass}">${pingStatus}</span></td>
                        <td>${device.display_name}</td>
                        <td>${device.branch}</td>
                        <td>${device.ip}</td>
                        <td>${device.device_type}</td>
                        <td>${device.problems > 0 ? `<span class="badge-count">${device.problems}</span>` : '✓'}</td>
                    </tr>
                `;
            }).join('');
        })
        .catch(error => console.error('Error loading devices:', error));
}

function updateTimestamp() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-US', { hour12: false });
    const elem = document.getElementById('last-update');
    if (elem) {
        elem.textContent = `Last updated: ${timeStr}`;
    }
}

function refreshData() {
    // Update last update time
    updateTimestamp();

    // Add refresh animation
    const btn = document.querySelector('.btn-refresh i');
    if (btn) {
        btn.classList.add('fa-spin');
        setTimeout(() => btn.classList.remove('fa-spin'), 1000);
    }

    loadDashboardStats();
    loadAlerts();
    loadRecentDevices();
}

function filterDevicesByGroup(groupName) {
    console.log('Filtering by:', groupName);
    // This will be called from sidebar
}

// Uptime Chart Modal
let chartInstance = null;

function showUptimeChart(filterValue, filterType) {
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'chart-modal';
    modal.innerHTML = `
        <div class="chart-modal-content">
            <div class="chart-modal-header">
                <h3><i class="fas fa-chart-line"></i> Uptime Overview: ${filterValue}</h3>
                <button class="chart-modal-close" onclick="closeChartModal()">&times;</button>
            </div>
            <div class="chart-modal-body">
                <canvas id="uptime-chart"></canvas>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    // Fetch data and render chart
    auth.fetch(`/api/v1/devices?${filterType === 'region' ? 'region' : 'type'}=${encodeURIComponent(filterValue)}`)
        .then(r => r.json())
        .then(devices => {
            renderUptimeChart(devices, filterValue);
        })
        .catch(error => {
            console.error('Error loading chart data:', error);
            closeChartModal();
        });

    // Close on backdrop click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeChartModal();
    });
}

function closeChartModal() {
    const modal = document.querySelector('.chart-modal');
    if (modal) {
        if (chartInstance) {
            chartInstance.destroy();
            chartInstance = null;
        }
        modal.remove();
    }
}

function renderUptimeChart(devices, title) {
    const ctx = document.getElementById('uptime-chart');
    if (!ctx) return;

    // Calculate uptime statistics over time (simulated last 24 hours)
    const hours = 24;
    const labels = [];
    const onlineData = [];
    const offlineData = [];
    const totalData = [];

    for (let i = hours; i >= 0; i--) {
        const hour = new Date();
        hour.setHours(hour.getHours() - i);
        labels.push(hour.getHours() + ':00');

        // Simulate historical data based on current status
        const online = devices.filter(d => d.ping_status === 'Up').length;
        const offline = devices.filter(d => d.ping_status === 'Down').length;
        const total = devices.length;

        // Add slight random variation to simulate historical changes
        const variance = Math.floor(Math.random() * 3) - 1;
        onlineData.push(Math.max(0, Math.min(total, online + variance)));
        offlineData.push(Math.max(0, Math.min(total, offline - variance)));
        totalData.push(total);
    }

    if (chartInstance) {
        chartInstance.destroy();
    }

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Online',
                    data: onlineData,
                    borderColor: '#00a86b',
                    backgroundColor: 'rgba(0, 168, 107, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Offline',
                    data: offlineData,
                    borderColor: '#dc3545',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.5,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                },
                title: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    },
                    title: {
                        display: true,
                        text: 'Device Count'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time (Last 24 Hours)'
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

// Close modal on ESC key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeChartModal();
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    refreshData();
    startAutoRefresh(30000);

    // Add severity filter event listener
    const severityFilter = document.getElementById('severity-filter');
    if (severityFilter) {
        severityFilter.addEventListener('change', filterAndDisplayAlerts);
    }
});