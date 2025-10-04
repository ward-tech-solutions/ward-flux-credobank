// Enterprise Network Topology Visualization
// Professional NOC-grade implementation

let network = null;
let allNodes = null;
let allEdges = null;
let visibleNodes = null;
let visibleEdges = null;
let currentView = 'hierarchical';
let detailsWebSocket = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('[NOC] Initializing enterprise topology...');
    initializeTopology();
    setupEventHandlers();
});

// Main initialization
function initializeTopology() {
    showLoading(true);
    loadTopologyData();
}

// Load data from API
function loadTopologyData() {
    fetch('/api/topology?view=hierarchical&limit=200')
        .then(res => res.ok ? res.json() : Promise.reject('API Error'))
        .then(data => {
            console.log('[NOC] Loaded:', data.stats);
            console.log('[NOC] Nodes:', data.nodes.length, 'Edges:', data.edges.length);

            // Ensure all nodes have proper level assignment
            data.nodes.forEach(node => {
                if (node.level === undefined || node.level === null) {
                    // Default to level 2 for end devices
                    node.level = 2;
                }
                // Ensure numeric level
                node.level = parseInt(node.level);
            });

            // Log level distribution
            const levels = data.nodes.reduce((acc, n) => {
                acc[n.level] = (acc[n.level] || 0) + 1;
                return acc;
            }, {});
            console.log('[NOC] Level distribution:', levels);

            allNodes = new vis.DataSet(data.nodes);
            allEdges = new vis.DataSet(data.edges);
            visibleNodes = new vis.DataSet(data.nodes);
            visibleEdges = new vis.DataSet(data.edges);

            updateStatistics(data.stats);
            buildDeviceTree(data.nodes);
            createNetworkVisualization();

            // Load bandwidth data for core router edges after network is created
            setTimeout(() => {
                loadCoreRouterBandwidth(data.nodes);
            }, 1000);

            showLoading(false);
        })
        .catch(err => {
            console.error('[NOC ERROR]', err);
            showError('Failed to load network topology');
            showLoading(false);
        });
}

// Load bandwidth data for core router interfaces
async function loadCoreRouterBandwidth(nodes) {
    // Find core routers (level 0)
    const coreRouters = nodes.filter(n => n.level === 0);

    for (const router of coreRouters) {
        try {
            const response = await fetch(`/api/v1/router/${router.id}/interfaces`);
            if (!response.ok) continue;

            const data = await response.json();
            const interfaces = data.interfaces || {};

            console.log(`[BANDWIDTH] Loaded ${Object.keys(interfaces).length} interfaces for ${router.label}`);

            // Update edges from this router with bandwidth labels
            updateEdgeBandwidth(router.id, interfaces);

        } catch (error) {
            console.error(`[BANDWIDTH] Failed to load interfaces for ${router.label}:`, error);
        }
    }
}

