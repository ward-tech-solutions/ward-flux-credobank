// Device Edit Modal Functions
let currentDevice = null;
let cities = [];

// Load cities for the branch selector
async function loadCities() {
    try {
        const response = await auth.fetch('/api/v1/config/georgian-cities');
        const data = await response.json();
        cities = data.cities || [];

        const select = document.getElementById('edit-branch');
        select.innerHTML = cities.map(city =>
            `<option value="${city.name_en}">${city.name_en}</option>`
        ).join('');
    } catch (error) {
        console.error('Failed to load cities:', error);
    }
}

// Open edit modal
async function openEditModal(hostid) {
    const modal = document.getElementById('edit-modal');
    const loadingEl = document.getElementById('edit-loading');
    const formEl = document.getElementById('edit-form');
    const alertEl = document.getElementById('edit-alert');

    // Show modal and loading state
    modal.style.display = 'flex';
    loadingEl.style.display = 'flex';
    formEl.style.display = 'none';
    alertEl.style.display = 'none';

    try {
        // Load cities if not already loaded
        if (cities.length === 0) {
            await loadCities();
        }

        // Fetch device details
        const response = await auth.fetch(`/api/v1/devices/${hostid}`);
        const device = await response.json();

        currentDevice = device;

        // Populate form
        document.getElementById('edit-hostid').value = device.hostid;
        document.getElementById('edit-hostname').value = device.hostname;
        document.getElementById('edit-visible-name').value = device.display_name;
        document.getElementById('edit-ip').value = device.ip;

        // Set branch
        const branchSelect = document.getElementById('edit-branch');
        branchSelect.value = device.branch;

        // Show form
        loadingEl.style.display = 'none';
        formEl.style.display = 'block';

    } catch (error) {
        console.error('Failed to load device:', error);
        showEditAlert('Failed to load device information', 'error');
        loadingEl.style.display = 'none';
    }
}

// Close edit modal
function closeEditModal(event) {
    if (event && event.target.id !== 'edit-modal') return;

    const modal = document.getElementById('edit-modal');
    modal.style.display = 'none';
    currentDevice = null;

    // Reset form
    document.getElementById('device-edit-form').reset();
}

// Handle device update
async function handleDeviceUpdate(event) {
    event.preventDefault();

    const btn = document.getElementById('update-btn');
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

    const hostid = document.getElementById('edit-hostid').value;
    const hostname = document.getElementById('edit-hostname').value.trim();
    const visibleName = document.getElementById('edit-visible-name').value.trim();
    const ip = document.getElementById('edit-ip').value.trim();
    const branch = document.getElementById('edit-branch').value;

    try {
        const response = await auth.fetch(`/api/v1/hosts/${hostid}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                hostname: hostname,
                visible_name: visibleName,
                ip_address: ip,
                branch: branch
            })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showEditAlert('Device updated successfully!', 'success');

            // Reload devices after 1 second
            setTimeout(() => {
                closeEditModal();
                loadDevices();
            }, 1000);
        } else {
            showEditAlert(result.error || 'Failed to update device', 'error');
            btn.disabled = false;
            btn.innerHTML = originalHTML;
        }

    } catch (error) {
        console.error('Update error:', error);
        showEditAlert('Failed to update device. Please try again.', 'error');
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }
}

// Show alert in edit modal
function showEditAlert(message, type) {
    const alertEl = document.getElementById('edit-alert');
    alertEl.textContent = message;
    alertEl.className = `alert alert-${type}`;
    alertEl.style.display = 'block';

    if (type === 'success') {
        setTimeout(() => {
            alertEl.style.display = 'none';
        }, 3000);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Close modal when pressing Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeEditModal();
        }
    });
});
