// ============================================================
// TaskMaster Pro - Frontend JavaScript Enhancements
// ============================================================

document.addEventListener('DOMContentLoaded', function () {
  // Initialize Bootstrap Tooltips if available
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Auto-dismiss Flash Alerts after 5 seconds
  const flashAlerts = document.querySelectorAll('.alert-dismissible');
  flashAlerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      } else {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 250);
      }
    }, 4500);
  });

  // Dynamic Character Counter for Task Title (if on form page)
  const titleInput = document.getElementById('title');
  const titleCharCount = document.getElementById('title-char-count');
  if (titleInput && titleCharCount) {
    const updateCount = () => {
      const len = titleInput.value.length;
      titleCharCount.textContent = `${len}/150`;
      if (len > 140) {
        titleCharCount.classList.add('text-danger');
      } else {
        titleCharCount.classList.remove('text-danger');
      }
    };
    titleInput.addEventListener('input', updateCount);
    updateCount();
  }
});