// Update edge labels with bandwidth data
function updateEdgeBandwidth(routerId, interfaces) {
    // Get all edges from this router
    const edges = allEdges.get().filter(e => e.from === routerId);

    edges.forEach(edge => {
        // Try to match edge to interface by looking at edge title or connected device
        const toNode = allNodes.get(edge.to);
        if (!toNode) return;

        // Extract branch name from the destination node
        const branchName = (toNode.branch || toNode.label || '').toLowerCase().replace(/[^a-z0-9]/g, '_');

        // Find matching interface by description
        for (const [ifaceName, ifaceData] of Object.entries(interfaces)) {
            const desc = (ifaceData.description || '').toLowerCase().replace(/[^a-z0-9]/g, '_');

            if (desc.includes(branchName) || branchName.includes(desc.split('_')[0])) {
                // Found matching interface - update edge with bandwidth
                const bwInMbps = ifaceData.bandwidth_in / 1000000;
                const bwOutMbps = ifaceData.bandwidth_out / 1000000;

                allEdges.update({
                    id: edge.id,
                    label: `▼ ${bwInMbps.toFixed(1)}M  ▲ ${bwOutMbps.toFixed(1)}M`,
                    width: 5,
                    color: {
                        color: ifaceData.status === 'up' ? '#5EBBA8' : '#ef4444',
                        highlight: '#72CFB8',
                        hover: '#72CFB8'
                    },
                    font: {
                        size: 18,                            // Larger font
                        color: '#FFFFFF',                    // White text
                        background: 'rgba(28, 33, 40, 0.95)', // Solid dark background
                        strokeWidth: 3,                      // Border around text
                        strokeColor: '#000000',              // Black border
                        align: 'horizontal',
                        face: 'Monaco, Consolas, Courier, monospace',
                        vadjust: -2,                         // Slightly above line
                        bold: true,
                        mod: 'bold'
                    },
                    title: edge.title + `\n\nInterface: ${ifaceName}\n▼ In: ${bwInMbps.toFixed(2)} Mbps\n▲ Out: ${bwOutMbps.toFixed(2)} Mbps\nStatus: ${ifaceData.status.toUpperCase()}`
                });

                console.log(`[BANDWIDTH] Updated edge to ${toNode.label}: ↓${bwInMbps.toFixed(1)}M ↑${bwOutMbps.toFixed(1)}M`);
                break;
            }
        }
    });
}

// Create network visualization
function createNetworkVisualization() {
    const container = document.getElementById('network-canvas');
    if (!container) return;

    const options = {
        nodes: {
            shape: 'dot',
            size: 30,
            font: {
                size: 18,
                color: '#F3F4F6',
                face: 'Arial, sans-serif',
                background: '#1c2128',
                strokeWidth: 0,
                bold: {
                    color: '#FFFFFF',
                    size: 18,
                    mod: 'bold'
                }
            },
            borderWidth: 3,
            borderWidthSelected: 5,
            shadow: {
                enabled: true,
                color: 'rgba(94, 187, 168, 0.5)',
                size: 15,
                x: 0,
                y: 0
            }
        },
        edges: {
            width: 5,
            color: {
                color: '#30363d',
                highlight: '#5EBBA8',
                hover: '#72CFB8'
            },
            smooth: {
                enabled: true,
                type: 'cubicBezier',
                roundness: 0.4
            },
            font: {
                size: 18,                              // Larger default font
                color: '#FFFFFF',                      // White text
                background: 'rgba(28, 33, 40, 0.95)',  // Dark background
                strokeWidth: 3,                        // Text border
                strokeColor: '#000000',                // Black border
                align: 'horizontal',
                face: 'Monaco, Consolas, Courier, monospace',
                vadjust: -2,                           // Above line
                bold: true,
                mod: 'bold'
            },
            arrows: {
                to: { enabled: false }
            },
            selectionWidth: 3
        },
        physics: {
            enabled: true,
            stabilization: {
                enabled: true,
                iterations: 500,
                updateInterval: 20,
                fit: true
            },
            hierarchicalRepulsion: {
                nodeDistance: 450,        // More spacing
                centralGravity: 0.0,
                springLength: 500,        // Longer springs
                springConstant: 0.001,    // Softer springs
                damping: 0.09,
                avoidOverlap: 1.2         // More overlap avoidance
            },
            solver: 'hierarchicalRepulsion',
            timestep: 0.25,
            adaptiveTimestep: true,
            maxVelocity: 30,
            minVelocity: 0.3
        },
        layout: {
            hierarchical: {
                enabled: currentView === 'hierarchical',
                direction: 'UD',           // Top to bottom
                sortMethod: 'directed',
                nodeSpacing: 350,          // Increased horizontal spacing
                treeSpacing: 400,          // More tree spacing
                levelSeparation: 400,      // More vertical spacing
                blockShifting: true,
                edgeMinimization: true,
                parentCentralization: true,
                shakeTowards: 'leaves'
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 200,
            navigationButtons: false,
            keyboard: true,
            zoomView: true,
            dragView: true,
            zoomSpeed: 0.4,
            multiselect: false,
            selectConnectedEdges: true
        }
    };

    try {
        network = new vis.Network(container, {
            nodes: visibleNodes,
            edges: visibleEdges
        }, options);

        // Force dark background
        setTimeout(() => {
            const canvas = container.querySelector('canvas');
            if (canvas) canvas.style.background = '#0d1117';
        }, 100);

        // Event handlers
        network.on('click', handleNetworkClick);
        network.on('hoverNode', handleNodeHover);
        network.on('blurNode', handleNodeBlur);
        network.on('doubleClick', handleDoubleClick);

        network.on('stabilizationProgress', (params) => {
            const progress = Math.round((params.iterations / params.total) * 100);
            console.log('[NOC] Stabilizing...', progress + '%');
        });

        network.on('stabilizationIterationsDone', () => {
            console.log('[NOC] Stabilization complete');
            network.fit({
                animation: {
                    duration: 1000,
                    easingFunction: 'easeInOutQuad'
                }
            });
            setTimeout(() => {
                network.setOptions({ physics: { enabled: false } });
            }, 500);
        });

        console.log('[NOC] Network visualization created');

    } catch (error) {
        console.error('[NOC ERROR] Creating network:', error);
        showError('Visualization rendering failed');
    }
}

// Handle network click
function handleNetworkClick(params) {
    if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const node = allNodes.get(nodeId);

        // Ensure panel is visible and scroll to top
        const panel = document.getElementById('details-panel');
        const content = document.getElementById('details-content');
        if (panel && content) {
            panel.style.display = 'flex';
            content.scrollTop = 0; // Reset scroll to top
        }

        showDeviceDetails(nodeId, node);
    } else {
        // Clicked empty space
        closeDetailsPanel();
    }
}

