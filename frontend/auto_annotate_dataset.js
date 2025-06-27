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

// Show subset details and allow selection
function showSubsetOptions(projectName, subsetJson) {
    const resultDiv = document.getElementById('result');
    // Fetch and display the subset's images
    fetch(`${BACKEND_URL}/projects/${projectName}/${subsetJson}`)
        .then(response => response.json())
        .then(data => {
            const images = data.images || [];
            let html = `<h3>Subset: ${subsetJson}</h3>`;
            html += `<div><b>Images in this subset (${images.length}):</b></div>`;
            html += '<div style="display:flex;flex-wrap:wrap;gap:10px;margin:10px 0;">' +
                images.map(img => {
                    const imgUrl = `${BACKEND_URL}/projects/${projectName}/images/${encodeURIComponent(img)}`;
                    return `<div style='display:inline-block;text-align:center;'>
                        <img src='${imgUrl}' alt='${img}' style='width:80px;height:80px;object-fit:cover;display:block;margin-bottom:4px;border:1px solid #ccc;'>
                        <span style='font-size:12px;word-break:break-all;'>${img}</span>
                    </div>`;
                }).join('') + '</div>';
            html += `<button id="selectSubsetBtn">Select This Subset</button> `;
            html += `<button id="backToSubsetsBtn">Back to Subsets</button>`;
            resultDiv.innerHTML = html;
            document.getElementById('selectSubsetBtn').onclick = function() {
                // Store selected subset in localStorage
                localStorage.setItem(`selectedSubset_${projectName}`, subsetJson);
                showAutoAnnotateStatus(`Subset selected: ${subsetJson}`);
            };
            document.getElementById('backToSubsetsBtn').onclick = function() {
                fetchAndDisplaySubsets(projectName);
            };
        })
        .catch(error => {
            resultDiv.innerHTML = 'Failed to load subset: ' + error;
        });
}

