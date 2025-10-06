// Enhanced map functionality with clustering
let map;
let markers = [];
let currentFilter = 'all';
let currentRegion = '';
let allDevices = [];
let markerClusterGroup = null;
let hasInitialViewport = false;

const georgiaCenter = [42.3154, 43.3569];

function initMap() {
    map = L.map('map', {
        center: georgiaCenter,
        zoom: 7,
        minZoom: 6,
        maxZoom: 18,
        zoomControl: false,
        scrollWheelZoom: true,
        doubleClickZoom: true,
        preferCanvas: true
    });

    const tileLayers = getTileLayers();
    tileLayers.Light.addTo(map);
    L.control.layers(tileLayers, null, { position: 'topleft', hideSingleBase: true }).addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);
    L.control.scale({ position: 'bottomleft', metric: true, imperial: false }).addTo(map);

    // Initialize marker cluster group with custom options
    markerClusterGroup = L.markerClusterGroup({
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        maxClusterRadius: 60,
        iconCreateFunction: function(cluster) {
            const markers = cluster.getAllChildMarkers();
            const total = markers.length;
            const online = markers.filter(m => m.deviceData && m.deviceData.online).length;
            const offline = total - online;

            let className = 'marker-cluster marker-cluster-';
            if (offline === 0) {
                className += 'online';
            } else if (online === 0) {
                className += 'offline';
            } else {
                className += 'mixed';
            }

            return L.divIcon({
                html: `<div><span>${total}</span></div>`,
                className: className,
                iconSize: L.point(40, 40)
            });
        }
    });

    map.addLayer(markerClusterGroup);
    addRegionControl();
    addResetControl();

    loadDevices();
    setInterval(loadDevices, 30000);
}

function getTileLayers() {
    const attribution = '&copy; OpenStreetMap contributors · &copy; CARTO · &copy; Esri';
    return {
        Light: L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution,
            subdomains: 'abcd',
            maxZoom: 18
        }),
        Voyager: L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
            attribution,
            subdomains: 'abcd',
            maxZoom: 18
        }),
        Satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution,
            maxZoom: 18
        })
    };
}

function loadDevices() {
    auth.fetch('/api/v1/devices')
        .then(r => r.json())
        .then(devices => {
            allDevices = devices;
            populateRegionControl(devices);
            applyMapFilters({ fitToMarkers: !hasInitialViewport });
            hasInitialViewport = true;
        })
        .catch(error => console.error('Failed to load map devices:', error));
}

function applyMapFilters({ fitToMarkers = false } = {}) {
    let filtered = allDevices.slice();

    if (currentRegion) {
        filtered = filtered.filter(device => device.region === currentRegion);
    }

    if (currentFilter === 'online') {
        filtered = filtered.filter(device => device.ping_status === 'Up');
    } else if (currentFilter === 'offline') {
        filtered = filtered.filter(device => device.ping_status === 'Down');
    }

    updateMarkers(filtered, { fitToMarkers });
}

function updateMarkers(devices, { fitToMarkers = false } = {}) {
    markerClusterGroup.clearLayers();
    markers = [];

    // Group devices by exact coordinates to avoid overlapping
    const locationGroups = {};

    devices.forEach(device => {
        const coords = { lat: device.latitude, lng: device.longitude };
        if (!coords.lat || !coords.lng) return;

        const key = `${coords.lat.toFixed(6)},${coords.lng.toFixed(6)}`;
        if (!locationGroups[key]) {
            locationGroups[key] = { coords, devices: [] };
        }
        locationGroups[key].devices.push(device);
    });

    Object.values(locationGroups).forEach(({ coords, devices: devicesAtLocation }) => {
        const onlineCount = devicesAtLocation.filter(d => d.ping_status === 'Up').length;
        const isOnline = onlineCount === devicesAtLocation.length;

        const markerHtml = `
            <div class="map-marker ${isOnline ? 'marker-online' : 'marker-offline'}">
                <span>${devicesAtLocation.length}</span>
            </div>
        `;

        const icon = L.divIcon({
            html: markerHtml,
            className: '',
            iconSize: [40, 40],
            iconAnchor: [20, 20]
        });

        const marker = L.marker([coords.lat, coords.lng], { icon })
            .bindPopup(createPopup(devicesAtLocation), { maxWidth: 350, maxHeight: 400 });

        marker.deviceData = { online: isOnline, count: devicesAtLocation.length };
        markers.push(marker);
        markerClusterGroup.addLayer(marker);
    });

    if (fitToMarkers && markers.length > 0) {
        const bounds = markerClusterGroup.getBounds();
        if (bounds.isValid()) {
            map.flyToBounds(bounds.pad(0.15), { duration: 0.8, maxZoom: 12 });
        }
    }
}

