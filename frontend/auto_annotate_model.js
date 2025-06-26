// auto_annotate_model.js
// Handles navigation and project context for auto annotation model page

function getProjectName() {
  const params = new URLSearchParams(window.location.search);
  return params.get('name');
}

document.addEventListener('DOMContentLoaded', function() {
  const projectName = getProjectName();
  // Optionally, display project name or use it for API calls
  // Update back button to preserve project context
  const backBtn = document.getElementById('backToProjectBtn');
  if (backBtn) {
    backBtn.onclick = function() {
      window.location.href = `project.html?name=${encodeURIComponent(projectName)}`;
    };
  }
});