// Handle node hover
function handleNodeHover(params) {
    const nodeId = params.node;
    const connectedEdges = network.getConnectedEdges(nodeId);

    // Highlight connected edges
    connectedEdges.forEach(edgeId => {
        const edge = allEdges.get(edgeId);
        allEdges.update({
            id: edgeId,
            width: 5,
            color: { color: '#58a6ff' }
        });
    });
}

// Handle node blur
function handleNodeBlur(params) {
    const nodeId = params.node;
    const connectedEdges = network.getConnectedEdges(nodeId);

    // Reset edge styling
    connectedEdges.forEach(edgeId => {
        const edge = allEdges.get(edgeId);
        allEdges.update({
            id: edgeId,
            width: 3,
            color: { color: '#30363d' }
        });
    });
}

// Handle double click
function handleDoubleClick(params) {
    if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        network.focus(nodeId, {
            scale: 1.5,
            animation: {
                duration: 800,
                easingFunction: 'easeInOutQuad'
            }
        });
    }
}

// Show device details
function showDeviceDetails(nodeId, node) {
    const panel = document.getElementById('details-panel');
    const title = document.getElementById('details-title');
    const content = document.getElementById('details-content');

    if (!panel || !title || !content) return;

    // Make panel visible
    panel.style.display = 'flex';

    title.innerHTML = `<i class="fas fa-server"></i> ${escapeHtml(node.label || 'Device')}`;

    // Reset scroll to top when showing details
    content.scrollTop = 0;

    // Check if core router (level 0 or core_router group)
    if (node.level === 0 || node.group === 'core_router') {
        // Load router interfaces
        loadRouterInterfaces(nodeId, node.label);
    } else {
        // Show basic device info
        content.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 1rem;">
                <div class="info-section">
                    <div class="info-label">Device Name</div>
                    <div class="info-value">${escapeHtml(node.label || 'Unknown')}</div>
                </div>
                <div class="info-section">
                    <div class="info-label">Type</div>
                    <div class="info-value">${escapeHtml(node.deviceType || node.group || 'Unknown')}</div>
                </div>
                <div class="info-section">
                    <div class="info-label">Status</div>
                    <div class="info-value">
                        <span class="status-badge ${node.color === '#dc3545' || node.color === '#ef4444' ? 'offline' : 'online'}">
                            ${node.title && node.title.includes('Status: Down') ? 'Offline' : 'Online'}
                        </span>
                    </div>
                </div>
                ${node.branch ? `
                    <div class="info-section">
                        <div class="info-label">Branch</div>
                        <div class="info-value">${escapeHtml(node.branch)}</div>
                    </div>
                ` : ''}
                <div class="info-section">
                    <div class="info-label">Information</div>
                    <div class="info-value" style="white-space: pre-line; font-size: 0.875rem; line-height: 1.6;">
                        ${escapeHtml(node.title || 'No additional information')}
                    </div>
                </div>
                ${!nodeId.startsWith('region_') && !nodeId.startsWith('branch_') && node.deviceData ? `
                    <button onclick="window.location.href='/device/${nodeId}'" onmouseover="this.style.background='#4A9D8A'; this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(94, 187, 168, 0.4)'" onmouseout="this.style.background='#5EBBA8'; this.style.transform='translateY(0)'; this.style.boxShadow='none'" style="width: 100%; padding: 0.875rem; background: #5EBBA8; color: white; border: none; border-radius: 6px; font-weight: 700; font-size: 0.9375rem; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
                        <i class="fas fa-external-link-alt"></i>
                        View Full Device Details
                    </button>
                ` : ''}
            </div>
        `;
    }

    addInfoStyles();
}

// Load router interfaces
function loadRouterInterfaces(hostid, routerName) {
    const content = document.getElementById('details-content');

    content.innerHTML = `
        <div class="loading-state">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Connecting to ${escapeHtml(routerName)}...</p>
        </div>
    `;

    // Close existing WebSocket
    if (detailsWebSocket) {
        detailsWebSocket.close();
        detailsWebSocket = null;
    }

    // Connect to WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/router-interfaces/${hostid}`;

    try {
        detailsWebSocket = new WebSocket(wsUrl);

        detailsWebSocket.onopen = () => {
            console.log('[WS] Connected to router', routerName);
        };

        detailsWebSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'update') {
                displayRouterInterfaces(data);
            } else if (data.type === 'error') {
                content.innerHTML = `
                    <div class="error-state">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>${escapeHtml(data.message)}</p>
                    </div>
                `;
            }
        };

        detailsWebSocket.onerror = () => {
            content.innerHTML = `
                <div class="error-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Failed to connect to router</p>
                </div>
            `;
        };

        detailsWebSocket.onclose = () => {
            console.log('[WS] Disconnected from router');
        };

    } catch (error) {
        console.error('[WS ERROR]', error);
        content.innerHTML = `
            <div class="error-state">
                <i class="fas fa-times-circle"></i>
                <p>Connection failed</p>
            </div>
        `;
    }
}

