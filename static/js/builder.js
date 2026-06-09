/* SmartForms AI — Form Builder JS */

let editingQuestionId = null;
let dragSrcEl = null;
window.QUESTIONS_BY_ID = window.QUESTIONS_BY_ID || {};

function normalizeQuestion(q) {
  const normalized = { ...q };
  normalized.id = Number(normalized.id);
  normalized.question_text = String(normalized.question_text || 'Untitled Question');
  normalized.question_type = normalized.question_type || 'short_text';
  normalized.is_required = !!normalized.is_required;
  normalized.placeholder = normalized.placeholder || '';
  if (typeof normalized.options === 'string') {
    try {
      normalized.options = JSON.parse(normalized.options || '[]');
    } catch {
      normalized.options = [];
    }
  }
  if (!Array.isArray(normalized.options)) normalized.options = [];

  if (typeof normalized.logic_rules === 'string') {
    try {
      normalized.logic_rules = JSON.parse(normalized.logic_rules || '[]');
    } catch {
      normalized.logic_rules = [];
    }
  }
  if (!Array.isArray(normalized.logic_rules)) normalized.logic_rules = [];
  return normalized;
}

function registerQuestions(questions) {
  (questions || []).forEach(q => {
    const normalized = normalizeQuestion(q);
    window.QUESTIONS_BY_ID[normalized.id] = normalized;
  });
}

function storeQuestion(q) {
  const normalized = normalizeQuestion(q);
  window.QUESTIONS_BY_ID[normalized.id] = normalized;
  return normalized;
}

// ============ ADD QUESTION ============
function addQuestion(type) {
  const defaultTexts = {
    short_text: 'Short answer question',
    long_text: 'Long answer question',
    email: 'Email address',
    phone: 'Phone number',
    multiple_choice: 'Multiple choice question',
    checkboxes: 'Checkboxes question',
    dropdown: 'Dropdown question',
    rating: 'Rate your experience',
    yes_no: 'Yes or No question',
    date: 'Date',
    file_upload: 'Upload a file'
  };

  const defaultOptions = {
    multiple_choice: ['Option 1', 'Option 2', 'Option 3'],
    checkboxes: ['Option 1', 'Option 2', 'Option 3'],
    dropdown: ['Option 1', 'Option 2', 'Option 3']
  };

  const payload = {
    question_text: defaultTexts[type] || 'New Question',
    question_type: type,
    is_required: false,
    options: defaultOptions[type] || [],
    placeholder: ''
  };

  fetch(`/api/forms/${FORM_ID}/questions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      appendQuestionCard(data.question);
      updateCounts();
      removeEmptyState();
      showToast('Question added!');
    } else {
      showToast(data.error || 'Failed to add question', 'error');
    }
  });
}

// ============ APPEND QUESTION CARD TO DOM ============
function appendQuestionCard(q) {
  const container = document.getElementById('questionsList');
  const card = createQuestionCard(q);
  container.appendChild(card);
  card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function createQuestionCard(q) {
  q = storeQuestion(q);
  const div = document.createElement('div');
  div.className = 'question-card';
  div.dataset.questionId = q.id;
  div.draggable = true;

  const optionBadges = ['multiple_choice','checkboxes','dropdown'].includes(q.question_type) && q.options?.length
    ? `<div class="question-options-preview">
        ${q.options.slice(0,3).map(o => `<span class="option-chip">${escHtml(o)}</span>`).join('')}
        ${q.options.length > 3 ? `<span class="option-chip option-chip-more">+${q.options.length-3} more</span>` : ''}
       </div>`
    : '';

  const ratingPreview = q.question_type === 'rating'
    ? '<div class="rating-preview">★★★★★</div>'
    : '';

  div.innerHTML = `
    <div class="question-drag-handle">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="8" cy="8" r="1" fill="currentColor"/><circle cx="16" cy="8" r="1" fill="currentColor"/>
        <circle cx="8" cy="12" r="1" fill="currentColor"/><circle cx="16" cy="12" r="1" fill="currentColor"/>
        <circle cx="8" cy="16" r="1" fill="currentColor"/><circle cx="16" cy="16" r="1" fill="currentColor"/>
      </svg>
    </div>
    <div class="question-content">
      <div class="question-meta">
        <span class="question-type-badge">${formatQuestionType(q.question_type)}</span>
        ${q.is_required ? '<span class="required-badge">Required</span>' : ''}
      </div>
      <div class="question-text" contenteditable="true"
           onblur="saveQuestionText(${q.id}, this.textContent)"
           data-original="${escAttr(q.question_text)}">${escHtml(q.question_text)}</div>
      ${optionBadges}
      ${ratingPreview}
    </div>
    <div class="question-actions">
      <button class="question-action-btn" onclick="editQuestion(${q.id})" title="Edit">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
      </button>
      <button class="question-action-btn question-action-danger" onclick="deleteQuestion(${q.id})" title="Delete">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3,6 5,6 21,6"/><path d="M19 6l-1 14H6L5 6M10 11v6M14 11v6"/></svg>
      </button>
    </div>
  `;

  setupDragHandlers(div);
  return div;
}

function formatQuestionType(type) {
  return String(type || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function replaceQuestionCard(q) {
  const normalized = storeQuestion(q);
  const current = document.querySelector(`[data-question-id="${normalized.id}"]`);
  const replacement = createQuestionCard(normalized);
  if (current) {
    current.replaceWith(replacement);
  } else {
    document.getElementById('questionsList')?.appendChild(replacement);
  }
}

function escHtml(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function escAttr(str) {
  return String(str || '').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

// ============ DRAG AND DROP ============
function setupDragHandlers(el) {
  el.addEventListener('dragstart', e => {
    dragSrcEl = el;
    el.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
  });
  el.addEventListener('dragend', () => {
    el.classList.remove('dragging');
    document.querySelectorAll('.question-card').forEach(c => c.classList.remove('drag-over'));
    saveOrder();
  });
  el.addEventListener('dragover', e => {
    e.preventDefault();
    if (el !== dragSrcEl) {
      document.querySelectorAll('.question-card').forEach(c => c.classList.remove('drag-over'));
      el.classList.add('drag-over');
      const container = document.getElementById('questionsList');
      const rect = el.getBoundingClientRect();
      const mid = rect.top + rect.height / 2;
      if (e.clientY < mid) {
        container.insertBefore(dragSrcEl, el);
      } else {
        container.insertBefore(dragSrcEl, el.nextSibling);
      }
    }
  });
}

// Set up drag on existing cards
document.querySelectorAll('.question-card').forEach(setupDragHandlers);

function saveOrder() {
  const ids = [...document.querySelectorAll('.question-card')].map(el => parseInt(el.dataset.questionId));
  fetch(`/api/forms/${FORM_ID}/reorder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ order: ids })
  });
}

