// Reports Page Functionality

let downtimeChart = null;
let mttrRegionChart = null;

function switchReportTab(tabName) {
    // Update active tab
    document.querySelectorAll('.report-tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.dataset.tab === tabName) {
            tab.classList.add('active');
        }
    });

    // Update active section
    document.querySelectorAll('.report-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(`${tabName}-report`).classList.add('active');

    // Load data for the selected tab
    if (tabName === 'downtime') {
        loadDowntimeReport();
    } else if (tabName === 'mttr') {
        loadMTTRReport();
    }
}

function loadDowntimeReport() {
    const period = document.getElementById('downtime-period')?.value || 'weekly';
    const region = document.getElementById('downtime-region')?.value || '';

    let url = `/api/reports/downtime?period=${period}`;
    if (region) url += `&region=${region}`;

    fetch(url)
        .then(r => r.json())
        .then(data => {
            // Update summary cards
            document.getElementById('total-devices-report').textContent = data.total_devices;
            document.getElementById('avg-availability').textContent = data.summary.average_availability + '%';
            document.getElementById('total-downtime').textContent = data.summary.total_downtime_hours.toFixed(1) + 'h';
            document.getElementById('devices-with-issues').textContent = data.summary.devices_with_downtime;

            // Populate table
            const tbody = document.getElementById('downtime-table-body');
            tbody.innerHTML = data.devices.map(device => `
                <tr>
                    <td>${device.name}</td>
                    <td>${device.region}</td>
                    <td>${device.device_type}</td>
                    <td>
                        <div class="availability-bar">
                            <div class="availability-fill" style="width: ${device.availability_percent}%; background: ${device.availability_percent > 99 ? 'var(--success-green)' : device.availability_percent > 95 ? 'var(--warning-orange)' : 'var(--danger-red)'}"></div>
                            <span>${device.availability_percent}%</span>
                        </div>
                    </td>
                    <td>${device.downtime_hours.toFixed(2)}h</td>
                    <td><span class="badge-count">${device.incidents}</span></td>
                </tr>
            `).join('');

            // Render downtime chart
            renderDowntimeChart(data.devices);

            // Populate region dropdown if empty
            const regionSelect = document.getElementById('downtime-region');
            if (regionSelect.options.length === 1) {
                const regions = [...new Set(data.devices.map(d => d.region))];
                regions.forEach(region => {
                    const option = document.createElement('option');
                    option.value = region;
                    option.textContent = region;
                    regionSelect.appendChild(option);
                });
            }
        })
        .catch(error => console.error('Error loading downtime report:', error));
}

function renderDowntimeChart(devices) {
    const ctx = document.getElementById('downtime-chart');
    if (!ctx) return;

    // Group by region
    const regionData = {};
    devices.forEach(device => {
        if (!regionData[device.region]) {
            regionData[device.region] = { downtime: 0, count: 0 };
        }
        regionData[device.region].downtime += device.downtime_hours;
        regionData[device.region].count++;
    });

    const labels = Object.keys(regionData);
    const data = labels.map(region => regionData[region].downtime);

    if (downtimeChart) {
        downtimeChart.destroy();
    }

    downtimeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Total Downtime (hours)',
                data: data,
                backgroundColor: 'rgba(220, 53, 69, 0.7)',
                borderColor: 'rgb(220, 53, 69)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 3,
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Downtime by Region'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Hours'
                    }
                }
            }
        }
    });
}

function loadMTTRReport() {
    auth.fetch('/api/v1/reports/mttr-extended')
        .then(r => r.json())
        .then(data => {
            // Update summary
            document.getElementById('overall-mttr').textContent = data.avg_mttr_minutes || 0;
            document.getElementById('total-incidents').textContent = data.total_incidents || 0;

            // Update trend
            const trendCard = document.getElementById('trend-card');
            const trendLabel = document.getElementById('trend-label');
            if (data.trends.improving) {
                trendCard.className = 'mttr-card trend-improving';
                trendLabel.textContent = 'Improving';
            } else {
                trendCard.className = 'mttr-card trend-worsening';
                trendLabel.textContent = 'Needs Attention';
            }

            // Render MTTR by region chart
            renderMTTRChart(data.mttr_by_region || {});

            // Populate problem devices table
            const tbody = document.getElementById('problem-devices-tbody');
            if (data.top_problem_devices && data.top_problem_devices.length > 0) {
                tbody.innerHTML = data.top_problem_devices.map((device, index) => `
                    <tr>
                        <td><strong>${index + 1}</strong></td>
                        <td>${device.name}</td>
                        <td>${device.region}</td>
                        <td><span class="badge-count">${device.incident_count}</span></td>
                        <td>${device.downtime_minutes} min</td>
                        <td><button class="btn-small" onclick="window.location.href='/device/${device.hostid}'">View</button></td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="6" class="loading-cell">No problem devices found</td></tr>';
            }
        })
        .catch(error => console.error('Error loading MTTR report:', error));
}

function renderMTTRChart(mttrByRegion) {
    const ctx = document.getElementById('mttr-region-chart');
    if (!ctx) return;

    const labels = Object.keys(mttrByRegion);
    const data = Object.values(mttrByRegion);

    if (mttrRegionChart) {
        mttrRegionChart.destroy();
    }

    mttrRegionChart = new Chart(ctx, {
        type: 'horizontalBar',
        data: {
            labels: labels,
            datasets: [{
                label: 'MTTR (minutes)',
                data: data,
                backgroundColor: 'rgba(26, 143, 255, 0.7)',
                borderColor: 'rgb(26, 143, 255)',
                borderWidth: 2
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Minutes'
                    }
                }
            }
        }
    });
}

function exportReport(reportType) {
    // Convert table data to CSV
    const table = document.querySelector(`#${reportType}-report .data-table`);
    let csv = [];

    // Headers
    const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent);
    csv.push(headers.join(','));

    // Rows
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
        const cols = Array.from(row.querySelectorAll('td')).map(td => {
            return '"' + td.textContent.trim().replace(/"/g, '""') + '"';
        });
        csv.push(cols.join(','));
    });

    // Download
    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${reportType}_report_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);

    showNotification('Report exported successfully', 'success');
}

function loadAllReports() {
    const activeTab = document.querySelector('.report-tab.active').dataset.tab;
    switchReportTab(activeTab);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadDowntimeReport();
});