// Display router interfaces
function displayRouterInterfaces(data) {
    const content = document.getElementById('details-content');

    if (!data.interfaces || data.interfaces.length === 0) {
        content.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>No interfaces found</p>
            </div>
        `;
        return;
    }

    const summary = data.summary;

    content.innerHTML = `
        <div class="interface-summary">
            <div class="summary-card">
                <div class="summary-label">Interfaces Up</div>
                <div class="summary-value success">${summary.up}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Interfaces Down</div>
                <div class="summary-value danger">${summary.down}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Traffic In</div>
                <div class="summary-value">${summary.bandwidth_in_mbps.toFixed(1)} Mbps</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Traffic Out</div>
                <div class="summary-value">${summary.bandwidth_out_mbps.toFixed(1)} Mbps</div>
            </div>
        </div>

        <div class="live-indicator">
            <span class="pulse"></span>
            <span>Live Updates - Every 5s</span>
        </div>

        <div class="interfaces-list">
            ${data.interfaces.map(iface => `
                <div class="interface-item ${iface.status}">
                    <div class="interface-header">
                        <div class="interface-name">${escapeHtml(iface.name)}</div>
                        <span class="status-badge ${iface.status}">${iface.status.toUpperCase()}</span>
                    </div>
                    ${iface.description ? `
                        <div class="interface-desc">${escapeHtml(iface.description)}</div>
                    ` : ''}
                    <div class="interface-stats">
                        <div class="stat-row">
                            <span class="stat-icon"><i class="fas fa-arrow-down"></i></span>
                            <span class="stat-label">In:</span>
                            <span class="stat-value">${iface.bandwidth_in_mbps.toFixed(2)} Mbps</span>
                        </div>
                        <div class="stat-row">
                            <span class="stat-icon"><i class="fas fa-arrow-up"></i></span>
                            <span class="stat-label">Out:</span>
                            <span class="stat-value">${iface.bandwidth_out_mbps.toFixed(2)} Mbps</span>
                        </div>
                    </div>
                    ${iface.errors_in > 0 || iface.errors_out > 0 ? `
                        <div class="error-indicator">
                            <i class="fas fa-exclamation-triangle"></i>
                            Errors: ${iface.errors_in} in / ${iface.errors_out} out
                        </div>
                    ` : ''}
                </div>
            `).join('')}
        </div>
    `;

    addInterfaceStyles();
}

// Build device tree
function buildDeviceTree(nodes) {
    const treeContent = document.getElementById('tree-content');
    if (!treeContent) return;

    // Group by level
    const coreRouters = nodes.filter(n => n.level === 0);
    const branchSwitches = nodes.filter(n => n.level === 1);
    const endDevices = nodes.filter(n => n.level === 2);

    treeContent.innerHTML = `
        <div class="tree-section">
            <div class="tree-section-header">
                <i class="fas fa-server"></i>
                Core Routers (${coreRouters.length})
            </div>
            ${coreRouters.map(n => `
                <div class="tree-node core" data-node="${n.id}" onclick="focusNode('${n.id}')">
                    <i class="fas fa-circle ${n.title && n.title.includes('Status: Down') ? 'offline' : 'online'}"></i>
                    <span>${escapeHtml(n.label)}</span>
                </div>
            `).join('')}
        </div>

        <div class="tree-section">
            <div class="tree-section-header">
                <i class="fas fa-network-wired"></i>
                Branch Switches (${branchSwitches.length})
            </div>
            ${branchSwitches.slice(0, 50).map(n => `
                <div class="tree-node branch" data-node="${n.id}" onclick="focusNode('${n.id}')">
                    <i class="fas fa-circle ${n.title && n.title.includes('Status: Down') ? 'offline' : 'online'}"></i>
                    <span>${escapeHtml(n.label || n.branch)}</span>
                </div>
            `).join('')}
            ${branchSwitches.length > 50 ? `
                <div class="tree-node-more">+ ${branchSwitches.length - 50} more...</div>
            ` : ''}
        </div>

        <div class="tree-section">
            <div class="tree-section-header">
                <i class="fas fa-hdd"></i>
                End Devices (${endDevices.length})
            </div>
            <div class="tree-node-more">Click devices on map to view</div>
        </div>
    `;

    addTreeStyles();
}

// Focus on node
function focusNode(nodeId) {
    if (!network) return;

    network.selectNodes([nodeId]);
    network.focus(nodeId, {
        scale: 1.5,
        animation: {
            duration: 800,
            easingFunction: 'easeInOutQuad'
        }
    });

    const node = allNodes.get(nodeId);
    showDeviceDetails(nodeId, node);
}

// Update statistics
function updateStatistics(stats) {
    document.getElementById('core-count').textContent = stats.core_routers || 2;
    document.getElementById('branch-count').textContent = stats.branch_switches || 0;
    document.getElementById('device-count').textContent = stats.end_devices || 0;
    document.getElementById('link-count').textContent = stats.total_edges || 0;

    const nodes = allNodes ? allNodes.get() : [];
    const online = nodes.filter(n => n.title && n.title.includes('Status: Up')).length;
    const offline = nodes.filter(n => n.title && n.title.includes('Status: Down')).length;

    document.getElementById('online-count').textContent = online;
    document.getElementById('offline-count').textContent = offline;
}

// Close details panel
function closeDetailsPanel() {
    const content = document.getElementById('details-content');
    const title = document.getElementById('details-title');

    if (title) title.innerHTML = '<i class="fas fa-info-circle"></i> Device Information';
    if (content) {
        content.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-mouse-pointer"></i>
                <p>Click on a device to view details</p>
            </div>
        `;
    }

    if (detailsWebSocket) {
        detailsWebSocket.close();
        detailsWebSocket = null;
    }

    if (network) {
        network.unselectAll();
    }
}