// ============ EDIT QUESTION ============
function editQuestion(id) {
  const q = window.QUESTIONS_BY_ID[Number(id)];
  if (!q) {
    showToast('Question data is still loading. Refresh and try again.', 'error');
    return;
  }
  editingQuestionId = id;
  document.getElementById('editQuestionText').value = q.question_text || '';
  document.getElementById('editQuestionType').value = q.question_type || 'short_text';
  document.getElementById('editRequired').checked = !!q.is_required;
  document.getElementById('editPlaceholder').value = q.placeholder || '';
  updateEditOptions(q.options || []);
  updateEditLogic(q.logic_rules || []);
  document.getElementById('editModal').style.display = 'flex';
}

function updateEditOptions(existingOptions) {
  const typeEl = document.getElementById('editQuestionType');
  const section = document.getElementById('editOptionsSection');
  if (!typeEl || !section) return;

  const type = typeEl.value;
  const hasOptions = ['multiple_choice', 'checkboxes', 'dropdown'].includes(type);
  section.style.display = hasOptions ? 'block' : 'none';

  if (hasOptions) {
    const list = document.getElementById('editOptionsList');
    const opts = existingOptions || (list && list.children.length
      ? [...document.querySelectorAll('.edit-option-input')].map(i => i.value)
      : ['Option 1', 'Option 2', 'Option 3']);
    renderOptionFields(Array.isArray(opts) ? opts : ['Option 1', 'Option 2', 'Option 3']);
  }

  // Also update logic dropdown choices based on current options
  const q = editingQuestionId ? window.QUESTIONS_BY_ID[Number(editingQuestionId)] : null;
  updateEditLogic(q ? q.logic_rules : []);
}

