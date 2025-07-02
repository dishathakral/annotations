/* Copied from frontend/view_predictions.js */
// Remove global projectName and subsetName usage from all functions and only use them after DOMContentLoaded
let images = [];
let currentImageIdx = 0;
// --- Image cache for fast switching ---
const imageCache = {};
let imageLoadTimeout = null;
let lastImageIdxRequested = null;

function preloadImage(projectName, imgName) {
  return new Promise((resolve, reject) => {
    if (imageCache[imgName]) {
      resolve(imageCache[imgName]);
      return;
    }
    const img = new window.Image();
    img.crossOrigin = 'anonymous';
    img.src = `http://localhost:5000/projects/${encodeURIComponent(projectName)}/images/${encodeURIComponent(imgName)}`;
    img.onload = () => {
      imageCache[imgName] = img;
      resolve(img);
    };
    img.onerror = reject;
  });
}

function preloadAdjacentImages(projectName, idx) {
  // Preload previous, current, and next images
  [idx - 1, idx, idx + 1].forEach(i => {
    if (i >= 0 && i < images.length) {
      preloadImage(projectName, images[i]);
    }
  });
}
// COCO 2017 80-class labels for YOLO models
let predictions = {};
let predictionsLoaded = {};
let labels = [
  'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light',
  'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
  'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
  'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket', 'bottle',
  'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
  'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed',
  'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone', 'microwave', 'oven',
  'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
];
// Only these labels will be shown in dropdowns
let presentLabelsGlobal = null;
let boxes = []; // [{x, y, w, h, label}]
let selectedBoxIdx = null;
let dragMode = null; // 'move', 'resize', or null
let dragOffset = {x:0, y:0};
let dragCorner = null;
let mode = 'draw'; // 'draw' or 'transform'
let currentMode = 'draw'; // 'draw', 'pan', 'zoomIn', 'zoomOut', 'reset'

// --- ZOOM & PAN STATE ---
let zoomLevel = 1;
let panX = 0;
let panY = 0;
let isPanning = false;
let panStart = {x:0, y:0};

function getProjectAndSubset() {
  // Use URLSearchParams on window.location.search
  const params = new URLSearchParams(window.location.search);
  // Log for debug
  console.log('DEBUG: window.location.search =', window.location.search);
  console.log('DEBUG: params.get("project") =', params.get('project'));
  console.log('DEBUG: params.get("subset") =', params.get('subset'));
  return {
    project: params.get('project') || '',
    subset: params.get('subset') || ''
  };
}

// Assumes subset JSON is always named <subsetName>.json inside the folder <subsetName>
async function fetchSubsetImages(projectNameArg, subsetNameArg) {
  if (!projectNameArg || !subsetNameArg) {
    return [];
  }
  let subsetFolder = subsetNameArg;
  if (subsetFolder.endsWith('.json')) {
    subsetFolder = subsetFolder.replace(/\.json$/, '');
  }
  if (subsetFolder.includes('/')) {
    subsetFolder = subsetFolder.split('/')[0];
  }
  const fixedUrl = `http://localhost:5000/projects/${encodeURIComponent(projectNameArg)}/${encodeURIComponent(subsetFolder)}/${encodeURIComponent(subsetFolder)}.json`;
  try {
    const response = await fetch(fixedUrl);
    if (!response.ok) return [];
    const jsonData = await response.json();
    return jsonData.images || [];
  } catch {
    return [];
  }
}

function fetchImages(projectNameArg) {
  return fetch(`http://localhost:5000/projects/${encodeURIComponent(projectNameArg)}/images/`)
    .then(res => res.json())
    .catch(() => []);
}

function fetchAnnotations(imgName, projectNameArg) {
  return fetch(`http://localhost:5000/api/projects/${encodeURIComponent(projectNameArg)}/annotations?image=${encodeURIComponent(imgName)}`)
    .then(res => res.json())
    .catch(() => []);
}

function saveAnnotations(imgName, boxes, projectNameArg) {
  return fetch(`http://localhost:5000/api/projects/${encodeURIComponent(projectNameArg)}/annotate`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ image: imgName, boxes })
  }).then(res => res.json());
}

// --- Virtualization/Pagination State ---
const THUMBS_PER_PAGE = 30;
let currentThumbPage = 0;
let totalThumbPages = 1;