function getMarkerCoordinates(devicesAtLocation) {
    const deviceWithCoords = devicesAtLocation.find(d => typeof d.latitude === 'number' && typeof d.longitude === 'number');
    if (deviceWithCoords) {
        return { lat: deviceWithCoords.latitude, lng: deviceWithCoords.longitude };
    }

    const fallbackRegion = devicesAtLocation[0]?.region;
    if (!fallbackRegion) return null;

    return regionToLatLng(fallbackRegion);
}

function regionToLatLng(region) {
    const regionCoordinates = {
        Tbilisi: { lat: 41.7151, lng: 44.8271 },
        'Kvemo Kartli': { lat: 41.541, lng: 44.961 },
        Kakheti: { lat: 41.6488, lng: 45.6942 },
        'Mtskheta-Mtianeti': { lat: 42.1, lng: 44.7 },
        'Samtskhe-Javakheti': { lat: 41.601, lng: 43.5 },
        'Shida Kartli': { lat: 42.025, lng: 43.95 },
        Imereti: { lat: 42.265, lng: 42.7 },
        Samegrelo: { lat: 42.52, lng: 41.87 },
        Guria: { lat: 41.99, lng: 42.11 },
        Achara: { lat: 41.641, lng: 41.65 },
        Other: { lat: georgiaCenter[0], lng: georgiaCenter[1] }
    };

    return regionCoordinates[region] || regionCoordinates.Other;
}

function createPopup(devices) {
    const onlineCount = devices.filter(d => d.ping_status === 'Up').length;
    const offlineCount = devices.length - onlineCount;

    const deviceList = devices.map(device => {
        const status = device.ping_status || device.available || 'Unknown';
        const statusClass = status === 'Up' || status === 'Available' ? 'color: var(--success-green);' :
            (status === 'Down' || status === 'Unavailable' ? 'color: var(--danger-red);' : 'color: var(--warning-orange);');
        return `
            <li style="margin-bottom: 0.35rem;">
                <div class="device-item-row">
                    <span class="device-name">${device.display_name}</span>
                    <span class="device-status" style="${statusClass}">${status}</span>
                </div>
                <span class="device-ip">${device.ip}</span>
            </li>
        `;
    }).join('');

    return `
        <div class="map-popup">
            <header>
                <h4>${devices[0].branch}</h4>
                <div class="region">${devices[0].region}</div>
            </header>
            <section class="stats">
                <div><span class="value">${devices.length}</span><span class="label">Total</span></div>
                <div><span class="value online">${onlineCount}</span><span class="label">Online</span></div>
                <div><span class="value offline">${offlineCount}</span><span class="label">Offline</span></div>
            </section>
            <div class="device-scroll">
                <ul>${deviceList}</ul>
            </div>
            <button class="map-popup-action" onclick="window.location.href='/devices?search=${devices[0].branch}'">
                View Devices
            </button>
        </div>
    `;
}

function filterMap(type) {
    currentFilter = type;

    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`btn-${type}`).classList.add('active');

    applyMapFilters();
}

function addRegionControl() {
    const control = L.control({ position: 'topright' });

    control.onAdd = function () {
        const container = L.DomUtil.create('div', 'map-region-control');
        container.innerHTML = `
            <label for="map-region-select">Jump to region</label>
            <select id="map-region-select">
                <option value="">All Regions</option>
            </select>
        `;
        L.DomEvent.disableClickPropagation(container);
        return container;
    };

    control.addTo(map);
}

function populateRegionControl(devices) {
    const select = document.getElementById('map-region-select');
    if (!select) return;

    const regions = Array.from(new Set(devices.map(d => d.region))).filter(Boolean).sort();

    const currentValue = select.value;
    select.innerHTML = '<option value="">All Regions</option>' +
        regions.map(region => `<option value="${region}">${region}</option>`).join('');

    select.value = currentValue;

    select.onchange = (event) => {
        currentRegion = event.target.value;
        const shouldFit = Boolean(currentRegion);
        applyMapFilters({ fitToMarkers: shouldFit });
    };
}

function addResetControl() {
    const control = L.control({ position: 'bottomleft' });

    control.onAdd = function () {
        const container = L.DomUtil.create('div', 'map-reset-control');
        container.innerHTML = `
            <button type="button" title="Reset view">
                <i class="fas fa-compass"></i>
            </button>
        `;
        container.querySelector('button').addEventListener('click', () => {
            currentRegion = '';
            const select = document.getElementById('map-region-select');
            if (select) select.value = '';
            applyMapFilters({ fitToMarkers: true });
        });
        L.DomEvent.disableClickPropagation(container);
        return container;
    };

    control.addTo(map);
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('map')) {
        initMap();
    }
});
