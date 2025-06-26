// Constant for the backend URL
const BACKEND_URL = 'http://127.0.0.1:5000';

// Function to show status messages to the user
function showAutoAnnotateStatus(message, isError = false) {
    let statusDiv = document.getElementById('autoAnnotateStatus');
    if (!statusDiv) {
        statusDiv = document.createElement('div');
        statusDiv.id = 'autoAnnotateStatus';
        document.body.appendChild(statusDiv);
    }
    statusDiv.textContent = message;
    statusDiv.style.color = isError ? 'red' : 'green';
}

// Function to send auto-annotate request for the complete dataset
function requestAutoAnnotateDataset(projectName, userOptions = {}) {
    showAutoAnnotateStatus('Submitting auto-annotate request...');
    fetch(`${BACKEND_URL}/api/projects/${projectName}/auto_annotate_request`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(userOptions)
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            showAutoAnnotateStatus('Auto-annotate request saved!');
            // No longer show image list
        } else {
            showAutoAnnotateStatus('Error: ' + (data.error || 'Unknown error'), true);
        }
    })
    .catch(error => {
        showAutoAnnotateStatus('Request failed: ' + error, true);
    });
}

// Fetch and display the list of images for the current project
function fetchAndDisplayImageList(projectName) {
    fetch(`${BACKEND_URL}/api/projects/${projectName}/images`)
        .then(response => response.json())
        .then(images => {
            const resultDiv = document.getElementById('result');
            if (!Array.isArray(images) || images.length === 0) {
                resultDiv.textContent = 'No images found.';
                return;
            }
            resultDiv.innerHTML = '<h3>Images in Project:</h3>' +
                '<ul>' + images.map(img => `<li>${img}</li>`).join('') + '</ul>';
        })
        .catch(error => {
            const resultDiv = document.getElementById('result');
            resultDiv.textContent = 'Failed to load images: ' + error;
        });
}

document.addEventListener('DOMContentLoaded', function() {
    const completeBtn = document.getElementById('complete-btn');
    const manualBtn = document.getElementById('manual-btn');
    const manualSection = document.getElementById('manual-section');
    const manualForm = document.getElementById('manual-form');
    const manualSubmit = document.getElementById('manual-submit');
    const randomBtn = document.getElementById('random-btn');
    const randomSection = document.getElementById('random-section');
    const randomPercent = document.getElementById('random-percent');
    const randomSubmit = document.getElementById('random-submit');

    if (completeBtn) {
        completeBtn.addEventListener('click', function() {
            const projectName = getCurrentProjectName();
            if (!projectName) {
                showAutoAnnotateStatus('Project name not found. Please select a project.', true);
                return;
            }
            requestAutoAnnotateDataset(projectName);
        });
    }

    if (manualBtn) {
        manualBtn.addEventListener('click', function() {
            manualSection.style.display = 'block';
            const projectName = getCurrentProjectName();
            if (!projectName) {
                showAutoAnnotateStatus('Project name not found. Please select a project.', true);
                return;
            }
            // Fetch images and render checkboxes with thumbnails
            fetch(`${BACKEND_URL}/api/projects/${projectName}/images`)
                .then(response => response.json())
                .then(images => {
                    if (!Array.isArray(images) || images.length === 0) {
                        manualForm.innerHTML = 'No images found.';
                        return;
                    }
                    manualForm.innerHTML = images.map(img => {
                        const imgUrl = `${BACKEND_URL}/projects/${projectName}/images/${encodeURIComponent(img)}`;
                        return `<label style='display:inline-block;margin:8px;text-align:center;'>
                            <input type='checkbox' name='images' value='${img}'>
                            <img src='${imgUrl}' alt='${img}' style='width:80px;height:80px;object-fit:cover;display:block;margin-bottom:4px;border:1px solid #ccc;'>
                            <span style='font-size:12px;word-break:break-all;'>${img}</span>
                        </label>`;
                    }).join('');
                })
                .catch(error => {
                    manualForm.innerHTML = 'Failed to load images: ' + error;
                });
        });
    }

    if (manualSubmit) {
        manualSubmit.addEventListener('click', function(e) {
            e.preventDefault();
            const projectName = getCurrentProjectName();
            if (!projectName) {
                showAutoAnnotateStatus('Project name not found. Please select a project.', true);
                return;
            }
            const checked = Array.from(manualForm.querySelectorAll('input[name="images"]:checked')).map(cb => cb.value);
            if (checked.length === 0) {
                showAutoAnnotateStatus('Please select at least one image.', true);
                return;
            }
            fetch(`${BACKEND_URL}/api/projects/${projectName}/create_manual_subset`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ images: checked })
            })
            .then(response => response.json())
            .then(function(data) {
                if (data.message) {
                    showAutoAnnotateStatus(data.message);
                } else {
                    showAutoAnnotateStatus('Error: ' + (data.error || 'Unknown error'), true);
                }
            })
            .catch(function(error) {
                showAutoAnnotateStatus('Request failed: ' + error, true);
            });
        });
    }

    if (randomBtn) {
        randomBtn.addEventListener('click', function() {
            randomSection.style.display = 'block';
        });
    }

    if (randomSubmit) {
        randomSubmit.addEventListener('click', function(e) {
            e.preventDefault();
            const projectName = getCurrentProjectName();
            if (!projectName) {
                showAutoAnnotateStatus('Project name not found. Please select a project.', true);
                return;
            }
            const percent = parseFloat(randomPercent.value);
            if (isNaN(percent) || percent <= 0 || percent > 100) {
                showAutoAnnotateStatus('Please enter a valid percentage (1-100).', true);
                return;
            }
            fetch(`${BACKEND_URL}/api/projects/${projectName}/create_random_subset`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ percent })
            })
            .then(response => response.json())
            .then(function(data) {
                if (data.message) {
                    showAutoAnnotateStatus(data.message);
                } else {
                    showAutoAnnotateStatus('Error: ' + (data.error || 'Unknown error'), true);
                }
            })
            .catch(function(error) {
                showAutoAnnotateStatus('Request failed: ' + error, true);
            });
        });
    }
});

// Example placeholder for getting the project name
function getCurrentProjectName() {
    // Get project name from URL query string, e.g. ?name=gg
    const params = new URLSearchParams(window.location.search);
    return params.get('name') || null;
}

// Example usage:
// requestAutoAnnotateDataset('my_project', { option1: 'value1' });
// Call this function when the user selects the complete dataset auto-annotate option.