function getVisibleThumbs() {
  totalThumbPages = Math.ceil(images.length / THUMBS_PER_PAGE);
  const start = currentThumbPage * THUMBS_PER_PAGE;
  const end = Math.min(start + THUMBS_PER_PAGE, images.length);
  return { start, end };
}

function gotoThumbPage(page, projectName) {
  if (page < 0 || page >= totalThumbPages) return;
  currentThumbPage = page;
  renderImageList(projectName);
}

function renderImageList(projectName) {
  const listDiv = document.getElementById('imageList');
  listDiv.innerHTML = '';
  const { start, end } = getVisibleThumbs();
  if (!images || images.length === 0) {
    listDiv.innerHTML = '<div style="color:#f63366;">No images found for this subset.</div>';
    return;
  }
  // Use DocumentFragment for fast batch DOM updates
  const fragment = document.createDocumentFragment();
  let rowDiv = null;
  const columns = 3;
  for (let idx = start; idx < end; idx++) {
    const img = images[idx];
    if ((idx - start) % columns === 0) {
      rowDiv = document.createElement('div');
      rowDiv.style.display = 'flex';
      rowDiv.style.justifyContent = 'center';
      rowDiv.style.marginBottom = '8px';
      fragment.appendChild(rowDiv);
    }
    const imgElem = document.createElement('img');
    imgElem.src = `http://localhost:5000/projects/${encodeURIComponent(projectName)}/images/${encodeURIComponent(img)}`;
    imgElem.className = 'anno-img-thumb' + (idx === currentImageIdx ? ' selected' : '');
    imgElem.style.width = '60px';
    imgElem.style.height = '60px';
    imgElem.style.objectFit = 'cover';
    imgElem.style.marginRight = '6px';
    imgElem.setAttribute('loading', 'lazy');
    imgElem.decoding = 'async';
    imgElem.onerror = () => {
      imgElem.style.display = 'none';
      if (rowDiv && rowDiv.childElementCount === 1) {
        rowDiv.innerHTML = '<span style="color:#f63366;">Image not found</span>';
      }
    };
    imgElem.onclick = () => {
      currentImageIdx = idx;
      lastImageIdxRequested = idx;
      loadImage(projectName);
      renderImageList(projectName);
      drawCanvasWithPreview(projectName);
    };
    rowDiv.appendChild(imgElem);
  }
  listDiv.appendChild(fragment);
  // Pagination controls
  if (totalThumbPages > 1) {
    const pagDiv = document.createElement('div');
    pagDiv.style.textAlign = 'center';
    pagDiv.style.margin = '8px 0';
    pagDiv.style.userSelect = 'none';
    pagDiv.innerHTML =
      `<button id="thumbPrevBtn" ${currentThumbPage === 0 ? 'disabled' : ''}>&lt; Prev</button> ` +
      `Page ${currentThumbPage + 1} of ${totalThumbPages} ` +
      `<button id="thumbNextBtn" ${currentThumbPage === totalThumbPages - 1 ? 'disabled' : ''}>Next &gt;</button>`;
    listDiv.appendChild(pagDiv);
    document.getElementById('thumbPrevBtn').onclick = () => gotoThumbPage(currentThumbPage - 1, projectName);
    document.getElementById('thumbNextBtn').onclick = () => gotoThumbPage(currentThumbPage + 1, projectName);
  }
}

function renderModeSelector() {
  // Do not clear the mode selector; leave it as is so the buttons remain visible
}

