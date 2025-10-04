// SSH Terminal Functions
let currentSSHIP = null;
let sshSocket = null;

// Open SSH terminal modal
function openSSHTerminal(ip, deviceName) {
    currentSSHIP = ip;

    const modal = document.getElementById('ssh-modal');
    const deviceNameEl = document.getElementById('ssh-device-name');

    deviceNameEl.textContent = `${deviceName} (${ip})`;
    modal.style.display = 'flex';

    // Focus on username input
    document.getElementById('ssh-username').focus();
}

// Close SSH modal
function closeSSHModal(event) {
    if (event && event.target.id !== 'ssh-modal') return;

    const modal = document.getElementById('ssh-modal');
    modal.style.display = 'none';

    // Disconnect SSH if connected
    if (sshSocket) {
        sshSocket.close();
        sshSocket = null;
    }

    // Reset terminal display
    const terminal = document.getElementById('ssh-terminal');
    terminal.innerHTML = `
        <div style="text-align: center;">
            <i class="fas fa-terminal" style="font-size: 3rem; margin-bottom: 1rem; display: block;"></i>
            <p>Enter credentials below and click Connect</p>
        </div>
    `;

    // Clear credentials
    document.getElementById('ssh-username').value = '';
    document.getElementById('ssh-password').value = '';

    currentSSHIP = null;
}

// Connect to device via SSH
async function connectSSH() {
    const username = document.getElementById('ssh-username').value.trim() || 'admin';
    const password = document.getElementById('ssh-password').value;
    const btn = document.getElementById('ssh-connect-btn');
    const terminal = document.getElementById('ssh-terminal');

    if (!password) {
        alert('Please enter a password');
        return;
    }

    // Disable button
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Connecting...';

    terminal.innerHTML = '<div style="padding: 2rem; color: #5EBBA8;">Connecting to ' + currentSSHIP + '...</div>';

    try {
        // Call backend SSH API
        const response = await auth.fetch('/api/v1/ssh/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                host: currentSSHIP,
                username: username,
                password: password
            })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            // Display terminal output
            terminal.innerHTML = `
                <pre style="padding: 1rem; color: #5EBBA8; font-family: monospace; height: 100%; overflow-y: auto; margin: 0;">
Connected to ${currentSSHIP}

${result.output || 'Connection established. SSH terminal access via CLI is recommended for full interactive experience.'}

To use full SSH terminal features, use your preferred SSH client:
ssh ${username}@${currentSSHIP}

</pre>
            `;

            btn.innerHTML = '<i class="fas fa-check"></i> Connected';
            setTimeout(() => {
                btn.innerHTML = originalHTML;
                btn.disabled = false;
            }, 2000);
        } else {
            terminal.innerHTML = `<div style="padding: 2rem; color: #dc2626;">
                <i class="fas fa-exclamation-triangle"></i> ${result.error || 'Failed to connect'}
            </div>`;
            btn.disabled = false;
            btn.innerHTML = originalHTML;
        }

    } catch (error) {
        console.error('SSH connection error:', error);
        terminal.innerHTML = `<div style="padding: 2rem; color: #dc2626;">
            <i class="fas fa-exclamation-triangle"></i> Failed to connect. Please check credentials and network connectivity.
        </div>`;
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }
}

// Handle Enter key in password field
document.addEventListener('DOMContentLoaded', () => {
    const passwordField = document.getElementById('ssh-password');
    if (passwordField) {
        passwordField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                connectSSH();
            }
        });
    }
});
