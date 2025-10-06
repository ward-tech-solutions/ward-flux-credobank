// Enhanced device modal with incident timeline
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
                document.getElementById('modal-title').textContent = 'Device Details';
                modalBody.innerHTML = `<div style="padding: 2.5rem; text-align: center; color: var(--danger-red);">
                    <i class="fas fa-ban" style="font-size: 2rem; display: block; margin-bottom: 0.75rem;"></i>
                    ${device.error}
                </div>`;
                return;
            }

            displayEnhancedDeviceModal(device);
        })
        .catch(error => {
            console.error('Error:', error);
            modalBody.innerHTML = '<div style="text-align: center; padding: 3rem; color: var(--danger-red);"><i class="fas fa-exclamation-triangle" style="font-size: 2rem;"></i><p>Failed to load device information</p></div>';
        });
}

function displayEnhancedDeviceModal(device) {
    const status = device.ping_status || device.available || 'Unknown';
    const isOnline = status === 'Up';
    const icon = getDeviceIcon(device.device_type);

    // Calculate incident data from history
    const incidentData = calculateIncidentTimeline(device.ping_data?.history || []);

    // If device is offline and we don't have downSince from history, try to get it from triggers
    if (!isOnline && !incidentData.downSince && device.triggers && device.triggers.length > 0) {
        const oldestTrigger = device.triggers.reduce((oldest, t) => {
            const triggerTime = parseInt(t.lastchange);
            const oldestTime = parseInt(oldest.lastchange);
            return triggerTime < oldestTime ? t : oldest;
        });

        if (oldestTrigger && oldestTrigger.lastchange) {
            const downStartMs = parseInt(oldestTrigger.lastchange) * 1000;
            incidentData.downSince = new Date(downStartMs).toLocaleString();
            incidentData.currentDowntime = formatDuration(Date.now() - downStartMs);
        }
    }

    document.getElementById('modal-title').innerHTML = `<i class="fas ${icon}"></i> ${device.display_name}`;

    document.getElementById('modal-body').innerHTML = `
        <!-- Status Banner -->
        <div class="status-banner ${isOnline ? 'banner-online' : 'banner-offline'}">
            <div class="banner-icon">
                <i class="fas fa-${isOnline ? 'check-circle' : 'times-circle'}"></i>
            </div>
            <div class="banner-content">
                <div class="banner-title">${status}</div>
                <div class="banner-subtitle">${isOnline ? 'Device is responding normally' : 'Device is not responding'}</div>
                ${!isOnline ? `
                    <div class="banner-downtime" style="margin-top: 0.75rem; padding: 0.75rem; background: rgba(0,0,0,0.2); border-radius: 6px; font-size: 0.95rem;">
                        ${incidentData.downSince ? `
                            <div style="margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
                                <i class="fas fa-calendar-times" style="width: 16px;"></i>
                                <div><strong>Down since:</strong> ${incidentData.downSince}</div>
                            </div>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <i class="fas fa-hourglass-half" style="width: 16px;"></i>
                                <div><strong>Downtime:</strong> ${incidentData.currentDowntime}</div>
                            </div>
                        ` : `
                            <i class="fas fa-exclamation-circle"></i> Device is currently offline - timestamp unavailable
                        `}
                    </div>
                ` : ''}
            </div>
        </div>
        
        <!-- Quick Actions Bar -->
        <div class="action-bar">
            <button class="action-btn action-ssh" onclick="openSSHTerminal('${device.hostid}', '${device.display_name}', '${device.ip}')">
                <i class="fas fa-terminal"></i>
                <span>SSH Client</span>
            </button>
            <button class="action-btn" onclick="window.open('http://${device.ip}', '_blank')">
                <i class="fas fa-globe"></i>
                <span>Web UI</span>
            </button>
            <button class="action-btn" onclick="copyToClipboard('${device.ip}')">
                <i class="fas fa-copy"></i>
                <span>Copy IP</span>
            </button>
            <button class="action-btn" onclick="window.location.href='/devices?search=${encodeURIComponent(device.branch)}'">
                <i class="fas fa-building"></i>
                <span>View Branch</span>
            </button>
            <button class="action-btn" onclick="openDeviceModal('${device.hostid}')">
                <i class="fas fa-sync-alt"></i>
                <span>Refresh</span>
            </button>
        </div>
        
        <!-- Device Details Grid -->
        <div class="details-grid">
            <div class="detail-card">
                <div class="detail-icon"><i class="fas fa-map-marker-alt"></i></div>
                <div class="detail-content">
                    <div class="detail-label">Branch</div>
                    <div class="detail-value">${device.branch}</div>
                </div>
            </div>
            <div class="detail-card">
                <div class="detail-icon"><i class="fas fa-map"></i></div>
                <div class="detail-content">
                    <div class="detail-label">Region</div>
                    <div class="detail-value">${device.region}</div>
                </div>
            </div>
            <div class="detail-card">
                <div class="detail-icon"><i class="fas fa-network-wired"></i></div>
                <div class="detail-content">
                    <div class="detail-label">IP Address</div>
                    <div class="detail-value">${device.ip}</div>
                </div>
            </div>
            <div class="detail-card">
                <div class="detail-icon"><i class="fas ${icon}"></i></div>
                <div class="detail-content">
                    <div class="detail-label">Device Type</div>
                    <div class="detail-value">${device.device_type}</div>
                </div>
            </div>
        </div>
        
        <!-- Incident Timeline -->
        ${incidentData.incidents.length > 0 ? `
        <div class="timeline-section">
            <div class="timeline-header">
                <h3><i class="fas fa-history"></i> Incident Timeline</h3>
                <span class="timeline-stats">${incidentData.incidents.length} incidents in last 30 days</span>
            </div>
            <div class="timeline-container">
                ${incidentData.incidents.map(incident => `
                    <div class="timeline-incident ${incident.type}">
                        <div class="incident-marker"></div>
                        <div class="incident-content">
                            <div class="incident-header">
                                <span class="incident-type">${incident.type === 'down' ? '❌ Went Offline' : '✅ Came Online'}</span>
                                <span class="incident-time">${incident.time}</span>
                            </div>
                            ${incident.duration ? `
                                <div class="incident-duration">
                                    <i class="fas fa-hourglass-half"></i> Downtime: ${incident.duration}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
        ` : ''}
        
        <!-- Active Problems -->
        ${device.triggers && device.triggers.length > 0 ? `
        <div class="problems-section">
            <div class="problems-header">
                <h3><i class="fas fa-exclamation-triangle"></i> Active Problems</h3>
                <span class="problems-count">${device.triggers.length}</span>
            </div>
            <div class="problems-list">
                ${device.triggers.map(t => {
                    const startTime = parseInt(t.lastchange) * 1000;
                    const duration = formatDuration(Date.now() - startTime);
                    return `
                        <div class="problem-item severity-${t.priority}">
                            <div class="problem-severity">
                                <span class="severity-badge">${getSeverityName(t.priority)}</span>
                            </div>
                            <div class="problem-details">
                                <div class="problem-description">${t.description}</div>
                                <div class="problem-meta">
                                    <span><i class="fas fa-clock"></i> ${new Date(startTime).toLocaleString()}</span>
                                    <span><i class="fas fa-hourglass-half"></i> ${duration}</span>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        </div>
        ` : ''}
    `;
}

function calculateIncidentTimeline(history) {
    if (!history || history.length === 0) {
        return { incidents: [], currentDowntime: null };
    }

    const sorted = [...history].sort((a, b) => parseInt(a.clock) - parseInt(b.clock));
    const incidents = [];
    let lastStatus = null;
    let downStart = null;
    let currentDowntime = null;

    sorted.forEach((entry, index) => {
        const currentStatus = parseInt(entry.value);
        const timestamp = parseInt(entry.clock) * 1000;

        if (lastStatus !== null && lastStatus !== currentStatus) {
            if (currentStatus === 0) {
                // Went down
                downStart = timestamp;
                incidents.push({
                    type: 'down',
                    time: new Date(timestamp).toLocaleString(),
                    timestamp: timestamp
                });
            } else if (currentStatus === 1 && downStart) {
                // Came back up
                const duration = formatDuration(timestamp - downStart);
                incidents.push({
                    type: 'up',
                    time: new Date(timestamp).toLocaleString(),
                    duration: duration,
                    timestamp: timestamp
                });
                downStart = null;
            }
        }

        lastStatus = currentStatus;
    });

    // Check if currently down
    let downSince = null;
    if (lastStatus === 0 && downStart) {
        currentDowntime = formatDuration(Date.now() - downStart);
        downSince = new Date(downStart).toLocaleString();
    }

    return {
        incidents: incidents.reverse().slice(0, 20),
        currentDowntime: currentDowntime,
        downSince: downSince
    };
}

function formatDuration(ms) {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ${hours % 24}h`;
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m`;
    return `${seconds}s`;
}

function getSeverityName(priority) {
    const severities = ['Not classified', 'Information', 'Warning', 'Average', 'High', 'Disaster'];
    return severities[parseInt(priority)] || 'Unknown';
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

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('✓ Copied: ' + text, 'success');
    }).catch(() => {
        showNotification('Failed to copy', 'error');
    });
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