function renderModeActionSection() {
  const section = document.getElementById('modeActionSection');
  section.innerHTML = `
    <button id="saveBtn" class="anno-btn btn btn-primary">Save Annotations</button>
  `;
  document.getElementById('saveBtn').onclick = async function() {
    const imgName = images[currentImageIdx];
    // Get image dimensions
    let width = 0, height = 0;
    try {
      const img = new window.Image();
      img.src = `http://localhost:5000/projects/${encodeURIComponent(projectName)}/images/${encodeURIComponent(imgName)}`;
      await new Promise(resolve => { img.onload = resolve; });
      width = img.width;
      height = img.height;
    } catch {}
    // Prepare annotation data for this image
    const annotationData = {
      file_name: imgName,
      width,
      height,
      annotations: boxes.map((b, i) => ({
        id: i + 1,
        bbox: [b.x, b.y, b.w, b.h],
        label: b.label
      }))
    };
    // POST to backend
    const resp = await fetch(`http://localhost:5000/api/projects/${encodeURIComponent(projectName)}/save_annotation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(annotationData)
    });
    const data = await resp.json();
    document.getElementById('annoMsg').innerText = data.message || data.error || 'Annotation saved!';
  };
}

function renderLabels() {
  const labelsSection = document.getElementById('labelsSection');
  labelsSection.innerHTML = '';
  // Use only presentLabelsGlobal for dropdown (plus any custom labels)
  const presentLabels = (presentLabelsGlobal && presentLabelsGlobal.length > 0) ? presentLabelsGlobal : labels;
  boxes.forEach((box, idx) => {
    const boxDiv = document.createElement('div');
    boxDiv.style.marginBottom = '10px';
    boxDiv.style.padding = '8px';
    boxDiv.style.border = idx === selectedBoxIdx ? '2px solid #f63366' : '1px solid #ddd';
    boxDiv.style.borderRadius = '6px';
    boxDiv.style.background = idx === selectedBoxIdx ? '#fff0f4' : '#fafafa';

    const boxTitle = document.createElement('div');
    boxTitle.style.display = 'flex';
    boxTitle.style.justifyContent = 'space-between';
    boxTitle.style.alignItems = 'center';
    boxTitle.style.marginBottom = '4px';

    const titleText = document.createElement('span');
    titleText.textContent = `Box ${idx + 1}`;
    titleText.style.fontWeight = 'bold';
    boxTitle.appendChild(titleText);

    // Bin icon for delete
    const bin = document.createElement('span');
    bin.innerHTML = '🗑️';
    bin.style.cursor = 'pointer';
    bin.title = 'Delete bounding box';
    bin.onclick = (e) => {
      e.stopPropagation();
      boxes.splice(idx, 1);
      if (selectedBoxIdx === idx) selectedBoxIdx = null;
      else if (selectedBoxIdx > idx) selectedBoxIdx--;
      renderLabels();
      drawCanvasWithPreview();
    };
    boxTitle.appendChild(bin);

    boxDiv.appendChild(boxTitle);

    const sel = document.createElement('select');
    sel.className = 'anno-label-dropdown form-control';
    presentLabels.forEach(label => {
      const opt = document.createElement('option');
      opt.value = label;
      opt.text = label;
      if (label === box.label) opt.selected = true;
      sel.appendChild(opt);
    });
    sel.onchange = () => {
      box.label = sel.value;
      drawCanvasWithPreview();
    };
    boxDiv.appendChild(sel);

    boxDiv.onclick = (e) => {
      if (e.target === sel || e.target === bin) return;
      selectedBoxIdx = idx;
      drawCanvasWithPreview();
      renderLabels();
    };

    labelsSection.appendChild(boxDiv);
  });
}

let currentLoadedImage = null;
let currentLoadedImageName = null;
let currentLoadedProject = null;
let currentLoadedImageIsReady = false;
let canvasLoading = false;

function drawCanvasWithPreview(projectName, previewBox = null) {
  const canvas = document.getElementById('annotateCanvas');
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!images.length) return;
  const imgName = images[currentImageIdx];

  // Use cache if available, else load and draw directly
  let img = imageCache[imgName];
  if (!img) {
    img = new window.Image();
    img.crossOrigin = 'anonymous';
    img.src = `http://localhost:5000/projects/${encodeURIComponent(projectName)}/images/${encodeURIComponent(imgName)}`;
    img.onload = function() {
      imageCache[imgName] = img;
      drawCanvasWithPreview(projectName, previewBox);
    };
    img.onerror = function() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.font = '20px Arial';
      ctx.fillStyle = '#f63366';
      ctx.fillText('Failed to load image', 20, 40);
    };
    // Show nothing until loaded
    return;
  }

  // Draw using cached image
  // Fit image to canvas
  let scale = Math.min(canvas.width / img.width, canvas.height / img.height);
  let offsetX = (canvas.width - img.width * scale) / 2;
  let offsetY = (canvas.height - img.height * scale) / 2;
  ctx.setTransform(1, 0, 0, 1, 0, 0); // Reset
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.save();
  ctx.translate(offsetX + panX, offsetY + panY);
  ctx.scale(scale * zoomLevel, scale * zoomLevel);
  ctx.drawImage(img, 0, 0);
  // Draw all boxes
  boxes.forEach((box, idx) => {
    ctx.save();
    ctx.strokeStyle = idx === selectedBoxIdx ? '#f63366' : '#00bfff';
    ctx.lineWidth = idx === selectedBoxIdx ? 3 : 2;
    ctx.strokeRect(box.x, box.y, box.w, box.h);
    ctx.font = '16px Arial';
    ctx.fillStyle = idx === selectedBoxIdx ? '#f63366' : '#00bfff';
    ctx.fillText(box.label, box.x + 4, box.y + 18);
    if (idx === selectedBoxIdx) drawHandles(ctx, box);
    ctx.restore();
  });
  // Draw preview box if any
  if (previewBox) {
    ctx.save();
    ctx.strokeStyle = '#f63366';
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    ctx.strokeRect(previewBox.x, previewBox.y, previewBox.w, previewBox.h);
    ctx.setLineDash([]);
    ctx.restore();
  }
  ctx.restore();
}

