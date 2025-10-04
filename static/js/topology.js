/**
 * WARD OPS - Network Topology Visualization
 * Clean rebuild with proper error handling
 */

// Global variables
let network = null;
let allNodes = null;
let allEdges = null;
let selectedNodeId = null;
let interfaceWebSocket = null;

// Initialize topology on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('[Topology] Initializing...');

    // Watch for theme changes to redraw mini-map
    watchThemeChanges();

    initializeTopology();
});

/**
 * Get theme-aware colors for labels (both edge and node)
 */
function getThemeColors() {
    // Get theme from data-theme attribute or localStorage or system preference
    let theme = document.documentElement.getAttribute('data-theme');

    if (!theme) {
        // Fallback to localStorage
        theme = localStorage.getItem('ward-theme');
    }

    if (!theme) {
        // Fallback to system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            theme = 'dark';
        } else {
            theme = 'light';
        }
    }

    const isDark = theme === 'dark';

    return {
        isDark: isDark,
        edgeLabel: {
            color: isDark ? '#FFFFFF' : '#1a1a1a',
            background: isDark ? 'rgba(0, 0, 0, 0.8)' : 'rgba(255, 255, 255, 0.9)'
        },
        nodeLabel: {
            color: isDark ? '#F3F4F6' : '#1a1a1a'
        }
    };
}

/**
 * Get edge label font colors based on current theme
 */
function getEdgeLabelColors() {
    return getThemeColors().edgeLabel;
}

/**
 * Update all edge label colors based on current theme
 */
function updateEdgeLabelColors() {
    if (!network || !allEdges) return;

    const colors = getEdgeLabelColors();

    // Update global edge font settings
    network.setOptions({
        edges: {
            font: {
                color: colors.color,
                background: colors.background
            }
        }
    });

    // Force redraw by updating all edges with labels
    const edges = allEdges.get();
    const edgesToUpdate = edges.filter(edge => edge.label && edge.label.trim() !== '').map(edge => ({
        id: edge.id,
        font: {
            size: edge.font?.size || 13,
            color: colors.color,
            background: colors.background,
            strokeWidth: 2,
            strokeColor: colors.color,
            align: edge.font?.align || 'top',
            vadjust: edge.font?.vadjust || -8
        }
    }));

    if (edgesToUpdate.length > 0) {
        allEdges.update(edgesToUpdate);
    }
}

/**
 * Update all node label colors based on current theme
 */
function updateNodeLabelColors() {
    if (!network || !allNodes) return;

    const nodeColor = getThemeColors().nodeLabel.color;

    // Update global node font settings
    network.setOptions({
        nodes: {
            font: {
                color: nodeColor
            }
        }
    });

    // Update all nodes
    const nodes = allNodes.get();
    const nodesToUpdate = nodes.map(node => ({
        id: node.id,
        font: {
            ...node.font,
            color: nodeColor
        }
    }));

    allNodes.update(nodesToUpdate);
}

/**
 * Watch for theme changes
 */
function watchThemeChanges() {
    // Watch for data-theme attribute changes on html element
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'data-theme') {
                const theme = document.documentElement.getAttribute('data-theme');
                console.log('[Topology] Theme changed to:', theme);
                // Update node label colors for new theme
                if (allNodes) {
                    updateNodeLabelColors();
                }
                // Update edge label colors for new theme
                if (allEdges) {
                    updateEdgeLabelColors();
                }
                // Redraw mini-map with new colors
                if (network) {
                    setTimeout(drawMiniMap, 100);
                    // Force redraw to apply new colors
                    network.redraw();
                }
            }
        });
    });

    observer.observe(document.documentElement, { attributes: true });
}

/**
 * Main initialization function
 */
function initializeTopology() {
    // Check if vis.js is loaded
    if (typeof vis === 'undefined') {
        showError('Visualization library not loaded. Please refresh the page.');
        return;
    }

    showLoading(true);
    loadTopologyData();
}

/**
 * Load topology data from API
 */
function loadTopologyData() {
    fetch('/api/topology?view=hierarchical&limit=200')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('[Topology] Data loaded:', data.stats);

            // Initialize data sets
            allNodes = new vis.DataSet(data.nodes || []);

            // Add default labels to all edges - no font settings here, will be set globally
            const edgesWithLabels = (data.edges || []).map(edge => ({
                ...edge,
                label: edge.label || ''
            }));

            allEdges = new vis.DataSet(edgesWithLabels);

            // Update statistics
            updateStatistics(data.stats);

            // Create the network visualization
            createNetworkVisualization();

            // Start fetching bandwidth data for edges
            startBandwidthUpdates();

            showLoading(false);
        })
        .catch(error => {
            console.error('[Topology] Error loading data:', error);
            showError('Failed to load topology data: ' + error.message);
            showLoading(false);
        });
}

/**
 * Start fetching bandwidth data for edges
 */
let bandwidthUpdateInterval = null;

function startBandwidthUpdates() {
    // Clear any existing interval
    if (bandwidthUpdateInterval) {
        clearInterval(bandwidthUpdateInterval);
    }

    // Fetch bandwidth data immediately
    fetchEdgeBandwidth();

    // Update every 10 seconds
    bandwidthUpdateInterval = setInterval(fetchEdgeBandwidth, 10000);
}

/**
 * Fetch bandwidth data for all edges
 */