// Zoom controls
function zoomIn() {
    if (network) network.moveTo({ scale: network.getScale() * 1.2 });
}

function zoomOut() {
    if (network) network.moveTo({ scale: network.getScale() * 0.8 });
}

function resetZoom() {
    if (network) network.fit({ animation: { duration: 800 } });
}

// Toggle mini map
function toggleMiniMap() {
    const miniMap = document.getElementById('mini-map');
    if (miniMap) {
        miniMap.style.display = miniMap.style.display === 'none' ? 'block' : 'none';
    }
}

// Export topology
function exportTopology() {
    alert('Export feature - Coming soon');
}

// Toggle fullscreen
function toggleFullscreen() {
    const workspace = document.querySelector('.topology-workspace');
    if (!workspace) return;

    if (!document.fullscreenElement) {
        workspace.requestFullscreen().catch(err => console.error(err));
    } else {
        document.exitFullscreen();
    }
}

// Setup event handlers
function setupEventHandlers() {
    // Search
    const searchInput = document.getElementById('topo-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            performSearch(e.target.value);
        });
    }

    // View selector
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const view = btn.dataset.view;
            switchView(view);
        });
    });
}

// Perform search
function performSearch(term) {
    if (!term) {
        visibleNodes.clear();
        visibleNodes.add(allNodes.get());
        visibleEdges.clear();
        visibleEdges.add(allEdges.get());
        return;
    }

    const searchTerm = term.toLowerCase();
    const matching = allNodes.get().filter(n => {
        const label = (n.label || '').toLowerCase();
        const title = (n.title || '').toLowerCase();
        const branch = (n.branch || '').toLowerCase();
        return label.includes(searchTerm) || title.includes(searchTerm) || branch.includes(searchTerm);
    });

    const matchingIds = new Set(matching.map(n => n.id));
    const matchingEdges = allEdges.get().filter(e =>
        matchingIds.has(e.from) || matchingIds.has(e.to)
    );

    visibleNodes.clear();
    visibleNodes.add(matching);
    visibleEdges.clear();
    visibleEdges.add(matchingEdges);

    if (network && matching.length > 0) {
        setTimeout(() => network.fit({ animation: { duration: 500 } }), 100);
    }
}