// When switching images, reset the cache so the new image is loaded
function loadImage(projectName) {
  const imgName = images[currentImageIdx];
  document.getElementById('imageName').innerText = imgName;
  document.getElementById('annoMsg').innerText = '';
  currentLoadedImage = imageCache[imgName] || null;
  currentLoadedImageName = imgName;
  currentLoadedProject = projectName;
  currentLoadedImageIsReady = !!currentLoadedImage;
  canvasLoading = !currentLoadedImage;
  preloadAdjacentImages(projectName, currentImageIdx);
  // Use predictions if available, else fallback to fetchAnnotations
  if (predictions && predictions[imgName] && predictions[imgName][0] && predictions[imgName][0].boxes && predictions[imgName][0].boxes.length > 0) {
    const pred = predictions[imgName][0];
    // Only show labels present in predictions for this image (plus any custom labels)
    const presentClassIndices = Array.from(new Set(pred.classes.map(c => Math.round(c))));
    let presentLabels = presentClassIndices.map(idx => labels[idx]).filter(Boolean);
    if (window.customLabels && Array.isArray(window.customLabels)) {
      presentLabels = [...presentLabels, ...window.customLabels.filter(l => !presentLabels.includes(l))];
    }
    // Convert predictions to boxes format [{x, y, w, h, label}]
    boxes = pred.boxes.map((b, i) => {
      const [x1, y1, x2, y2] = b;
      const classIdx = Math.round(pred.classes[i] || 0);
      return {
        x: x1,
        y: y1,
        w: x2 - x1,
        h: y2 - y1,
        label: labels[classIdx] || presentLabels[0] || ''
      };
    });
    // Store presentLabels for use in renderLabels
    window._presentLabels = presentLabels;
    renderLabels();
    selectedBoxIdx = null;
    drawCanvasWithPreview(projectName);
  } else {
    fetchAnnotations(imgName, projectName).then(data => {
      boxes = Array.isArray(data) ? data : [];
      window._presentLabels = undefined;
      renderLabels();
      selectedBoxIdx = null;
      drawCanvasWithPreview(projectName);
    });
  }
}

function drawHandles(ctx, box) {
  // Draw small squares at corners and edges for resizing
  const handles = getHandlePositions(box);
  ctx.fillStyle = "#fff";
  ctx.strokeStyle = "#f63366";
  handles.forEach(h => {
    ctx.beginPath();
    ctx.rect(h.x-4, h.y-4, 8, 8);
    ctx.fill();
    ctx.stroke();
  });
}

function getHandlePositions(box) {
  // Returns 8 handles: 4 corners, 4 edges
  const {x, y, w, h} = box;
  return [
    {x: x, y: y}, // top-left
    {x: x+w/2, y: y}, // top
    {x: x+w, y: y}, // top-right
    {x: x+w, y: y+h/2}, // right
    {x: x+w, y: y+h}, // bottom-right
    {x: x+w/2, y: y+h}, // bottom
    {x: x, y: y+h}, // bottom-left
    {x: x, y: y+h/2} // left
  ];
}

