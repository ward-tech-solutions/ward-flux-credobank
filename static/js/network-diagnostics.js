/**
 * WARD OPS - Network Diagnostics UI
 * Independent Ping & Traceroute with WARD styling
 */

class NetworkDiagnostics {
    constructor(deviceIP, deviceName) {
        this.deviceIP = deviceIP;
        this.deviceName = deviceName;
        this.isPinging = false;
        this.isTracing = false;
    }

    /**
     * Perform ping check
     */
    async performPing(count = 5) {
        if (this.isPinging) return;

        this.isPinging = true;
        this.updatePingUI('running');

        try {
            const response = await auth.fetch(`/api/v1/diagnostics/ping?ip=${this.deviceIP}&count=${count}`, {
                method: 'POST'
            });

            const result = await response.json();
            this.displayPingResult(result);

        } catch (error) {
            this.displayPingError(error.message);
        } finally {
            this.isPinging = false;
            this.updatePingUI('idle');
        }
    }

    /**
     * Perform traceroute
     */
    async performTraceroute(maxHops = 30) {
        if (this.isTracing) return;

        this.isTracing = true;
        this.updateTracerouteUI('running');

        try {
            const response = await auth.fetch(`/api/v1/diagnostics/traceroute?ip=${this.deviceIP}&max_hops=${maxHops}`, {
                method: 'POST'
            });

            const result = await response.json();
            this.displayTracerouteResult(result);

        } catch (error) {
            this.displayTracerouteError(error.message);
        } finally {
            this.isTracing = false;
            this.updateTracerouteUI('idle');
        }
    }

    /**
     * Update ping UI state
     */
    updatePingUI(state) {
        const button = document.getElementById('ping-button');
        const container = document.getElementById('ping-results');

        if (state === 'running') {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Pinging...';
            container.innerHTML = `
                <div class="diagnostic-loading">
                    <div class="loading-spinner"></div>
                    <p>Sending ICMP packets to ${this.deviceIP}...</p>
                </div>
            `;
        } else {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-satellite-dish"></i> Run Ping Check';
        }
    }

