// Host Group Configuration Management

let availableGroups = [];
let selectedGroups = new Set();

// Show alert message
function showAlert(message, type = 'success') {
    const alertContainer = document.getElementById('alert-container');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        ${message}
    `;
    alertContainer.innerHTML = '';
    alertContainer.appendChild(alert);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

// Update selection count
function updateSelectionCount() {
    const countElement = document.getElementById('selection-count');
    const saveBtn = document.getElementById('save-config-btn');

    if (selectedGroups.size > 0) {
        countElement.textContent = `${selectedGroups.size} selected`;
        countElement.style.display = 'inline-block';
        saveBtn.style.display = 'inline-flex';
    } else {
        countElement.style.display = 'none';
        saveBtn.style.display = 'none';
    }
}

// Fetch Zabbix host groups
document.getElementById('fetch-groups-btn').addEventListener('click', async () => {
    const btn = document.getElementById('fetch-groups-btn');
    const originalText = btn.innerHTML;

    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> Fetching...';

    try {
        const response = await auth.fetch('/api/v1/config/zabbix-hostgroups');
        if (!response.ok) {
            throw new Error('Failed to fetch host groups');
        }

        const data = await response.json();
        availableGroups = data.hostgroups;

        // Also fetch currently monitored groups to pre-select them
        const monitoredResponse = await auth.fetch('/api/v1/config/monitored-hostgroups');
        const monitoredData = await monitoredResponse.json();
        const monitoredGroupIds = new Set(monitoredData.monitored_groups.map(g => g.groupid));
        const monitoredDisplayNames = {};
        monitoredData.monitored_groups.forEach(g => {
            monitoredDisplayNames[g.groupid] = g.display_name;
        });

        selectedGroups = monitoredGroupIds;

        renderHostGroups(monitoredDisplayNames);
        updateSelectionCount();

        showAlert(`Loaded ${availableGroups.length} host groups from Zabbix`, 'success');
    } catch (error) {
        showAlert(`Error: ${error.message}`, 'error');
        console.error('Error fetching host groups:', error);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
});

// Render host groups
function renderHostGroups(monitoredDisplayNames = {}) {
    const container = document.getElementById('hostgroups-list');

    if (availableGroups.length === 0) {
        container.innerHTML = `
            <p style="text-align: center; color: #999; grid-column: 1 / -1;">
                No host groups found
            </p>
        `;
        return;
    }

    container.innerHTML = availableGroups.map(group => {
        const isSelected = selectedGroups.has(group.groupid);
        const displayName = monitoredDisplayNames[group.groupid] || group.name;

        return `
            <div class="hostgroup-item ${isSelected ? 'selected' : ''}" data-groupid="${group.groupid}">
                <div style="display: flex; align-items: center;">
                    <input type="checkbox"
                           id="group-${group.groupid}"
                           value="${group.groupid}"
                           ${isSelected ? 'checked' : ''}
                           onchange="toggleGroup('${group.groupid}')">
                    <label for="group-${group.groupid}">${group.name}</label>
                </div>
                <input type="text"
                       placeholder="Display name (optional)"
                       id="display-${group.groupid}"
                       value="${displayName}">
            </div>
        `;
    }).join('');
}

// Toggle group selection
function toggleGroup(groupid) {
    const checkbox = document.getElementById(`group-${groupid}`);
    const item = document.querySelector(`[data-groupid="${groupid}"]`);

    if (checkbox.checked) {
        selectedGroups.add(groupid);
        item.classList.add('selected');
    } else {
        selectedGroups.delete(groupid);
        item.classList.remove('selected');
    }

    updateSelectionCount();
}

// Save configuration
document.getElementById('save-config-btn').addEventListener('click', async () => {
    const btn = document.getElementById('save-config-btn');
    const originalText = btn.innerHTML;

    if (selectedGroups.size === 0) {
        showAlert('Please select at least one host group', 'error');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> Saving...';

    try {
        const groups = Array.from(selectedGroups).map(groupid => {
            const group = availableGroups.find(g => g.groupid === groupid);
            const displayNameInput = document.getElementById(`display-${groupid}`);
            const displayName = displayNameInput ? displayNameInput.value.trim() : '';

            return {
                groupid,
                name: group.name,
                display_name: displayName || group.name
            };
        });

        const response = await auth.fetch('/api/v1/config/monitored-hostgroups', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ groups })
        });

        if (!response.ok) {
            throw new Error('Failed to save configuration');
        }

        const result = await response.json();
        showAlert(`Configuration saved successfully! ${result.saved} host groups configured.`, 'success');

    } catch (error) {
        showAlert(`Error: ${error.message}`, 'error');
        console.error('Error saving configuration:', error);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
});

// Load Georgian cities on page load
async function loadGeorgianCities() {
    try {
        const response = await auth.fetch('/api/v1/config/georgian-cities');
        if (!response.ok) {
            throw new Error('Failed to fetch cities');
        }

        const data = await response.json();
        const citiesContainer = document.getElementById('cities-list');

        if (data.cities.length === 0) {
            citiesContainer.innerHTML = `
                <p style="text-align: center; color: #999; grid-column: 1 / -1;">
                    No cities configured
                </p>
            `;
            return;
        }

        citiesContainer.innerHTML = data.cities.map(city => `
            <div class="city-item">
                <strong>${city.name_en}</strong><br>
                <small>${city.region_name}</small><br>
                <small style="color: #666;">${city.latitude.toFixed(4)}, ${city.longitude.toFixed(4)}</small>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading cities:', error);
        document.getElementById('cities-list').innerHTML = `
            <p style="text-align: center; color: #dc3545; grid-column: 1 / -1;">
                Error loading cities: ${error.message}
            </p>
        `;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadGeorgianCities();
});