function fetchEdgeBandwidth() {
    if (!allNodes || !allEdges) return;

    // Get all core routers
    const coreRouters = allNodes.get().filter(n => n.level === 0 || n.deviceType === 'Core Router');

    // console.log(`[Bandwidth] Fetching data for ${coreRouters.length} core routers`);

    coreRouters.forEach(router => {
        const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/router-interfaces/${router.id}`;

        const ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                // Skip the initial "connected" message and wait for actual interface data
                if (data.type === 'connected') {
                    // console.log(`[Bandwidth] ✓ Connected to router ${router.label || router.id}, waiting for interface data...`);
                    return; // Don't close, wait for actual data
                }

                // Check all possible data structures for interface data
                if (data.interfaces && Array.isArray(data.interfaces)) {
                    // console.log(`[Bandwidth] ✓ Processing ${data.interfaces.length} interfaces (direct)`);
                    updateEdgeBandwidthLabels(router.id, data.interfaces);
                    ws.close();
                } else if (data.type === 'interface_update' && data.interfaces) {
                    // console.log(`[Bandwidth] ✓ Processing ${data.interfaces.length} interfaces (type:interface_update)`);
                    updateEdgeBandwidthLabels(router.id, data.interfaces);
                    ws.close();
                } else if (data.type === 'update' && data.interfaces) {
                    // console.log(`[Bandwidth] ✓ Processing ${data.interfaces.length} interfaces (type:update)`);
                    updateEdgeBandwidthLabels(router.id, data.interfaces);
                    ws.close();
                } else if (data.data && data.data.interfaces) {
                    // console.log(`[Bandwidth] ✓ Processing ${data.data.interfaces.length} interfaces (nested data.data)`);
                    updateEdgeBandwidthLabels(router.id, data.data.interfaces);
                    ws.close();
                } else {
                    // console.warn('[Bandwidth] Unexpected data format. Keys:', Object.keys(data));
                    // console.warn('[Bandwidth] Data type:', data.type);
                    // console.warn('[Bandwidth] Full data:', JSON.stringify(data, null, 2));
                }
            } catch (error) {
                // console.error('[Bandwidth] Error parsing data:', error);
            }
        };

        ws.onerror = (error) => {
            // console.error(`[Bandwidth] WebSocket error for router ${router.id}:`, error);
            ws.close();
        };
    });
}

/**
 * Update edge labels with bandwidth data
 */
function updateEdgeBandwidthLabels(routerId, interfaces) {
    const edges = allEdges.get();
    let updatedCount = 0;

    interfaces.forEach(iface => {
        // Try multiple matching strategies
        let edge = null;

        // Get all edges from this router
        const routerEdges = edges.filter(e => e.from === routerId);

        // Strategy 1: Match by interface name directly (Tu10, Tu12, etc.)
        if (iface.name) {
            edge = routerEdges.find(e =>
                e.label && e.label.includes(iface.name)
            );
        }

        // Strategy 2: Match by interface name in edge ID
        if (!edge && iface.name) {
            edge = routerEdges.find(e =>
                e.id && e.id.includes(iface.name)
            );
        }

        // Strategy 3: Match by "to" node label from description
        if (!edge && iface.description) {
            const targetName = iface.description.replace(/To_|to_|_Branch|_TB|\d+/gi, '').trim();
            if (targetName) {
                edge = routerEdges.find(e => {
                    const toNode = allNodes.get(e.to);
                    return toNode && toNode.label && toNode.label.toLowerCase().includes(targetName.toLowerCase());
                });
            }
        }

        // Strategy 4: Match by description in title
        if (!edge && iface.description) {
            edge = routerEdges.find(e =>
                e.title && e.title.includes(iface.description)
            );
        }

        if (edge) {
            const bwIn = iface.bandwidth_in_mbps || 0;
            const bwOut = iface.bandwidth_out_mbps || 0;
            const totalBw = bwIn + bwOut;

            // Only show label if total bandwidth is above 1 Mbps to reduce clutter
            const showLabel = totalBw > 1.0;

            // Get theme-appropriate label colors
            const labelColors = getEdgeLabelColors();

            const edgeUpdate = {
                id: edge.id,
                label: showLabel ? `▼${bwIn.toFixed(1)}M ▲${bwOut.toFixed(1)}M` : '',
                title: `${iface.name}\n${iface.description || ''}\n▼ Download: ${bwIn.toFixed(2)} Mbps\n▲ Upload: ${bwOut.toFixed(2)} Mbps\nStatus: ${iface.status}`,
                color: {
                    color: iface.status === 'up' ? '#5EBBA8' : '#ef4444',
                    highlight: '#72CFB8',
                    hover: '#72CFB8'
                },
                width: Math.max(3, Math.min(8, totalBw / 100)),
                font: {
                    size: 13,
                    color: labelColors.color,
                    background: labelColors.background,
                    strokeWidth: 2,
                    strokeColor: labelColors.color,
                    align: 'top'
                }
            };

            // Update edge with bandwidth label - adapts to theme
            allEdges.update(edgeUpdate);

            updatedCount++;
            // console.log(`[Bandwidth] ✓ Updated edge for ${iface.name}: ▼${bwIn.toFixed(1)}M ▲${bwOut.toFixed(1)}M`);
        } else {
            // console.log(`[Bandwidth] ✗ No edge found for ${iface.name} (${iface.description || 'no description'})`);
        }
    });

    // console.log(`[Bandwidth] Updated ${updatedCount} of ${interfaces.length} interfaces for router ${routerId}`);

    // Update performance metrics after bandwidth update
    updatePerformanceMetrics();
}

/**
 * Create the network visualization
 */
function createNetworkVisualization() {
    const container = document.getElementById('topology-canvas');

    if (!container) {
        console.error('[Topology] Canvas container not found');
        return;
    }

    // Get theme colors from CSS variables
    const edgeColor = getComputedStyle(document.documentElement).getPropertyValue('--edge-color').trim() || '#30363d';
    const wardGreen = getComputedStyle(document.documentElement).getPropertyValue('--ward-green').trim() || '#5EBBA8';
    const wardGreenLight = getComputedStyle(document.documentElement).getPropertyValue('--ward-green-light').trim() || '#72CFB8';

    // Vis.js network options
    const options = {
        nodes: {
            shape: 'dot',
            size: 25,
            font: {
                size: 16,
                color: getThemeColors().nodeLabel.color,
                face: 'Arial, sans-serif'
            },
            borderWidth: 2,
            shadow: {
                enabled: true,
                color: 'rgba(94, 187, 168, 0.4)',
                size: 10,
                x: 0,
                y: 0
            }
        },
        edges: {
            width: 4,
            color: {
                color: edgeColor,
                highlight: wardGreen,
                hover: wardGreenLight
            },
            smooth: {
                enabled: true,
                type: 'cubicBezier',
                roundness: 0.4
            },
            font: {
                size: 13,
                color: getEdgeLabelColors().color,
                background: getEdgeLabelColors().background,
                strokeWidth: 2,
                strokeColor: getEdgeLabelColors().color,
                align: 'top',
                vadjust: -8,
                multi: false
            },
            arrows: {
                to: {
                    enabled: false
                }
            },
            chosen: {
                label: true,
                edge: true
            },
            labelHighlightBold: true,
            selectionWidth: 2
        },
        physics: {
            enabled: true,
            stabilization: {
                enabled: true,
                iterations: 500,
                fit: true
            },
            hierarchicalRepulsion: {
                nodeDistance: 400,
                springLength: 450,
                springConstant: 0.002,
                damping: 0.09
            },
            solver: 'hierarchicalRepulsion'
        },
        layout: {
            hierarchical: {
                enabled: false
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 100,
            navigationButtons: false,
            keyboard: true
        }
    };

    try {
        // Create network
        network = new vis.Network(container, {
            nodes: allNodes,
            edges: allEdges
        }, options);

        console.log('[Topology] Network created successfully');

        // Setup event handlers
        setupEventHandlers();

        // Setup mini-map
        setupMiniMapUpdates();

        // Disable physics after stabilization and apply force layout
        network.once('stabilizationIterationsDone', () => {
            console.log('[Topology] Stabilization complete');

            // Apply force-directed layout
            changeLayout('force');

            network.fit({
                animation: {
                    duration: 800,
                    easingFunction: 'easeInOutQuad'
                }
            });

            // Draw mini-map after stabilization
            setTimeout(() => {
                drawMiniMap();
            }, 500);
        });

    } catch (error) {
        console.error('[Topology] Error creating network:', error);
        showError('Failed to create visualization: ' + error.message);
    }
}

/**
 * Setup event handlers for network interactions
 */
function setupEventHandlers() {
    // Click event
    network.on('click', (params) => {
        if (params.nodes.length > 0) {
            selectedNodeId = params.nodes[0];
            const node = allNodes.get(selectedNodeId);
            showNodeDetails(node);
        } else {
            closeDetailsPanel();
        }
    });

    // Double click event
    network.on('doubleClick', (params) => {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            if (!nodeId.startsWith('region_') && !nodeId.startsWith('branch_')) {
                window.location.href = `/device/${nodeId}`;
            }
        }
    });

    // Hover events
    network.on('hoverNode', () => {
        document.body.style.cursor = 'pointer';
    });

    network.on('blurNode', () => {
        document.body.style.cursor = 'default';
    });

    // Search box
    const searchBox = document.getElementById('search-box');
    if (searchBox) {
        searchBox.addEventListener('input', (e) => {
            performSearch(e.target.value);
        });
    }
}

/**
 * Show node details in the panel
 */
function showNodeDetails(node) {
    const panel = document.getElementById('details-panel');
    const panelTitle = document.getElementById('panel-title');
    const panelContent = document.getElementById('panel-content');

    if (!panel || !panelTitle || !panelContent) return;

    // Show panel
    panel.style.display = 'flex';

    // Reset scroll
    panelContent.scrollTop = 0;

    // Set title
    panelTitle.textContent = node.label || 'Device';

    // Check if this is a core router
    if (node.deviceType === 'Core Router' || node.level === 0) {
        loadRouterInterfaces(node.id, node.label);
    } else {
        displayBasicNodeInfo(node);
    }
}

/**
 * Display basic node information
 */
function displayBasicNodeInfo(node) {
    const panelContent = document.getElementById('panel-content');

    const status = (node.title && node.title.includes('Status: Down')) ? 'offline' : 'online';
    const statusText = status === 'online' ? 'Online' : 'Offline';

    panelContent.innerHTML = `
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
                <span class="status-badge ${status}">${statusText}</span>
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
            <div class="info-value" style="white-space: pre-line; font-size: 0.875rem;">
                ${escapeHtml(node.title || 'No additional information')}
            </div>
        </div>
    `;
}

/**
 * Load router interfaces via WebSocket
 */
function loadRouterInterfaces(hostid, routerName) {
    const panelContent = document.getElementById('panel-content');

    panelContent.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Loading router interfaces...</p>
        </div>
    `;

    // Close existing WebSocket
    if (interfaceWebSocket) {
        interfaceWebSocket.close();
        interfaceWebSocket = null;
    }

    // Connect to WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/router-interfaces/${hostid}`;

    try {
        interfaceWebSocket = new WebSocket(wsUrl);

        interfaceWebSocket.onopen = () => {
            console.log('[WebSocket] Connected to router:', routerName);
        };

        interfaceWebSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'interface_update' || data.type === 'update') {
                displayRouterInterfaces(data);
            } else if (data.type === 'error') {
                panelContent.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-exclamation-triangle" style="color: var(--danger);"></i>
                        <p>${escapeHtml(data.message || 'Failed to load interfaces')}</p>
                    </div>
                `;
            }
        };

        interfaceWebSocket.onerror = (error) => {
            console.error('[WebSocket] Error:', error);
            panelContent.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-times-circle" style="color: var(--danger);"></i>
                    <p>Failed to connect to router</p>
                </div>
            `;
        };

        interfaceWebSocket.onclose = () => {
            console.log('[WebSocket] Connection closed');
        };

    } catch (error) {
        console.error('[WebSocket] Failed to create connection:', error);
        panelContent.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-times-circle" style="color: var(--danger);"></i>
                <p>Connection error</p>
            </div>
        `;
    }
}

/**
 * Display router interfaces
 */
function displayRouterInterfaces(data) {
    const panelContent = document.getElementById('panel-content');
    const panelTitle = document.getElementById('panel-title');

    if (!data.interfaces || data.interfaces.length === 0) {
        panelContent.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>No interfaces found</p>
            </div>
        `;
        return;
    }

    // Calculate summary from current router's interfaces only
    let up = 0, down = 0;
    let totalBandwidthIn = 0, totalBandwidthOut = 0;

    data.interfaces.forEach(iface => {
        if (iface.status === 'up') up++;
        else down++;

        totalBandwidthIn += iface.bandwidth_in_mbps || 0;
        totalBandwidthOut += iface.bandwidth_out_mbps || 0;
    });

    // Update panel title with router name
    if (data.router_name || data.hostname) {
        panelTitle.textContent = data.router_name || data.hostname;
    }

    panelContent.innerHTML = `
        <div class="live-indicator">
            <span class="pulse-dot"></span>
            <span>Live Updates - Every 5s</span>
        </div>

        <div class="interface-summary">
            <div class="summary-card">
                <div class="summary-label">Interfaces Up</div>
                <div class="summary-value success">${up}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Interfaces Down</div>
                <div class="summary-value danger">${down}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Traffic In</div>
                <div class="summary-value">${totalBandwidthIn.toFixed(1)} Mbps</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Traffic Out</div>
                <div class="summary-value">${totalBandwidthOut.toFixed(1)} Mbps</div>
            </div>
        </div>

        <div class="interface-list">
            ${data.interfaces.map(iface => {
                // Extract destination from description (e.g., "To_Gori")
                const description = iface.description || '';
                const hasDestination = description.includes('To_') || description.includes('to_');

                return `
                <div class="interface-card ${iface.status}">
                    <div class="interface-header">
                        <div style="display: flex; flex-direction: column; gap: 0.25rem; flex: 1;">
                            <span class="interface-name">${escapeHtml(iface.name)}</span>
                            ${description ? `
                                <div style="font-size: 0.875rem; color: ${hasDestination ? 'var(--ward-green)' : 'var(--text-secondary)'}; font-weight: ${hasDestination ? '600' : '500'};">
                                    <i class="fas fa-${hasDestination ? 'arrow-right' : 'info-circle'}"></i> ${escapeHtml(description)}
                                </div>
                            ` : ''}
                        </div>
                        <span class="interface-status ${iface.status}">${iface.status.toUpperCase()}</span>
                    </div>

                    ${iface.ip_address ? `
                        <div style="font-size: 0.8125rem; color: var(--text-secondary); margin: 0.5rem 0; padding: 0.5rem; background: rgba(94, 187, 168, 0.05); border-radius: 4px; border-left: 2px solid var(--ward-green);">
                            <i class="fas fa-network-wired"></i> ${escapeHtml(iface.ip_address)}
                        </div>
                    ` : ''}

                    <div class="interface-metrics">
                        <div class="metric" style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem; background: rgba(59, 130, 246, 0.1); border-radius: 4px;">
                            <i class="fas fa-arrow-down" style="color: #3b82f6;"></i>
                            <div style="flex: 1;">
                                <div style="font-size: 0.6875rem; color: var(--text-secondary);">Download</div>
                                <div style="font-weight: 700; color: var(--text-primary);">${iface.bandwidth_in_mbps.toFixed(2)} Mbps</div>
                            </div>
                        </div>
                        <div class="metric" style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem; background: rgba(139, 92, 246, 0.1); border-radius: 4px;">
                            <i class="fas fa-arrow-up" style="color: #8b5cf6;"></i>
                            <div style="flex: 1;">
                                <div style="font-size: 0.6875rem; color: var(--text-secondary);">Upload</div>
                                <div style="font-weight: 700; color: var(--text-primary);">${iface.bandwidth_out_mbps.toFixed(2)} Mbps</div>
                            </div>
                        </div>
                    </div>

                    ${iface.errors_in > 0 || iface.errors_out > 0 ? `
                        <div style="margin-top: 0.75rem; padding: 0.625rem; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 4px; font-size: 0.8125rem; color: var(--danger); display: flex; align-items: center; gap: 0.5rem;">
                            <i class="fas fa-exclamation-triangle"></i>
                            <span><strong>Errors:</strong> ${iface.errors_in} in / ${iface.errors_out} out</span>
                        </div>
                    ` : ''}

                    ${iface.admin_status && iface.admin_status !== iface.status ? `
                        <div style="margin-top: 0.5rem; padding: 0.5rem; background: rgba(245, 158, 11, 0.1); border-radius: 4px; font-size: 0.75rem; color: var(--warning);">
                            <i class="fas fa-info-circle"></i> Admin Status: ${escapeHtml(iface.admin_status)}
                        </div>
                    ` : ''}
                </div>
            `}).join('')}
        </div>
    `;
}

/**
 * Close details panel
 */
function closeDetailsPanel() {
    const panel = document.getElementById('details-panel');
    if (panel) {
        panel.style.display = 'none';
    }

    // Close WebSocket
    if (interfaceWebSocket) {
        interfaceWebSocket.close();
        interfaceWebSocket = null;
    }

    selectedNodeId = null;
}

/**
 * Update statistics display
 */
function updateStatistics(stats) {
    document.getElementById('total-nodes').textContent = stats.total_nodes || 0;
    document.getElementById('total-edges').textContent = stats.total_edges || 0;

    // Calculate online/offline counts
    const nodes = allNodes ? allNodes.get() : [];
    const onlineCount = nodes.filter(n =>
        n.title && n.title.includes('Status: Up')
    ).length;
    const offlineCount = nodes.filter(n =>
        n.title && n.title.includes('Status: Down')
    ).length;

    document.getElementById('online-count').textContent = onlineCount;
    document.getElementById('offline-count').textContent = offlineCount;
}

/**
 * Search functionality
 */
function performSearch(query) {
    if (!network || !allNodes) return;

    query = query.toLowerCase().trim();

    if (!query) {
        network.unselectAll();
        return;
    }

    const matchingNodes = allNodes.get().filter(node => {
        const label = (node.label || '').toLowerCase();
        const title = (node.title || '').toLowerCase();
        return label.includes(query) || title.includes(query);
    });

    if (matchingNodes.length > 0) {
        const ids = matchingNodes.map(n => n.id);
        network.selectNodes(ids);
        network.fit({
            nodes: ids,
            animation: { duration: 500 }
        });
    }
}

/**
 * Layout control functions
 */
function changeLayout(layoutType) {
    if (!network) return;

    console.log('[Topology] Changing layout to:', layoutType);
    let options = {};

    switch (layoutType) {
        case 'hierarchical':
            options = {
                layout: {
                    hierarchical: {
                        enabled: true,
                        direction: 'UD',
                        sortMethod: 'directed',
                        nodeSpacing: 350,
                        treeSpacing: 400,
                        levelSeparation: 400,
                        blockShifting: true,
                        edgeMinimization: true
                    }
                },
                physics: {
                    enabled: true,
                    solver: 'hierarchicalRepulsion',
                    hierarchicalRepulsion: {
                        nodeDistance: 400
                    }
                }
            };
            break;

        case 'force':
            options = {
                layout: {
                    hierarchical: { enabled: false }
                },
                physics: {
                    enabled: true,
                    solver: 'forceAtlas2Based',
                    forceAtlas2Based: {
                        gravitationalConstant: -80,
                        centralGravity: 0.01,
                        springLength: 300,
                        springConstant: 0.08,
                        damping: 0.4
                    },
                    stabilization: {
                        enabled: true,
                        iterations: 300
                    }
                }
            };
            break;

        case 'circular':
            // First disable hierarchical and physics
            network.setOptions({
                layout: { hierarchical: { enabled: false } },
                physics: { enabled: false }
            });

            // Get all nodes and arrange them in a circle
            const nodes = allNodes.get();
            const centerX = 0;
            const centerY = 0;
            const radius = Math.max(300, nodes.length * 15);

            nodes.forEach((node, index) => {
                const angle = (index / nodes.length) * 2 * Math.PI;
                const x = centerX + radius * Math.cos(angle);
                const y = centerY + radius * Math.sin(angle);

                allNodes.update({
                    id: node.id,
                    x: x,
                    y: y,
                    fixed: { x: false, y: false }
                });
            });

            setTimeout(() => {
                network.fit({ animation: { duration: 800 } });
                // Redraw mini-map after layout
                setTimeout(drawMiniMap, 500);
            }, 100);
            return;

        case 'radial':
            // Disable physics and hierarchical
            network.setOptions({
                layout: { hierarchical: { enabled: false } },
                physics: { enabled: false }
            });

            // Get all nodes
            const allNodesArray = allNodes.get();
            const coreRouters = allNodesArray.filter(n => n.level === 0 || (n.deviceType && n.deviceType.includes('Core')));
            const otherNodes = allNodesArray.filter(n => !coreRouters.includes(n));

            console.log('[Layout] Radial: Total nodes:', allNodesArray.length, 'Core routers:', coreRouters.length, 'Other nodes:', otherNodes.length);

            // Place core routers in center
            const coreRadius = 200;
            if (coreRouters.length > 0) {
                coreRouters.forEach((node, index) => {
                    const angle = (index / coreRouters.length) * 2 * Math.PI;
                    allNodes.update({
                        id: node.id,
                        x: coreRadius * Math.cos(angle),
                        y: coreRadius * Math.sin(angle),
                        fixed: { x: false, y: false }
                    });
                });
            }

            // Group nodes by level
            const levels = {};
            otherNodes.forEach(node => {
                const level = node.level !== undefined ? node.level : 1;
                if (!levels[level]) levels[level] = [];
                levels[level].push(node);
            });

            // Sort levels
            const sortedLevels = Object.keys(levels).map(l => parseInt(l)).sort((a, b) => a - b);

            console.log(`[Layout] Radial levels distribution:`, sortedLevels.map(l => `Level ${l}: ${levels[l].length}`).join(', '));

            // Place nodes in concentric rings
            sortedLevels.forEach((level, ringIndex) => {
                const levelNodes = levels[level];
                const levelRadius = 450 + (ringIndex * 350);

                console.log(`[Layout] Placing level ${level}: ${levelNodes.length} nodes at radius ${levelRadius}px`);

                levelNodes.forEach((node, index) => {
                    const angle = (index / levelNodes.length) * 2 * Math.PI;
                    const x = levelRadius * Math.cos(angle);
                    const y = levelRadius * Math.sin(angle);

                    allNodes.update({
                        id: node.id,
                        x: x,
                        y: y,
                        fixed: { x: false, y: false }
                    });
                });
            });

            // Ensure all nodes are visible
            setTimeout(() => {
                const allNodeIds = allNodesArray.map(n => n.id);
                console.log(`[Layout] Fitting view to all ${allNodeIds.length} nodes`);

                network.fit({
                    animation: {
                        duration: 1000,
                        easingFunction: 'easeInOutQuad'
                    },
                    nodes: allNodeIds
                });

                // Redraw mini-map after layout
                setTimeout(drawMiniMap, 500);
            }, 300);
            return;

        default:
            console.warn('[Topology] Unknown layout type:', layoutType);
            return;
    }

    network.setOptions(options);

    // Stabilize and fit view
    setTimeout(() => {
        network.fit({ animation: { duration: 800 } });

        // Disable physics after stabilization for hierarchical/force layouts
        setTimeout(() => {
            if (layoutType === 'hierarchical' || layoutType === 'force') {
                network.setOptions({ physics: { enabled: false } });
                // Redraw mini-map after physics stabilization
                setTimeout(drawMiniMap, 500);
            }
        }, 2000);
    }, 500);
}

/**
 * Zoom controls
 */
function zoomIn() {
    if (network) {
        const scale = network.getScale();
        network.moveTo({ scale: scale * 1.3, animation: { duration: 300 } });
    }
}

function zoomOut() {
    if (network) {
        const scale = network.getScale();
        network.moveTo({ scale: scale * 0.7, animation: { duration: 300 } });
    }
}

function resetView() {
    if (network) {
        network.fit({ animation: { duration: 800 } });
    }
}

/**
 * Fullscreen toggle
 */
function toggleFullscreen() {
    const wrapper = document.querySelector('.topology-page-wrapper');
    if (!wrapper) return;

    if (!document.fullscreenElement) {
        wrapper.requestFullscreen().catch(err => {
            console.error('Error entering fullscreen:', err);
        });
    } else {
        document.exitFullscreen();
    }
}

/**
 * Show/hide loading overlay
 */
function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = show ? 'flex' : 'none';
    }
}