function hitTestHandle(mx, my, box) {
  const handles = getHandlePositions(box);
  for (let i = 0; i < handles.length; i++) {
    const h = handles[i];
    if (Math.abs(mx - h.x) <= 6 && Math.abs(my - h.y) <= 6) {
      return i;
    }
  }
  return -1;
}

function hitTestBox(mx, my, box) {
  return mx >= box.x && mx <= box.x + box.w && my >= box.y && my <= box.y + box.h;
}

function setupCanvas(projectName) {
  const canvas = document.getElementById('annotateCanvas');
  let isDrawing = false;
  let isEditing = false;
  let startX = 0, startY = 0;
  let previewBox = null;
  let editBoxIdx = null;
  let editDragMode = null;
  let editDragCorner = null;
  let editDragOffset = {x:0, y:0};

  function getMousePos(e) {
    const canvas = e.target;
    const rect = canvas.getBoundingClientRect();
    // Mouse position relative to canvas top-left
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    // Account for zoom and pan
    // First, undo pan (which is in screen/canvas pixels)
    // Then, undo offsetX/offsetY (image centering)
    // Then, undo zoom/scale
    // To get offsetX/offsetY, we need the image and canvas size
    const imgName = images[currentImageIdx];
    let img = imageCache[imgName];
    if (!img) {
      // fallback: no image loaded yet, just use canvas center
      return { x: (x - panX), y: (y - panY) };
    }
    let scale = Math.min(canvas.width / img.width, canvas.height / img.height);
    let offsetX = (canvas.width - img.width * scale) / 2;
    let offsetY = (canvas.height - img.height * scale) / 2;
    // Undo pan, then offset, then scale/zoom
    const realX = (x - panX - offsetX) / (scale * zoomLevel);
    const realY = (y - panY - offsetY) / (scale * zoomLevel);
    return { x: realX, y: realY };
  }

  // --- MODE RADIO HANDLERS ---
  document.getElementById('drawModeRadio').onchange = function() {
    if (this.checked) {
      currentMode = 'draw';
      canvas.style.cursor = 'crosshair';
    }
  };
  document.getElementById('panModeRadio').onchange = function() {
    if (this.checked) {
      currentMode = 'pan';
      canvas.style.cursor = 'grab';
    }
  };
  document.getElementById('zoomInModeRadio').onchange = function() {
    if (this.checked) {
      zoomLevel = Math.min(zoomLevel * 1.25, 8);
      drawCanvasWithPreview(projectName);
      document.getElementById('drawModeRadio').checked = true;
      currentMode = 'draw';
      canvas.style.cursor = 'crosshair';
    }
  };
  document.getElementById('zoomOutModeRadio').onchange = function() {
    if (this.checked) {
      zoomLevel = Math.max(zoomLevel / 1.25, 0.2);
      drawCanvasWithPreview(projectName);
      document.getElementById('drawModeRadio').checked = true;
      currentMode = 'draw';
      canvas.style.cursor = 'crosshair';
    }
  };
  document.getElementById('zoomResetModeRadio').onchange = function() {
    if (this.checked) {
      zoomLevel = 1;
      panX = 0;
      panY = 0;
      drawCanvasWithPreview(projectName);
      document.getElementById('drawModeRadio').checked = true;
      currentMode = 'draw';
      canvas.style.cursor = 'crosshair';
    }
  };
  // Set initial mode
  canvas.style.cursor = 'crosshair';

  // --- PAN LOGIC ---
  canvas.addEventListener('mousedown', function(e) {
    if (currentMode === 'pan' && e.button === 0) {
      isPanning = true;
      const rect = canvas.getBoundingClientRect();
      panStart = {
        x: e.clientX - rect.left - panX,
        y: e.clientY - rect.top - panY
      };
      canvas.style.cursor = 'grabbing';
      return;
    }
    if (currentMode !== 'draw') return;
    const {x: mx, y: my} = getMousePos(e);
    if (isEditing && editBoxIdx !== null) {
      const box = boxes[editBoxIdx];
      const handleIdx = hitTestHandle(mx, my, box);
      if (handleIdx !== -1) {
        editDragMode = 'resize';
        editDragCorner = handleIdx;
        editDragOffset = { x: mx, y: my };
      } else if (hitTestBox(mx, my, box)) {
        editDragMode = 'move';
        editDragOffset = { x: mx - box.x, y: my - box.y };
      } else {
        editDragMode = null;
        editDragCorner = null;
      }
      return;
    }
    startX = mx;
    startY = my;
    isDrawing = true;
    previewBox = null;
    selectedBoxIdx = null;
  });

  canvas.addEventListener('mousemove', function(e) {
    if (isPanning) {
      const rect = canvas.getBoundingClientRect();
      panX = (e.clientX - rect.left) - panStart.x;
      panY = (e.clientY - rect.top) - panStart.y;
      drawCanvasWithPreview(projectName);
      return;
    }
    if (currentMode !== 'draw') return;
    const {x: mx, y: my} = getMousePos(e);
    if (isEditing && editBoxIdx !== null && editDragMode) {
      let box = boxes[editBoxIdx];
      if (editDragMode === 'move') {
        box.x = mx - editDragOffset.x;
        box.y = my - editDragOffset.y;
        drawCanvasWithPreview(projectName);
      } else if (editDragMode === 'resize' && editDragCorner !== null) {
        let dx = mx - editDragOffset.x;
        let dy = my - editDragOffset.y;
        switch (editDragCorner) {
          case 0: box.x += dx; box.y += dy; box.w -= dx; box.h -= dy; break;
          case 1: box.y += dy; box.h -= dy; break;
          case 2: box.y += dy; box.w += dx; box.h -= dy; break;
          case 3: box.w += dx; break;
          case 4: box.w += dx; box.h += dy; break;
          case 5: box.h += dy; break;
          case 6: box.x += dx; box.w -= dx; box.h += dy; break;
          case 7: box.x += dx; box.w -= dx; break;
        }
        editDragOffset = { x: mx, y: my };
        drawCanvasWithPreview(projectName);
      }
      return;
    }
    if (isDrawing) {
      const currX = mx;
      const currY = my;
      previewBox = {
        x: Math.min(startX, currX),
        y: Math.min(startY, currY),
        w: Math.abs(currX - startX),
        h: Math.abs(currY - startY),
        label: labels[0] || ''
      };
      drawCanvasWithPreview(projectName, previewBox);
    }
  });

  canvas.addEventListener('mouseup', function(e) {
    if (isPanning) {
      isPanning = false;
      canvas.style.cursor = 'grab';
      return;
    }
    if (currentMode !== 'draw') return;
    if (isEditing && editBoxIdx !== null && editDragMode) {
      editDragMode = null;
      editDragCorner = null;
      return;
    }
    if (isDrawing) {
      isDrawing = false;
      if (previewBox && previewBox.w > 2 && previewBox.h > 2) {
        boxes.push(previewBox);
        selectedBoxIdx = null;
        renderLabels();
      }
      previewBox = null;
      drawCanvasWithPreview(projectName);
    }
  });

  canvas.addEventListener('dblclick', function(e) {
    const {x: mx, y: my} = getMousePos(e);
    if (isEditing && editBoxIdx !== null) {
      if (!hitTestBox(mx, my, boxes[editBoxIdx])) {
        isEditing = false;
        editBoxIdx = null;
        selectedBoxIdx = null;
        drawCanvasWithPreview(projectName);
        renderLabels();
      }
      return;
    }
    for (let i = boxes.length - 1; i >= 0; i--) {
      if (hitTestBox(mx, my, boxes[i])) {
        isEditing = true;
        editBoxIdx = i;
        selectedBoxIdx = i;
        drawCanvasWithPreview(projectName);
        renderLabels();
        return;
      }
    }
  });

  canvas.addEventListener('mouseleave', function(e) {
    if (isPanning) {
      isPanning = false;
      canvas.style.cursor = 'grab';
    }
  });
}

