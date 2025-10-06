// Add host functionality
let availableGroups = [];
let availableTemplates = [];

function loadGroups() {
    auth.fetch('/api/v1/groups')
        .then(response => response.json())
        .then(groups => {
            availableGroups = groups;
            const select = document.getElementById('groups');
            select.innerHTML = groups.map(group =>
                `<option value="${group.groupid}">${group.name}</option>`
            ).join('');
        })
        .catch(error => {
            console.error('Error loading groups:', error);
            document.getElementById('groups').innerHTML = '<option value="">Error loading groups</option>';
        });
}

function loadTemplates() {
    auth.fetch('/api/v1/templates')
        .then(response => response.json())
        .then(templates => {
            availableTemplates = templates;
            const select = document.getElementById('templates');
            select.innerHTML = templates.map(template =>
                `<option value="${template.templateid}">${template.name}</option>`
            ).join('');
        })
        .catch(error => {
            console.error('Error loading templates:', error);
            document.getElementById('templates').innerHTML = '<option value="">Error loading templates</option>';
        });
}

function quickSelectTemplate(keyword) {
    const select = document.getElementById('templates');
    const options = select.options;

    // Deselect all first
    for (let i = 0; i < options.length; i++) {
        options[i].selected = false;
    }

    // Select matching templates
    for (let i = 0; i < options.length; i++) {
        if (options[i].text.toLowerCase().includes(keyword.toLowerCase())) {
            options[i].selected = true;
        }
    }
}

function handleSubmit(event) {
    event.preventDefault();

    const form = document.getElementById('add-host-form');
    const resultDiv = document.getElementById('result-message');

    // Get selected groups and templates
    const groupSelect = document.getElementById('groups');
    const templateSelect = document.getElementById('templates');

    const selectedGroups = Array.from(groupSelect.selectedOptions).map(opt => opt.value);
    const selectedTemplates = Array.from(templateSelect.selectedOptions).map(opt => opt.value);

    if (selectedGroups.length === 0) {
        showMessage('error', 'Please select at least one host group');
        return;
    }

    if (selectedTemplates.length === 0) {
        showMessage('error', 'Please select at least one template');
        return;
    }

    const data = {
        hostname: document.getElementById('hostname').value,
        visible_name: document.getElementById('visible_name').value,
        ip_address: document.getElementById('ip_address').value,
        group_ids: selectedGroups,
        template_ids: selectedTemplates
    };

    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating...';

    auth.fetch('/api/v1/hosts', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showMessage('success', result.message);
            form.reset();
            setTimeout(() => {
                window.location.href = '/devices';
            }, 2000);
        } else {
            showMessage('error', result.message);
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    })
    .catch(error => {
        console.error('Error creating host:', error);
        showMessage('error', 'Failed to create host. Please try again.');
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    });
}

function showMessage(type, message) {
    const resultDiv = document.getElementById('result-message');
    resultDiv.className = `message ${type}`;
    resultDiv.textContent = message;
    resultDiv.classList.remove('hidden');

    // Auto-hide after 5 seconds
    setTimeout(() => {
        resultDiv.classList.add('hidden');
    }, 5000);
}

// Event listeners
document.getElementById('add-host-form').addEventListener('submit', handleSubmit);

// Initial load
loadGroups();
loadTemplates();