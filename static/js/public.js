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

  // Only count visible required questions
  const questions = [...document.querySelectorAll('.public-question[data-required]')].filter(q => q.style.display !== 'none');
  let answered = 0;

  questions.forEach(q => {
    const qId = q.dataset.questionId;
    const inputs = q.querySelectorAll(`input[name="q_${qId}"], textarea[name="q_${qId}"], select[name="q_${qId}"], input[type="hidden"]`);
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

// ============ BRANCHING / SKIP ENGINE ============
const ORIGINALLY_REQUIRED = {};

function initRequiredMapping() {
  document.querySelectorAll('.public-question').forEach(card => {
    const qId = Number(card.dataset.questionId);
    if (card.dataset.required === '1' || card.dataset.required === 'true') {
      ORIGINALLY_REQUIRED[qId] = true;
    }
  });
}

function evaluateBranching() {
  if (typeof QUESTIONS === 'undefined' || !Array.isArray(QUESTIONS)) return;

  const visibility = {};
  QUESTIONS.forEach(q => {
    visibility[q.id] = true;
  });

  for (let i = 0; i < QUESTIONS.length; i++) {
    const q = QUESTIONS[i];
    const qId = q.id;

    if (!visibility[qId]) continue;

    const value = getQuestionValue(qId);
    if (!value) continue;

    const rules = q.logic_rules || [];
    const matchingRule = rules.find(r => r.value.toLowerCase() === value.toLowerCase());

    if (matchingRule) {
      const target = matchingRule.target_id;
      if (target === 'submit') {
        for (let j = i + 1; j < QUESTIONS.length; j++) {
          visibility[QUESTIONS[j].id] = false;
        }
        break;
      } else {
        const targetId = Number(target);
        let hiding = true;
        for (let j = i + 1; j < QUESTIONS.length; j++) {
          const nextQ = QUESTIONS[j];
          if (nextQ.id === targetId) {
            hiding = false;
          }
          if (hiding) {
            visibility[nextQ.id] = false;
          }
        }
      }
    }
  }

  // Update DOM state
  QUESTIONS.forEach(q => {
    const card = document.querySelector(`.public-question[data-question-id="${q.id}"]`);
    if (!card) return;

    const shouldShow = visibility[q.id];
    if (shouldShow) {
      card.style.display = 'block';
      if (ORIGINALLY_REQUIRED[q.id]) {
        card.querySelectorAll('input, textarea, select').forEach(input => {
          if (input.type !== 'hidden') input.required = true;
        });
      }
    } else {
      card.style.display = 'none';
      card.querySelectorAll('input, textarea, select').forEach(input => {
        input.required = false;
        if (input.type === 'checkbox' || input.type === 'radio') {
          input.checked = false;
        } else if (input.type !== 'hidden') {
          input.value = '';
        }
      });
    }
  });
}

function getQuestionValue(qId) {
  const container = document.querySelector(`.public-question[data-question-id="${qId}"]`);
  if (!container) return null;

  const textInput = container.querySelector(`input[type="text"][name="q_${qId}"], select[name="q_${qId}"], input[type="email"][name="q_${qId}"], input[type="tel"][name="q_${qId}"], input[type="date"][name="q_${qId}"]`);
  if (textInput) return textInput.value.trim();

  const checkedRadio = container.querySelector(`input[type="radio"][name="q_${qId}"]:checked`);
  if (checkedRadio) return checkedRadio.value;

  const ratingInput = document.getElementById(`rating_q_${qId}`);
  if (ratingInput) return ratingInput.value;

  return null;
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

  // Init Required mappings
  initRequiredMapping();

  // Progress & branching tracking
  const inputs = document.querySelectorAll('.public-question input, .public-question textarea, .public-question select');
  inputs.forEach(el => {
    const handler = () => {
      evaluateBranching();
      updateProgress();
    };
    el.addEventListener('change', handler);
    el.addEventListener('input', handler);
  });

  evaluateBranching();
  updateProgress();
});

// Spin animation for submit button
const style = document.createElement('style');
style.textContent = `@keyframes spin { to { transform: rotate(360deg); } }`;
document.head.appendChild(style);