function updateEditLogic(existingRules) {
  const typeEl = document.getElementById('editQuestionType');
  const section = document.getElementById('editLogicSection');
  if (!typeEl || !section) return;

  const type = typeEl.value;
  const supportsLogic = ['multiple_choice', 'dropdown', 'yes_no'].includes(type);
  section.style.display = supportsLogic ? 'block' : 'none';

  if (supportsLogic) {
    renderLogicRuleFields(existingRules || []);
  }
}

function renderLogicRuleFields(rules) {
  const list = document.getElementById('editLogicRulesList');
  const typeEl = document.getElementById('editQuestionType');
  if (!list || !typeEl) return;
  const type = typeEl.value;
  
  let options = [];
  if (type === 'yes_no') {
    options = ['Yes', 'No'];
  } else {
    options = [...document.querySelectorAll('.edit-option-input')].map(i => i.value.trim()).filter(Boolean);
    if (!options.length) {
      options = ['Option 1', 'Option 2', 'Option 3'];
    }
  }

  const allCards = [...document.querySelectorAll('.question-card')];
  const currentIndex = allCards.findIndex(c => Number(c.dataset.questionId) === Number(editingQuestionId));
  const subsequentQuestions = allCards.slice(currentIndex + 1).map(c => {
    const qId = Number(c.dataset.questionId);
    const qObj = window.QUESTIONS_BY_ID[qId];
    return {
      id: qId,
      text: qObj ? qObj.question_text : `Question (ID: ${qId})`
    };
  });

  list.innerHTML = '';
  if (!rules.length) {
    list.innerHTML = '<p style="font-size:12px;color:var(--text-secondary);font-style:italic;">No rules defined.</p>';
    return;
  }

  rules.forEach((rule, idx) => {
    const row = document.createElement('div');
    row.className = 'edit-logic-row';
    row.style.cssText = 'display:flex;align-items:center;gap:6px;margin-bottom:6px;';
    
    let optionsHtml = options.map(o => `<option value="${escAttr(o)}" ${rule.value === o ? 'selected' : ''}>${escHtml(o)}</option>`).join('');
    let targetsHtml = subsequentQuestions.map(q => `<option value="${q.id}" ${Number(rule.target_id) === q.id ? 'selected' : ''}>Go to: ${escHtml(q.text.substring(0, 30))}</option>`).join('');
    targetsHtml += `<option value="submit" ${rule.target_id === 'submit' ? 'selected' : ''}>Submit Form</option>`;

    row.innerHTML = `
      <span style="font-size:12.5px;color:var(--text-secondary);flex-shrink:0;">If answer is</span>
      <select class="form-select edit-logic-val" style="padding:6px;font-size:13px;height:auto;margin:0;">
        ${optionsHtml}
      </select>
      <span style="font-size:12.5px;color:var(--text-secondary);flex-shrink:0;">then</span>
      <select class="form-select edit-logic-target" style="padding:6px;font-size:13px;height:auto;margin:0;">
        ${targetsHtml}
      </select>
      <button type="button" class="btn btn-ghost btn-xs" onclick="this.parentElement.remove()" style="flex-shrink:0;font-weight:700;">×</button>
    `;
    list.appendChild(row);
  });
}

function addLogicRuleField() {
  const list = document.getElementById('editLogicRulesList');
  const typeEl = document.getElementById('editQuestionType');
  if (!list || !typeEl) return;
  if (list.querySelector('p')) {
    list.innerHTML = '';
  }
  
  const type = typeEl.value;
  let options = [];
  if (type === 'yes_no') {
    options = ['Yes', 'No'];
  } else {
    options = [...document.querySelectorAll('.edit-option-input')].map(i => i.value.trim()).filter(Boolean);
    if (!options.length) {
      options = ['Option 1', 'Option 2', 'Option 3'];
    }
  }

  const allCards = [...document.querySelectorAll('.question-card')];
  const currentIndex = allCards.findIndex(c => Number(c.dataset.questionId) === Number(editingQuestionId));
  const subsequentQuestions = allCards.slice(currentIndex + 1).map(c => {
    const qId = Number(c.dataset.questionId);
    const qObj = window.QUESTIONS_BY_ID[qId];
    return {
      id: qId,
      text: qObj ? qObj.question_text : `Question (ID: ${qId})`
    };
  });

  const row = document.createElement('div');
  row.className = 'edit-logic-row';
  row.style.cssText = 'display:flex;align-items:center;gap:6px;margin-bottom:6px;';
  
  let optionsHtml = options.map(o => `<option value="${escAttr(o)}">${escHtml(o)}</option>`).join('');
  let targetsHtml = subsequentQuestions.map(q => `<option value="${q.id}">Go to: ${escHtml(q.text.substring(0, 30))}</option>`).join('');
  targetsHtml += `<option value="submit">Submit Form</option>`;

  row.innerHTML = `
    <span style="font-size:12.5px;color:var(--text-secondary);flex-shrink:0;">If answer is</span>
    <select class="form-select edit-logic-val" style="padding:6px;font-size:13px;height:auto;margin:0;">
      ${optionsHtml}
    </select>
    <span style="font-size:12.5px;color:var(--text-secondary);flex-shrink:0;">then</span>
    <select class="form-select edit-logic-target" style="padding:6px;font-size:13px;height:auto;margin:0;">
      ${targetsHtml}
    </select>
    <button type="button" class="btn btn-ghost btn-xs" onclick="this.parentElement.remove()" style="flex-shrink:0;font-weight:700;">×</button>
  `;
  list.appendChild(row);
}