document.addEventListener('DOMContentLoaded', async function() {
  const params = getProjectAndSubset();
  let projectName = params.project || '';
  let subsetName = params.subset || '';
  const pageTitleElem = document.getElementById('pageTitle');
  if (pageTitleElem) {
    pageTitleElem.innerText = `Manual Annotation: ${projectName || '[No Project]'}`;
  }
  // Render UI shell immediately
  document.getElementById('imageList').innerHTML = '<div class="loading-spinner" style="text-align:center;padding:40px 0;"><span style="font-size:2em;">⏳</span><br>Loading images...</div>';
  renderModeSelector();
  renderModeActionSection();

  // Add navigation arrows below the canvas (UI only, no keyboard events)
  function renderCanvasArrows() {
    let navDiv = document.getElementById('canvasNavArrows');
    if (!navDiv) {
      navDiv = document.createElement('div');
      navDiv.id = 'canvasNavArrows';
      navDiv.style.textAlign = 'center';
      navDiv.style.margin = '10px 0 0 0';
      const canvas = document.getElementById('annotateCanvas');
      canvas.parentNode.insertBefore(navDiv, canvas.nextSibling);
    }
    navDiv.innerHTML =
      `<button id="prevImgBtn" ${currentImageIdx === 0 ? 'disabled' : ''} style="font-size:1.5em;margin-right:20px;">&#8592;</button>` +
      `<span style="font-size:1.1em;">${images.length ? (currentImageIdx+1) : 0} / ${images.length}</span>` +
      `<button id="nextImgBtn" ${currentImageIdx === images.length-1 ? 'disabled' : ''} style="font-size:1.5em;margin-left:20px;">&#8594;</button>`;
    document.getElementById('prevImgBtn').onclick = function() {
      if (currentImageIdx > 0) {
        currentImageIdx--;
        loadImage(projectName);
        renderImageList(projectName);
        drawCanvasWithPreview(projectName);
        renderCanvasArrows();
      }
    };
    document.getElementById('nextImgBtn').onclick = function() {
      if (currentImageIdx < images.length-1) {
        currentImageIdx++;
        loadImage(projectName);
        renderImageList(projectName);
        drawCanvasWithPreview(projectName);
        renderCanvasArrows();
      }
    };
  }

  // Remove keyboard arrow navigation for image switching
  // (No event listener for left/right arrow keys)

  // Add keyboard arrow navigation for image switching
  document.addEventListener('keydown', function(e) {
    if (images.length === 0) return;
    if (e.key === 'ArrowLeft' && currentImageIdx > 0) {
      currentImageIdx--;
      loadImage(projectName);
      renderImageList(projectName);
      drawCanvasWithPreview(projectName);
      if (typeof renderCanvasArrows === 'function') renderCanvasArrows();
      e.preventDefault();
    } else if (e.key === 'ArrowRight' && currentImageIdx < images.length - 1) {
      currentImageIdx++;
      loadImage(projectName);
      renderImageList(projectName);
      drawCanvasWithPreview(projectName);
      if (typeof renderCanvasArrows === 'function') renderCanvasArrows();
      e.preventDefault();
    }
  });

  // Start loading images and predictions in the background
  Promise.all([
    fetchSubsetImages(projectName, subsetName),
    fetchPredictions(projectName)
  ]).then(([imgList, preds]) => {
    images = imgList;
    predictions = preds;
    // Parse all unique class indices from predictions
    const allClassIndices = new Set();
    Object.values(predictions).forEach(arr => {
      if (Array.isArray(arr) && arr[0] && arr[0].classes) {
        arr[0].classes.forEach(c => allClassIndices.add(Math.round(c)));
      }
    });
    presentLabelsGlobal = Array.from(allClassIndices).map(idx => labels[idx]).filter(Boolean);
    if (!images.length) {
      document.getElementById('imageList').innerHTML = '<div>No images to annotate.</div>';
      return;
    }
    renderImageList(projectName);
    setupCanvas(projectName);
    loadImage(projectName);
    setTimeout(() => drawCanvasWithPreview(projectName), 100);
    renderCanvasArrows();
    window.customLabels = [];
    document.getElementById('addLabelBtn').onclick = function() {
      const newLabel = document.getElementById('newLabelInput').value.trim();
      if (newLabel && !presentLabelsGlobal.includes(newLabel)) {
        presentLabelsGlobal.push(newLabel);
        if (!window.customLabels.includes(newLabel)) window.customLabels.push(newLabel);
        renderLabels();
        document.getElementById('newLabelInput').value = '';
      }
    };
  });
});

async function fetchPredictions(projectNameArg) {
  // Fetch auto_annotate_results.json for the project
  const url = `http://localhost:5000/projects/${encodeURIComponent(projectNameArg)}/auto_annotate_results.json`;
  try {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error('Failed to fetch predictions');
    return await resp.json();
  } catch (e) {
    console.error('Error fetching predictions:', e);
    return {};
  }
}