// Switch view
function switchView(view) {
    currentView = view;
    console.log('[NOC] Switching to', view, 'view');

    if (!network) return;

    if (view === 'hierarchical') {
        network.setOptions({
            layout: {
                hierarchical: {
                    enabled: true,
                    direction: 'UD',
                    sortMethod: 'directed',
                    nodeSpacing: 250,
                    treeSpacing: 300,
                    levelSeparation: 350
                }
            },
            physics: {
                enabled: true,
                solver: 'hierarchicalRepulsion'
            }
        });
    } else if (view === 'geographic') {
        network.setOptions({
            layout: {
                hierarchical: {
                    enabled: false
                }
            },
            physics: {
                enabled: true,
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {
                    gravitationalConstant: -100,
                    centralGravity: 0.02,
                    springLength: 300,
                    springConstant: 0.05,
                    damping: 0.4,
                    avoidOverlap: 0.8
                },
                stabilization: {
                    enabled: true,
                    iterations: 200
                }
            }
        });
    }

    // Restart physics simulation
    network.stabilize();
    setTimeout(() => {
        network.fit({ animation: { duration: 1000 } });
    }, 500);
}

// Utility functions
function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.style.display = show ? 'flex' : 'none';
}

function showError(message) {
    const container = document.getElementById('network-canvas');
    if (container) {
        container.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding: 2rem; text-align: center; color: #f85149;">
                <div style="width: 80px; height: 80px; border-radius: 50%; background: rgba(248, 81, 73, 0.1); display: flex; align-items: center; justify-content: center; margin-bottom: 1.5rem;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: #f85149;"></i>
                </div>
                <h3 style="margin: 0 0 0.75rem 0; color: #c9d1d9; font-size: 1.5rem; font-weight: 700;">Network Topology Error</h3>
                <p style="margin: 0 0 2rem 0; color: #8b949e; font-size: 1rem; max-width: 500px; line-height: 1.6;">${escapeHtml(message)}</p>
                <button onclick="location.reload()" style="padding: 0.875rem 1.75rem; background: #5EBBA8; border: none; border-radius: 8px; color: white; font-weight: 700; cursor: pointer; font-size: 1rem; display: flex; align-items: center; gap: 0.625rem; transition: all 0.2s;">
                    <i class="fas fa-sync"></i> Reload Topology
                </button>
            </div>
        `;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Dynamic styles injection
function addInfoStyles() {
    if (document.getElementById('info-styles')) return;

    const style = document.createElement('style');
    style.id = 'info-styles';
    style.textContent = `
        .info-section { margin-bottom: 1.5rem; padding: 1rem; background: rgba(255,255,255,0.02); border-radius: 8px; border: 1px solid #21262d; transition: all 0.2s; }
        .info-section:hover { border-color: #5EBBA8; }
        .info-label { font-size: 0.75rem; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.625rem; font-weight: 600; }
        .info-value { font-size: 1rem; color: #c9d1d9; font-weight: 500; line-height: 1.6; }
        .status-badge { padding: 0.5rem 1rem; border-radius: 6px; font-size: 0.8125rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; display: inline-flex; align-items: center; gap: 0.5rem; }
        .status-badge::before { content: ''; width: 8px; height: 8px; border-radius: 50%; }
        .status-badge.online { background: rgba(94, 187, 168, 0.15); color: #5EBBA8; border: 1px solid rgba(94, 187, 168, 0.3); }
        .status-badge.online::before { background: #5EBBA8; box-shadow: 0 0 8px rgba(94, 187, 168, 0.6); }
        .status-badge.offline { background: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid rgba(248, 81, 73, 0.3); }
        .status-badge.offline::before { background: #f85149; box-shadow: 0 0 8px rgba(248, 81, 73, 0.6); }
    `;
    document.head.appendChild(style);
}

function addInterfaceStyles() {
    if (document.getElementById('interface-styles')) return;

    const style = document.createElement('style');
    style.id = 'interface-styles';
    style.textContent = `
        .interface-summary { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1.25rem; }
        .summary-card { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 1rem; transition: all 0.2s; }
        .summary-card:hover { border-color: #5EBBA8; }
        .summary-label { font-size: 0.6875rem; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.5rem; font-weight: 600; }
        .summary-value { font-size: 1.75rem; font-weight: 700; color: #c9d1d9; }
        .summary-value.success { color: #5EBBA8; }
        .summary-value.danger { color: #f85149; }
        .live-indicator { display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem; background: rgba(94, 187, 168, 0.1); border: 1px solid rgba(94, 187, 168, 0.3); border-radius: 6px; margin-bottom: 1.25rem; font-size: 0.875rem; color: #5EBBA8; font-weight: 600; }
        .pulse { width: 10px; height: 10px; background: #5EBBA8; border-radius: 50%; animation: pulse 2s infinite; box-shadow: 0 0 8px rgba(94, 187, 168, 0.6); }
        @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.6; transform: scale(0.9); } }
        .interfaces-list { display: flex; flex-direction: column; gap: 0.875rem; max-height: 600px; overflow-y: auto; padding-right: 0.5rem; }
        .interface-item { background: #161b22; border: 1px solid #21262d; border-left: 4px solid #30363d; border-radius: 8px; padding: 1.125rem; transition: all 0.2s; }
        .interface-item:hover { border-left-color: #5EBBA8; transform: translateX(4px); box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
        .interface-item.up { border-left-color: #5EBBA8; background: linear-gradient(to right, rgba(94, 187, 168, 0.05), #161b22); }
        .interface-item.down { border-left-color: #f85149; background: linear-gradient(to right, rgba(248, 81, 73, 0.05), #161b22); }
        .interface-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.625rem; }
        .interface-name { font-weight: 700; color: #c9d1d9; font-size: 0.9375rem; }
        .interface-desc { font-size: 0.8125rem; color: #8b949e; margin-bottom: 0.875rem; font-style: italic; }
        .interface-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 0.625rem; }
        .stat-row { display: flex; align-items: center; gap: 0.625rem; font-size: 0.875rem; padding: 0.5rem; background: rgba(255,255,255,0.02); border-radius: 4px; }
        .stat-icon { width: 18px; color: #5EBBA8; font-size: 0.875rem; }
        .stat-label { color: #8b949e; font-weight: 500; }
        .stat-value { color: #c9d1d9; font-weight: 700; margin-left: auto; }
        .error-indicator { margin-top: 0.875rem; padding: 0.625rem 0.875rem; background: rgba(248, 81, 73, 0.1); border: 1px solid rgba(248, 81, 73, 0.3); border-radius: 6px; font-size: 0.8125rem; color: #f85149; display: flex; align-items: center; gap: 0.625rem; font-weight: 600; }
        .interfaces-list::-webkit-scrollbar { width: 6px; }
        .interfaces-list::-webkit-scrollbar-track { background: #0d1117; border-radius: 3px; }
        .interfaces-list::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
        .interfaces-list::-webkit-scrollbar-thumb:hover { background: #5EBBA8; }
    `;
    document.head.appendChild(style);
}

function addTreeStyles() {
    if (document.getElementById('tree-styles')) return;

    const style = document.createElement('style');
    style.id = 'tree-styles';
    style.textContent = `
        .tree-section { margin-bottom: 1.75rem; }
        .tree-section-header { font-weight: 700; color: #c9d1d9; font-size: 0.875rem; padding: 0.75rem 1rem; background: linear-gradient(135deg, #161b22 0%, #1c2128 100%); border-radius: 6px; margin-bottom: 0.625rem; display: flex; align-items: center; gap: 0.625rem; border: 1px solid #21262d; }
        .tree-section-header i { color: #5EBBA8; font-size: 1rem; }
        .tree-node { padding: 0.75rem 1rem; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 0.75rem; font-size: 0.875rem; color: #c9d1d9; transition: all 0.2s; margin-bottom: 0.375rem; border: 1px solid transparent; background: rgba(255,255,255,0.01); }
        .tree-node:hover { background: #161b22; transform: translateX(4px); border-color: #5EBBA8; box-shadow: 0 2px 8px rgba(94, 187, 168, 0.15); }
        .tree-node i.online { color: #5EBBA8; font-size: 0.625rem; animation: pulse-dot 2s infinite; }
        .tree-node i.offline { color: #f85149; font-size: 0.625rem; }
        .tree-node-more { padding: 0.625rem 1rem; font-size: 0.8125rem; color: #8b949e; font-style: italic; text-align: center; }
        @keyframes pulse-dot { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    `;
    document.head.appendChild(style);
}

console.log('[NOC] Enterprise topology module loaded');