// Fetch and display available subsets for the project
function fetchAndDisplaySubsets(projectName) {
    fetch(`${BACKEND_URL}/api/projects/${projectName}/subsets`)
        .then(response => response.json())
        .then(subsets => {
            const resultDiv = document.getElementById('result');
            if (!Array.isArray(subsets) || subsets.length === 0) {
                resultDiv.innerHTML = '<h3>No subsets found.</h3>';
                return;
            }
            resultDiv.innerHTML = '<h3>Available Subsets:</h3>' +
                '<ul>' + subsets.map(sub =>
                    `<li><button class="choose-subset-btn" data-json="${sub.json}">${sub.name}</button></li>`
                ).join('') + '</ul>';
            // Add event listeners for subset selection
            document.querySelectorAll('.choose-subset-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const subsetJson = btn.getAttribute('data-json');
                    showSubsetOptions(projectName, subsetJson);
                });
            });
        })
        .catch(error => {
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = 'Failed to load subsets: ' + error;
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
    const projectName = getCurrentProjectName();

    function hideAllSections() {
        manualSection.style.display = 'none';
        randomSection.style.display = 'none';
        manualForm.innerHTML = '';
    }

    if (completeBtn) {
        completeBtn.addEventListener('click', function() {
            hideAllSections();
            if (!projectName) {
                showAutoAnnotateStatus('Project name not found. Please select a project.', true);
                return;
            }
            requestAutoAnnotateDataset(projectName);
        });
    }

    if (manualBtn) {
        manualBtn.addEventListener('click', function() {
            hideAllSections();
            manualSection.style.display = 'block';
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
                    fetchAndDisplaySubsets(projectName);
                    hideAllSections();
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
            hideAllSections();
            randomSection.style.display = 'block';
        });
    }

    if (randomSubmit) {
        randomSubmit.addEventListener('click', function(e) {
            e.preventDefault();
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
                    fetchAndDisplaySubsets(projectName);
                    hideAllSections();
                } else {
                    showAutoAnnotateStatus('Error: ' + (data.error || 'Unknown error'), true);
                }
            })
            .catch(function(error) {
                showAutoAnnotateStatus('Request failed: ' + error, true);
            });
        });
    }

    // --- Model selection logic for sidebar ---
    const modelFamilySel = document.getElementById('modelFamily');
    const modelVersionSel = document.getElementById('modelVersion');
    const modelDescDiv = document.getElementById('modelDescription');
    const modelSelectStatus = document.getElementById('modelSelectStatus');

    async function fetchModelList() {
      const res = await fetch(`${BACKEND_URL}/api/models/list`);
      return await res.json();
    }
    async function fetchModelDescriptions() {
      const res = await fetch(`${BACKEND_URL}/api/models/descriptions`);
      return await res.json();
    }

    async function setupModelSelection() {
      let modelList = await fetchModelList();
      let modelDescriptions = await fetchModelDescriptions();
      modelFamilySel.innerHTML = '<option value="">Select family</option>' +
        Object.keys(modelList).map(fam => `<option value="${fam}">${fam}</option>`).join('');
      modelFamilySel.onchange = function() {
        const fam = modelFamilySel.value;
        modelVersionSel.innerHTML = '<option value="">Select version</option>';
        modelDescDiv.textContent = '';
        modelSelectStatus.textContent = '';
        if (fam && modelList[fam]) {
          modelVersionSel.innerHTML += modelList[fam].map(ver => `<option value="${ver}">${ver}</option>`).join('');
        }
      };
      modelVersionSel.onchange = function() {
        const fam = modelFamilySel.value;
        const ver = modelVersionSel.value;
        if (fam && ver && modelDescriptions[fam] && modelDescriptions[fam][ver]) {
          modelDescDiv.textContent = modelDescriptions[fam][ver];
          modelSelectStatus.textContent = `Selected: ${fam} / ${ver}`;
        } else {
          modelDescDiv.textContent = '';
          modelSelectStatus.textContent = '';
        }
      };
    }

    setupModelSelection();

    // Always show available subsets
    if (projectName) {
        fetchAndDisplaySubsets(projectName);
    }

    // --- Modal logic for auto-annotate feedback and next steps ---
    function showAutoAnnotateModal(contentHtml) {
        const modal = document.getElementById('autoAnnotateModal');
        const modalContent = document.getElementById('autoAnnotateModalContent');
        modalContent.innerHTML = contentHtml;
        modal.style.display = 'flex';
    }
    function closeAutoAnnotateModal() {
        document.getElementById('autoAnnotateModal').style.display = 'none';
    }
    document.getElementById('closeAutoAnnotateModal').onclick = closeAutoAnnotateModal;
    window.onclick = function(event) {
        const modal = document.getElementById('autoAnnotateModal');
        if (event.target === modal) closeAutoAnnotateModal();
    };

    // --- Start Auto-Annotate button logic ---
    const startAutoAnnotateBtn = document.getElementById('start-auto-annotate-btn');
    if (startAutoAnnotateBtn) {
        startAutoAnnotateBtn.addEventListener('click', function() {
            if (!projectName) {
                showAutoAnnotateStatus('Project name not found. Please select a project.', true);
                return;
            }
            // Get selected model family, version, and subset from UI/localStorage
            const modelFamily = modelFamilySel.value || localStorage.getItem('selectedModelFamily');
            const modelVersion = modelVersionSel.value || localStorage.getItem('selectedModelVersion');
            const subset = localStorage.getItem(`selectedSubset_${projectName}`);
            if (!modelFamily || !modelVersion || !subset) {
                showAutoAnnotateStatus('Please select a model family, model version, and subset before starting auto-annotate.', true);
                return;
            }
            // Save to backend
            fetch(`${BACKEND_URL}/api/projects/${projectName}/save_auto_annotate_config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model_family: modelFamily,
                    model_version: modelVersion,
                    subset: subset
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.message) {
                    // Fetch subset image count for modal
                    fetch(`${BACKEND_URL}/projects/${projectName}/${subset}`)
                        .then(resp => resp.json())
                        .then(subsetData => {
                            const images = subsetData.images || [];
                            showAutoAnnotateModal(`
                                <div style='font-size:1.15rem;margin-bottom:12px;'>✅ Model config saved successfully!</div>
                                <div style='margin-bottom:10px;'><b>Model:</b> ${modelFamily} / ${modelVersion}</div>
                                <div style='margin-bottom:18px;'><b>Images in subset:</b> ${images.length}</div>
                                <div id='inferenceProgress' style='margin-bottom:12px;'></div>
                                <button id='startAutoLabelBtn' class='primary-btn' style='font-size:1.08rem;padding:10px 22px;'>Start Auto Label</button>
                            `);
                            document.getElementById('startAutoLabelBtn').onclick = function() {
                                document.getElementById('startAutoLabelBtn').disabled = true;
                                document.getElementById('startAutoLabelBtn').textContent = 'Running...';
                                // Use SSE for progress
                                const progressDiv = document.getElementById('inferenceProgress');
                                const evtSource = new EventSource(`${BACKEND_URL.replace('http', 'http')}/api/projects/${projectName}/run_inference`);
                                evtSource.onmessage = function(event) {
                                    if (event.data) {
                                        progressDiv.textContent = event.data;
                                        // Highlight errors in red
                                        if (event.data.includes('Error')) {
                                            progressDiv.style.color = 'red';
                                        } else {
                                            progressDiv.style.color = '';
                                        }
                                        if (event.data.includes('complete') || event.data.includes('Error')) {
                                            evtSource.close();
                                            document.getElementById('startAutoLabelBtn').disabled = false;
                                            document.getElementById('startAutoLabelBtn').textContent = 'Start Auto Label';
                                        }
                                    }
                                };
                                evtSource.onerror = function(err) {
                                    progressDiv.textContent = 'Error during inference.';
                                    evtSource.close();
                                    document.getElementById('startAutoLabelBtn').disabled = false;
                                    document.getElementById('startAutoLabelBtn').textContent = 'Start Auto Label';
                                };
                            };
                        });
                } else {
                    showAutoAnnotateModal(`<div style='color:red;'>Error: ${data.error || 'Unknown error'}</div>`);
                }
            })
            .catch(error => {
                showAutoAnnotateModal(`<div style='color:red;'>Request failed: ${error}</div>`);
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