function renderOptionFields(options) {
  const list = document.getElementById('editOptionsList');
  if (!list) return;
  list.innerHTML = options.map((opt, i) => `
    <div class="edit-option-row" style="display:flex;gap:6px;margin-bottom:6px;">
      <input type="text" class="form-input edit-option-input" value="${escAttr(opt)}" placeholder="Option ${i+1}">
      <button type="button" class="btn btn-ghost btn-xs" onclick="this.parentElement.remove()" style="flex-shrink:0">×</button>
    </div>
  `).join('');
}

function addOptionField() {
  const list = document.getElementById('editOptionsList');
  if (!list) return;
  const row = document.createElement('div');
  row.className = 'edit-option-row';
  row.style.cssText = 'display:flex;gap:6px;margin-bottom:6px;';
  row.innerHTML = `
    <input type="text" class="form-input edit-option-input" placeholder="New option">
    <button type="button" class="btn btn-ghost btn-xs" onclick="this.parentElement.remove()" style="flex-shrink:0">×</button>
  `;
  list.appendChild(row);
  row.querySelector('input').focus();
}

function saveQuestion() {
  const textEl = document.getElementById('editQuestionText');
  if (!textEl) return;
  const text = textEl.value.trim();
  if (!text) { showToast('Question text is required', 'error'); return; }

  const typeEl = document.getElementById('editQuestionType');
  const requiredEl = document.getElementById('editRequired');
  const placeholderEl = document.getElementById('editPlaceholder');
  if (!typeEl || !requiredEl || !placeholderEl) return;

  const type = typeEl.value;
  const required = requiredEl.checked;
  const placeholder = placeholderEl.value.trim();
  const options = ['multiple_choice','checkboxes','dropdown'].includes(type)
    ? [...document.querySelectorAll('.edit-option-input')].map(i => i.value.trim()).filter(Boolean)
    : [];

  const logic_rules = [];
  if (['multiple_choice', 'dropdown', 'yes_no'].includes(type)) {
    document.querySelectorAll('.edit-logic-row').forEach(row => {
      const valEl = row.querySelector('.edit-logic-val');
      const targetEl = row.querySelector('.edit-logic-target');
      if (valEl && targetEl) {
        logic_rules.push({
          value: valEl.value,
          action: 'jump',
          target_id: targetEl.value === 'submit' ? 'submit' : Number(targetEl.value)
        });
      }
    });
  }

  fetch(`/api/questions/${editingQuestionId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question_text: text, question_type: type, is_required: required, options, placeholder, logic_rules })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      replaceQuestionCard(data.question);
      updateCounts();
      closeEditModal();
      showToast('Question saved!');
    } else {
      showToast(data.error || 'Failed to save', 'error');
    }
  });
}

function closeEditModal() {
  document.getElementById('editModal').style.display = 'none';
  editingQuestionId = null;
}

// ============ DELETE QUESTION ============
function deleteQuestion(id) {
  if (!confirm('Delete this question?')) return;
  fetch(`/api/questions/${id}`, { method: 'DELETE' })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      const card = document.querySelector(`[data-question-id="${id}"]`);
      card?.remove();
      updateCounts();
      if (!document.querySelectorAll('.question-card').length) showEmptyState();
      showToast('Question deleted');
    }
  });
}

// ============ SAVE QUESTION TEXT (INLINE EDIT) ============
function saveQuestionText(id, text) {
  text = text.trim();
  if (!text) return;
  fetch(`/api/questions/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question_text: text })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success && data.question) {
      storeQuestion(data.question);
      const card = document.querySelector(`[data-question-id="${id}"]`);
      if (card) {
        card.querySelector('.question-text').dataset.original = data.question.question_text;
        // Show "Saved ✓" badge
        let badge = card.querySelector('.saved-badge');
        if (!badge) {
          badge = document.createElement('span');
          badge.className = 'saved-badge';
          badge.style.cssText = 'font-size:11px;color:#10b981;font-weight:600;margin-left:8px;opacity:1;transition:opacity .4s';
          card.querySelector('.question-meta').appendChild(badge);
        }
        badge.textContent = '✓ Saved';
        badge.style.opacity = '1';
        clearTimeout(badge._t);
        badge._t = setTimeout(() => { badge.style.opacity = '0'; }, 1500);
      }
    }
  });
}