    /**
     * Display ping results with WARD styling
     */
    displayPingResult(result) {
        const container = document.getElementById('ping-results');

        const lossPercent = result.packet_loss_percent;
        const avgRTT = result.avg_rtt_ms;

        // Determine status color (WARD green for good, red for bad)
        let statusClass = 'status-good';
        let statusIcon = 'check-circle';
        let statusText = 'Reachable';

        if (lossPercent > 0) {
            statusClass = 'status-warning';
            statusIcon = 'exclamation-triangle';
            statusText = 'Packet Loss';
        }

        if (lossPercent === 100) {
            statusClass = 'status-critical';
            statusIcon = 'times-circle';
            statusText = 'Unreachable';
        }

        container.innerHTML = `
            <div class="ping-result-card ${statusClass}">
                <div class="result-header">
                    <i class="fas fa-${statusIcon}"></i>
                    <span>${statusText}</span>
                    <small>${new Date(result.timestamp).toLocaleString()}</small>
                </div>

                <div class="result-stats">
                    <div class="stat-item">
                        <div class="stat-icon"><i class="fas fa-paper-plane"></i></div>
                        <div class="stat-content">
                            <span class="stat-value">${result.packets_sent}</span>
                            <span class="stat-label">Sent</span>
                        </div>
                    </div>

                    <div class="stat-item">
                        <div class="stat-icon"><i class="fas fa-reply"></i></div>
                        <div class="stat-content">
                            <span class="stat-value">${result.packets_received}</span>
                            <span class="stat-label">Received</span>
                        </div>
                    </div>

                    <div class="stat-item ${lossPercent > 0 ? 'stat-warning' : ''}">
                        <div class="stat-icon"><i class="fas fa-chart-line"></i></div>
                        <div class="stat-content">
                            <span class="stat-value">${lossPercent}%</span>
                            <span class="stat-label">Loss</span>
                        </div>
                    </div>

                    ${avgRTT ? `
                    <div class="stat-item">
                        <div class="stat-icon"><i class="fas fa-tachometer-alt"></i></div>
                        <div class="stat-content">
                            <span class="stat-value">${avgRTT.toFixed(1)} ms</span>
                            <span class="stat-label">Avg RTT</span>
                        </div>
                    </div>
                    ` : ''}

                    ${result.min_rtt_ms ? `
                    <div class="stat-item">
                        <div class="stat-icon"><i class="fas fa-arrow-down"></i></div>
                        <div class="stat-content">
                            <span class="stat-value">${result.min_rtt_ms.toFixed(1)} ms</span>
                            <span class="stat-label">Min RTT</span>
                        </div>
                    </div>
                    ` : ''}

                    ${result.max_rtt_ms ? `
                    <div class="stat-item">
                        <div class="stat-icon"><i class="fas fa-arrow-up"></i></div>
                        <div class="stat-content">
                            <span class="stat-value">${result.max_rtt_ms.toFixed(1)} ms</span>
                            <span class="stat-label">Max RTT</span>
                        </div>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Display ping error
     */
    displayPingError(message) {
        const container = document.getElementById('ping-results');
        container.innerHTML = `
            <div class="diagnostic-error">
                <i class="fas fa-exclamation-circle"></i>
                <p>Ping failed: ${message}</p>
            </div>
        `;
    }

    /**
     * Update traceroute UI state
     */
    updateTracerouteUI(state) {
        const button = document.getElementById('traceroute-button');
        const container = document.getElementById('traceroute-results');

        if (state === 'running') {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Tracing Route...';
            container.innerHTML = `
                <div class="diagnostic-loading">
                    <div class="loading-spinner"></div>
                    <p>Discovering network path to ${this.deviceIP}...</p>
                    <small>This may take up to 30 seconds</small>
                </div>
            `;
        } else {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-route"></i> Trace Network Path';
        }
    }

    /**
     * Display traceroute results with visual path
     */
    displayTracerouteResult(result) {
        const container = document.getElementById('traceroute-results');

        const hops = result.hops || [];
        const reached = result.reached_destination;

        let hopsHTML = hops.map((hop, index) => {
            const latencyClass = hop.latency_ms < 20 ? 'latency-good' :
                                hop.latency_ms < 50 ? 'latency-warning' :
                                'latency-critical';

            return `
                <div class="hop-item ${latencyClass}">
                    <div class="hop-number">${hop.hop_number}</div>
                    <div class="hop-details">
                        <div class="hop-hostname">${hop.hostname || 'Unknown'}</div>
                        <div class="hop-ip">${hop.ip || '*'}</div>
                    </div>
                    <div class="hop-latency">
                        ${hop.latency_ms ? `${hop.latency_ms.toFixed(1)} ms` : '*'}
                    </div>
                    ${index < hops.length - 1 ? '<div class="hop-arrow">↓</div>' : ''}
                </div>
            `;
        }).join('');

        container.innerHTML = `
            <div class="traceroute-result-card">
                <div class="result-header">
                    <i class="fas fa-${reached ? 'check-circle' : 'exclamation-triangle'}"></i>
                    <span>${reached ? 'Destination Reached' : 'Path Traced'}</span>
                    <small>${hops.length} hops</small>
                </div>

                <div class="network-path">
                    <div class="path-start">
                        <i class="fas fa-server"></i>
                        <span>Your Server</span>
                    </div>

                    <div class="path-hops">
                        ${hopsHTML || '<p class="no-hops">No hops discovered</p>'}
                    </div>

                    <div class="path-end ${reached ? 'path-reached' : ''}">
                        <i class="fas fa-bullseye"></i>
                        <span>${this.deviceName || this.deviceIP}</span>
                    </div>
                </div>

                <div class="path-summary">
                    <div class="summary-item">
                        <i class="fas fa-route"></i>
                        <span>Total Hops: ${hops.length}</span>
                    </div>
                    ${hops.length > 0 && hops[hops.length - 1].latency_ms ? `
                    <div class="summary-item">
                        <i class="fas fa-clock"></i>
                        <span>End-to-End: ${hops[hops.length - 1].latency_ms.toFixed(1)} ms</span>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Display traceroute error
     */
    displayTracerouteError(message) {
        const container = document.getElementById('traceroute-results');
        container.innerHTML = `
            <div class="diagnostic-error">
                <i class="fas fa-exclamation-circle"></i>
                <p>Traceroute failed: ${message}</p>
            </div>
        `;
    }
}

// Export for use in device details page
window.NetworkDiagnostics = NetworkDiagnostics;
