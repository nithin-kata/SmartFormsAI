/* SmartForms AI — Public Form JS */

// ============ RATING STARS ============
function setRating(name, value) {
  document.getElementById(`rating_${name}`).value = value;
  const container = document.querySelector(`[data-name="${name}"]`);
  container?.querySelectorAll('.rating-star').forEach((star, i) => {
    star.classList.toggle('active', i < value);
  });
}

// ============ FILE UPLOAD DISPLAY ============
function showFileName(input) {
  const id = input.id.replace('file_', 'upload_');
  const label = document.getElementById(id);
  if (label && input.files[0]) {
    label.textContent = input.files[0].name;
  }
}

// ============ PROGRESS BAR ============
function updateProgress() {
  const progressBar = document.getElementById('progressBar');
  const progressLabel = document.getElementById('progressLabel');
  if (!progressBar) return;

  const questions = document.querySelectorAll('.public-question[data-required]');
  let answered = 0;

  questions.forEach(q => {
    const qId = q.dataset.questionId;
    const inputs = q.querySelectorAll(`input[name="q_${qId}"], textarea[name="q_${qId}"], select[name="q_${qId}"]`);
    let hasAnswer = false;

    inputs.forEach(input => {
      if (input.type === 'checkbox' || input.type === 'radio') {
        if (input.checked) hasAnswer = true;
      } else if (input.value.trim()) {
        hasAnswer = true;
      }
    });

    if (hasAnswer) answered++;
  });

  const pct = questions.length > 0 ? Math.round((answered / questions.length) * 100) : 0;
  progressBar.style.width = pct + '%';
  if (progressLabel) progressLabel.textContent = `${answered} of ${questions.length} answered`;
}

// ============ FORM SUBMISSION ============
document.getElementById('publicForm')?.addEventListener('submit', function(e) {
  const btn = document.getElementById('submitBtn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin 0.8s linear infinite">
        <circle cx="12" cy="12" r="10" stroke-opacity="0.3"/><path d="M12 2a10 10 0 0110 10"/>
      </svg>
      Submitting...
    `;
  }
});

// ============ EVENT LISTENERS ============
document.addEventListener('DOMContentLoaded', () => {
  // Rating hover effects
  document.querySelectorAll('.public-rating').forEach(container => {
    const stars = container.querySelectorAll('.rating-star');
    stars.forEach((star, idx) => {
      star.addEventListener('mouseenter', () => {
        stars.forEach((s, i) => s.style.color = i <= idx ? '#f59e0b' : '#e2e8f0');
      });
      star.addEventListener('mouseleave', () => {
        const val = parseInt(container.querySelector('input[type=hidden]')?.value || '0');
        stars.forEach((s, i) => { s.style.color = ''; s.classList.toggle('active', i < val); });
      });
    });
  });

  // Progress tracking
  document.querySelectorAll('.public-question input, .public-question textarea, .public-question select').forEach(el => {
    el.addEventListener('change', updateProgress);
    el.addEventListener('input', updateProgress);
  });
  updateProgress();
});

// Spin animation for submit button
const style = document.createElement('style');
style.textContent = `@keyframes spin { to { transform: rotate(360deg); } }`;
document.head.appendChild(style);