/**
 * Show error message
 */
function showError(message) {
    const canvas = document.getElementById('topology-canvas');
    if (canvas) {
        canvas.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-secondary);">
                <div style="width: 80px; height: 80px; border-radius: 50%; background: rgba(239, 68, 68, 0.1); display: flex; align-items: center; justify-content: center; margin-bottom: 1.5rem;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 2.5rem; color: var(--danger);"></i>
                </div>
                <h3 style="margin: 0 0 0.5rem 0; color: var(--text-primary);">Error Loading Topology</h3>
                <p style="margin: 0 0 1.5rem 0; max-width: 400px; text-align: center;">${escapeHtml(message)}</p>
                <button onclick="location.reload()" style="padding: 0.75rem 1.5rem; background: var(--ward-green); color: white; border: none; border-radius: 6px; font-weight: 600; cursor: pointer;">
                    <i class="fas fa-sync"></i> Reload Page
                </button>
            </div>
        `;
    }
    showLoading(false);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Apply filters to network visualization
 */
function applyFilters() {
    if (!network || !allNodes) return;

    const showRouters = document.getElementById('filter-routers').checked;
    const showSwitches = document.getElementById('filter-switches').checked;
    const showPayboxes = document.getElementById('filter-payboxes').checked;
    const showOnline = document.getElementById('filter-online').checked;
    const showOffline = document.getElementById('filter-offline').checked;

    const allNodesArray = allNodes.get();
    const visibleNodeIds = [];

    allNodesArray.forEach(node => {
        let show = true;

        // Filter by device type
        const deviceType = (node.deviceType || node.group || '').toLowerCase();
        if (deviceType.includes('router') && !showRouters) show = false;
        if (deviceType.includes('switch') && !showSwitches) show = false;
        if (deviceType.includes('paybox') && !showPayboxes) show = false;

        // Filter by status
        const isOnline = node.title && node.title.includes('Status: Up');
        const isOffline = node.title && node.title.includes('Status: Down');

        if (isOnline && !showOnline) show = false;
        if (isOffline && !showOffline) show = false;

        if (show) {
            visibleNodeIds.push(node.id);
        }
    });

    // Show/hide nodes
    const updates = allNodesArray.map(node => ({
        id: node.id,
        hidden: !visibleNodeIds.includes(node.id)
    }));

    allNodes.update(updates);

    // Update edge visibility
    const allEdgesArray = allEdges.get();
    const edgeUpdates = allEdgesArray.map(edge => ({
        id: edge.id,
        hidden: !visibleNodeIds.includes(edge.from) || !visibleNodeIds.includes(edge.to)
    }));

    allEdges.update(edgeUpdates);

    console.log(`[Filter] Showing ${visibleNodeIds.length} of ${allNodesArray.length} nodes`);
}

/**
 * Update performance metrics dashboard
 */
function updatePerformanceMetrics() {
    if (!allEdges || !allNodes) return;

    const edges = allEdges.get();
    const nodes = allNodes.get();

    let totalBandwidth = 0;
    let busiestInterface = { name: '-', bandwidth: 0 };
    let devicesWithErrors = 0;

    let matchedEdges = 0;
    let edgesWithLabels = 0;
    let totalEdges = edges.length;
    let sampleNonMatching = [];

    edges.forEach(edge => {
        if (edge.label) {
            edgesWithLabels++;
            // Parse bandwidth from label - new format: "▼X.XM ▲Y.YM"
            const matches = edge.label.match(/▼([\d.]+)M\s*▲([\d.]+)M/);
            if (matches) {
                matchedEdges++;
                const bwIn = parseFloat(matches[1]) || 0;
                const bwOut = parseFloat(matches[2]) || 0;
                const totalEdgeBw = bwIn + bwOut;

                totalBandwidth += totalEdgeBw;

                if (totalEdgeBw > busiestInterface.bandwidth) {
                    busiestInterface = {
                        name: edge.title ? edge.title.split('\n')[0] : 'Unknown',
                        bandwidth: totalEdgeBw
                    };
                }
            } else {
                // Collect first 3 non-matching labels for debugging
                if (sampleNonMatching.length < 3) {
                    sampleNonMatching.push(`"${edge.label}" (ID: ${edge.id})`);
                }
            }
        }

        // Count devices with errors (red edges)
        if (edge.color && edge.color.color === '#ef4444') {
            devicesWithErrors++;
        }
    });

    // Metrics debug logging disabled
    // if (sampleNonMatching.length > 0) {
    //     console.log('[Metrics DEBUG] Sample non-matching labels:', sampleNonMatching.join(', '));
    // }
    // console.log(`[Metrics DEBUG] Total edges: ${totalEdges}, With labels: ${edgesWithLabels}, Matched regex: ${matchedEdges}, Total BW: ${totalBandwidth.toFixed(2)} Mbps`);

    // Update DOM with proper formatting
    const totalBandwidthEl = document.getElementById('total-bandwidth');
    const busiestEl = document.getElementById('busiest-interface');
    const errorCountEl = document.getElementById('error-count');

    if (totalBandwidthEl) {
        totalBandwidthEl.textContent = `${(totalBandwidth / 1000).toFixed(2)} Gbps`;
    }

    if (busiestEl) {
        busiestEl.textContent = busiestInterface.bandwidth > 0 ?
            `${busiestInterface.name} (${busiestInterface.bandwidth.toFixed(1)} Mbps)` : '-';
    }

    if (errorCountEl) {
        errorCountEl.textContent = devicesWithErrors;
    }

    // console.log(`[Metrics] Total BW: ${(totalBandwidth / 1000).toFixed(2)} Gbps, Busiest: ${busiestInterface.name}, Errors: ${devicesWithErrors}`);
}

/**
 * Draw mini-map
 */
function drawMiniMap() {
    if (!network || !allNodes || !allEdges) {
        return;
    }

    const canvas = document.getElementById('mini-map-canvas');
    if (!canvas) {
        return;
    }

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Get canvas background color from CSS variable
    const canvasBg = getComputedStyle(document.documentElement).getPropertyValue('--canvas-bg').trim() || '#0d1117';
    ctx.fillStyle = canvasBg;
    ctx.fillRect(0, 0, width, height);

    // Draw subtle border around mini-map
    ctx.strokeStyle = 'rgba(94, 187, 168, 0.3)';
    ctx.lineWidth = 2;
    ctx.strokeRect(1, 1, width - 2, height - 2);

    // Get network positions
    const positions = network.getPositions();
    const nodeIds = Object.keys(positions);

    if (nodeIds.length === 0) {
        return;
    }

    // Calculate bounds with padding
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    nodeIds.forEach(id => {
        const pos = positions[id];
        if (pos && pos.x !== undefined && pos.y !== undefined) {
            if (pos.x < minX) minX = pos.x;
            if (pos.x > maxX) maxX = pos.x;
            if (pos.y < minY) minY = pos.y;
            if (pos.y > maxY) maxY = pos.y;
        }
    });

    const rangeX = (maxX - minX) || 1000;
    const rangeY = (maxY - minY) || 1000;
    const padding = 15;
    const scale = Math.min((width - 2 * padding) / rangeX, (height - 2 * padding) / rangeY);

    // Draw edges with subtle styling - don't draw them, too cluttered
    // Skip edge drawing for cleaner mini-map

    // Draw nodes with enhanced hierarchy
    nodeIds.forEach(id => {
        const node = allNodes.get(id);
        if (!node || node.hidden) return;

        const pos = positions[id];
        if (!pos) return;

        const x = ((pos.x - minX) * scale) + padding;
        const y = ((pos.y - minY) * scale) + padding;

        // Determine node color and size based on type/status
        let nodeColor = '#5EBBA8'; // Default green
        let nodeSize = 3;
        let borderColor = '#ffffff';
        let glowIntensity = 0.8;
        let showLabel = false;

        // Core routers - extra large orange with pulse glow
        if (node.level === 0 || (node.deviceType && node.deviceType.includes('Core'))) {
            nodeSize = 10;
            nodeColor = '#FF6B35';
            borderColor = '#FFE5DB';
            glowIntensity = 1.5;
            showLabel = true;
        }
        // Branch switches - medium teal
        else if (node.deviceType && node.deviceType.includes('Switch')) {
            nodeSize = 5;
            nodeColor = '#14b8a6';
        }
        // Offline devices - red
        else if (node.title && node.title.includes('Status: Down')) {
            nodeColor = '#ef4444';
            nodeSize = 4;
            glowIntensity = 1.2;
        }

        // Draw node with enhanced glow
        ctx.shadowBlur = nodeSize * glowIntensity;
        ctx.shadowColor = nodeColor;

        ctx.fillStyle = nodeColor;
        ctx.beginPath();
        ctx.arc(x, y, nodeSize, 0, 2 * Math.PI);
        ctx.fill();

        // Reset shadow
        ctx.shadowBlur = 0;

        // Border for definition (thicker for core routers)
        ctx.strokeStyle = borderColor;
        ctx.lineWidth = nodeSize >= 10 ? 2.5 : 1.5;
        ctx.beginPath();
        ctx.arc(x, y, nodeSize, 0, 2 * Math.PI);
        ctx.stroke();

        // Draw label for core routers
        if (showLabel && node.label) {
            ctx.font = 'bold 10px Arial';
            ctx.fillStyle = '#FFFFFF';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'bottom';

            // Add text shadow for readability
            ctx.shadowBlur = 3;
            ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';

            ctx.fillText(node.label, x, y - nodeSize - 3);
            ctx.shadowBlur = 0;
        }
    });

    // Draw viewport indicator
    try {
        const scale_vis = network.getScale();
        const viewPos = network.getViewPosition();

        const canvas_vis = network.canvas.frame.canvas;
        const viewWidthWorld = canvas_vis.clientWidth / scale_vis;
        const viewHeightWorld = canvas_vis.clientHeight / scale_vis;

        // Convert viewport to mini-map coordinates
        const viewWidth = viewWidthWorld * scale;
        const viewHeight = viewHeightWorld * scale;

        // viewPos is the CENTER of the viewport in world coordinates
        // We need to calculate the top-left corner of the viewport in world coords first
        const viewTopLeftX = viewPos.x - (viewWidthWorld / 2);
        const viewTopLeftY = viewPos.y - (viewHeightWorld / 2);

        // Now convert to mini-map coordinates
        const viewX = ((viewTopLeftX - minX) * scale) + padding;
        const viewY = ((viewTopLeftY - minY) * scale) + padding;

        // Clamp viewport to canvas bounds to prevent it going off-screen
        const clampedViewX = Math.max(0, Math.min(viewX, width - viewWidth));
        const clampedViewY = Math.max(0, Math.min(viewY, height - viewHeight));
        const clampedViewWidth = Math.min(viewWidth, width);
        const clampedViewHeight = Math.min(viewHeight, height);

        // console.log(`[MiniMap] ViewPos: (${viewPos.x.toFixed(0)}, ${viewPos.y.toFixed(0)}), Scale: ${scale_vis.toFixed(2)}, Viewport: (${clampedViewX.toFixed(0)}, ${clampedViewY.toFixed(0)}, ${clampedViewWidth.toFixed(0)}x${clampedViewHeight.toFixed(0)})`);

        // Draw viewport with enhanced styling
        // Outer glow
        ctx.shadowBlur = 12;
        ctx.shadowColor = 'rgba(94, 187, 168, 0.6)';

        // Draw border with rounded corners effect
        ctx.strokeStyle = '#5EBBA8';
        ctx.lineWidth = 3;
        ctx.strokeRect(clampedViewX, clampedViewY, clampedViewWidth, clampedViewHeight);

        // Inner subtle border for depth
        ctx.shadowBlur = 0;
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 1;
        ctx.strokeRect(clampedViewX + 1, clampedViewY + 1, clampedViewWidth - 2, clampedViewHeight - 2);

        // Semi-transparent gradient fill
        const gradient = ctx.createLinearGradient(clampedViewX, clampedViewY, clampedViewX, clampedViewY + clampedViewHeight);
        gradient.addColorStop(0, 'rgba(94, 187, 168, 0.2)');
        gradient.addColorStop(1, 'rgba(94, 187, 168, 0.1)');
        ctx.fillStyle = gradient;
        ctx.fillRect(clampedViewX, clampedViewY, clampedViewWidth, clampedViewHeight);

        // Store viewport bounds for click navigation
        canvas.dataset.minX = minX;
        canvas.dataset.maxX = maxX;
        canvas.dataset.minY = minY;
        canvas.dataset.maxY = maxY;
        canvas.dataset.scale = scale;
        canvas.dataset.padding = padding;
    } catch (error) {
        console.error('[MiniMap] Error drawing viewport:', error);
    }
}

/**
 * Toggle mini-map visibility
 */
function toggleMiniMap() {
    const miniMap = document.querySelector('.mini-map');
    if (miniMap) {
        miniMap.style.display = miniMap.style.display === 'none' ? 'block' : 'none';
    }
}

/**
 * Handle mini-map click for navigation
 */
function setupMiniMapClickNavigation() {
    const canvas = document.getElementById('mini-map-canvas');
    if (!canvas) return;

    // Add cursor pointer style
    canvas.style.cursor = 'pointer';

    canvas.addEventListener('click', (event) => {
        if (!network) return;

        const rect = canvas.getBoundingClientRect();
        const clickX = event.clientX - rect.left;
        const clickY = event.clientY - rect.top;

        // Use stored bounds from last draw (more efficient)
        const minX = parseFloat(canvas.dataset.minX);
        const maxX = parseFloat(canvas.dataset.maxX);
        const minY = parseFloat(canvas.dataset.minY);
        const maxY = parseFloat(canvas.dataset.maxY);
        const scale = parseFloat(canvas.dataset.scale);
        const padding = parseFloat(canvas.dataset.padding);

        if (isNaN(minX) || isNaN(scale)) {
            console.warn('[MiniMap] No bounds data available for navigation');
            return;
        }

        // Convert click coordinates to network position
        const networkX = ((clickX - padding) / scale) + minX;
        const networkY = ((clickY - padding) / scale) + minY;

        // console.log(`[MiniMap] Click navigation to (${networkX.toFixed(0)}, ${networkY.toFixed(0)})`);

        // Move network view to clicked position with smooth animation
        network.moveTo({
            position: { x: networkX, y: networkY },
            scale: network.getScale(),
            animation: {
                duration: 500,
                easingFunction: 'easeInOutQuad'
            }
        });

        // console.log(`[MiniMap] Navigated to position: ${networkX.toFixed(0)}, ${networkY.toFixed(0)}`);
    });
}

/**
 * Update mini-map when network view changes
 */
let miniMapUpdateTimeout = null;

function debouncedMiniMapUpdate() {
    if (miniMapUpdateTimeout) {
        clearTimeout(miniMapUpdateTimeout);
    }
    miniMapUpdateTimeout = setTimeout(drawMiniMap, 100);
}

function setupMiniMapUpdates() {
    if (!network) {
        console.log('[MiniMap] Network not ready for setup');
        return;
    }

    console.log('[MiniMap] Setting up event listeners');

    network.on('zoom', debouncedMiniMapUpdate);
    network.on('dragEnd', debouncedMiniMapUpdate);

    network.on('stabilized', () => {
        setTimeout(drawMiniMap, 300);
    });

    // Setup click navigation on mini-map
    setupMiniMapClickNavigation();

    // Update mini-map less frequently (every 10 seconds instead of 3)
    setInterval(drawMiniMap, 10000);

    // Update performance metrics
    setInterval(updatePerformanceMetrics, 10000);
}

console.log('[Topology] Module loaded successfully');