// ============ AI GENERATE ============
function openAIModal() {
  document.getElementById('aiModal').style.display = 'flex';
  document.getElementById('aiModalPrompt').focus();
}
function closeAIModal() {
  document.getElementById('aiModal').style.display = 'none';
}

function generateQuestionsAI() {
  const prompt = document.getElementById('aiModalPrompt').value.trim();
  if (!prompt) { showToast('Please describe what questions you need', 'error'); return; }

  const btn = document.querySelector('#aiModal .btn-ai');
  btn.disabled = true; btn.textContent = 'Generating...';

  fetch('/api/forms/ai-generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt: `For the form "${document.querySelector('.canvas-title')?.textContent || 'this form'}", add questions about: ${prompt}` })
  })
  .then(r => r.json())
  .then(data => {
    btn.disabled = false; btn.textContent = 'Generate →';
    if (data.success) {
      addAIQuestions(data.data.questions || []);
      closeAIModal();
      showToast(`Added ${data.data.questions?.length || 0} AI-generated questions!`);
    } else {
      showToast(data.error || 'Generation failed. Check your API key in Settings.', 'error');
    }
  })
  .catch(() => {
    btn.disabled = false; btn.textContent = 'Generate →';
    showToast('Connection failed', 'error');
  });
}

function addAIQuestions(questions) {
  if (!questions?.length) return;
  let delay = 0;
  questions.forEach(q => {
    setTimeout(() => {
      const payload = {
        question_text: q.question_text,
        question_type: q.question_type || 'short_text',
        is_required: q.is_required || false,
        options: q.options || [],
        placeholder: q.placeholder || ''
      };
      fetch(`/api/forms/${FORM_ID}/questions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          appendQuestionCard(data.question);
          updateCounts();
          removeEmptyState();
        }
      });
    }, delay);
    delay += 200;
  });
}

// ============ COUNT HELPERS ============
function updateCounts() {
  const cards = document.querySelectorAll('.question-card');
  const required = [...cards].filter(c => c.querySelector('.required-badge')).length;
  const qCount = document.getElementById('questionCount');
  const rCount = document.getElementById('requiredCount');
  if (qCount) qCount.textContent = cards.length;
  if (rCount) rCount.textContent = required;
}

function removeEmptyState() {
  document.getElementById('questionsEmpty')?.remove();
}

function showEmptyState() {
  const container = document.getElementById('questionsList');
  if (!document.getElementById('questionsEmpty')) {
    container.innerHTML = `
      <div class="questions-empty" id="questionsEmpty">
        <div class="questions-empty-icon">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><path d="M9 12h6M9 16h6M9 8h6M5 4h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2z"/></svg>
        </div>
        <h3>No questions yet</h3>
        <p>Add a question from the panel on the right, or use AI to generate questions automatically.</p>
      </div>
    `;
  }
}

// ============ KEYBOARD SHORTCUTS ============
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    closeEditModal();
    closeAIModal();
  }
});

// ============ CLOSE MODALS ON OVERLAY CLICK ============
document.getElementById('editModal')?.addEventListener('click', e => {
  if (e.target === document.getElementById('editModal')) closeEditModal();
});
document.getElementById('aiModal')?.addEventListener('click', e => {
  if (e.target === document.getElementById('aiModal')) closeAIModal();
});
