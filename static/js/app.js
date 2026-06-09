/* SmartForms AI — Main Application JS */

// ============ SIDEBAR TOGGLE ============
const sidebar = document.getElementById('sidebar');
const menuToggle = document.getElementById('menuToggle');
const sidebarClose = document.getElementById('sidebarClose');
const sidebarOverlay = document.getElementById('sidebarOverlay');

function openSidebar() {
  sidebar?.classList.add('open');
  sidebarOverlay?.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeSidebar() {
  sidebar?.classList.remove('open');
  sidebarOverlay?.classList.remove('open');
  document.body.style.overflow = '';
}

menuToggle?.addEventListener('click', openSidebar);
sidebarClose?.addEventListener('click', closeSidebar);
sidebarOverlay?.addEventListener('click', closeSidebar);

// ============ TOAST NOTIFICATIONS ============
(function injectToastCSS() {
  if (document.getElementById('toast-styles')) return;
  const s = document.createElement('style');
  s.id = 'toast-styles';
  s.textContent = [
    '.toast-container{position:fixed;bottom:24px;right:24px;display:flex;flex-direction:column;gap:8px;z-index:9999;pointer-events:none;}',
    '.toast{background:#0f172a;color:#fff;padding:12px 18px;border-radius:10px;font-size:14px;font-weight:500;',
    'box-shadow:0 8px 24px rgba(0,0,0,0.18);display:flex;align-items:center;gap:10px;',
    'animation:toastIn 0.25s ease;pointer-events:auto;max-width:360px;}',
    '.toast::before{content:"\\2713";font-weight:700;color:#34d399;}',
    '.toast-error{background:#991b1b;}.toast-error::before{content:"\\2715";color:#fca5a5;}',
    '.toast-info{background:#1e40af;}.toast-info::before{content:"i";color:#93c5fd;font-style:italic;}',
    '@keyframes toastIn{from{opacity:0;transform:translateY(10px) scale(0.96);}to{opacity:1;transform:translateY(0) scale(1);}}'
  ].join('');
  document.head.appendChild(s);
})();

function showToast(message, type) {
  type = type || 'success';
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = 'toast' + (type === 'error' ? ' toast-error' : type === 'info' ? ' toast-info' : '');
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(function() {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    toast.style.transition = 'opacity 0.22s, transform 0.22s';
    setTimeout(function() { toast.remove(); }, 250);
  }, 3200);
}

// ============ COPY TO CLIPBOARD ============
function copyToClipboard(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(
      function() { showToast('Link copied to clipboard!'); },
      function() { fallbackCopyToClipboard(text); }
    );
  } else {
    fallbackCopyToClipboard(text);
  }
}

function fallbackCopyToClipboard(text) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.style.top = "0";
  textArea.style.left = "0";
  textArea.style.position = "fixed";
  textArea.style.opacity = "0";
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();
  try {
    const successful = document.execCommand('copy');
    if (successful) {
      showToast('Link copied to clipboard!');
    } else {
      showToast('Failed to copy link', 'error');
    }
  } catch (err) {
    showToast('Failed to copy link', 'error');
  }
  document.body.removeChild(textArea);
}


// ============ KEYBOARD SHORTCUTS ============
document.addEventListener('keydown', function(e) {
  // Escape: close any open modal or AI panel
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay, .ai-panel-overlay').forEach(function(el) {
      if (el.style.display !== 'none') el.style.display = 'none';
    });
    document.querySelectorAll('.dropdown-menu.open').forEach(function(m) { m.classList.remove('open'); });
  }
  // Ctrl+S / Cmd+S: trigger save in builder
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    const saveBtn = document.querySelector('[data-save-shortcut]');
    if (saveBtn) { e.preventDefault(); saveBtn.click(); }
  }
});

// ============ AUTO DISMISS FLASH MESSAGES ============
document.addEventListener('DOMContentLoaded', function() {
  const flashContainer = document.getElementById('flashContainer');
  if (flashContainer) {
    setTimeout(function() {
      flashContainer.style.opacity = '0';
      flashContainer.style.transition = 'opacity 0.4s ease';
      setTimeout(function() { flashContainer.remove(); }, 400);
    }, 4000);
  }

  // Time-based greeting
  const greetEl = document.getElementById('greeting-text');
  if (greetEl) {
    const h = new Date().getHours();
    const greeting = h >= 5 && h < 12 ? 'Good morning' :
                     h >= 12 && h < 17 ? 'Good afternoon' :
                     h >= 17 && h < 22 ? 'Good evening' : 'Good night';
    greetEl.textContent = greeting + (greetEl.dataset.suffix || '');
  }
});

// ============ CARD HOVER 3D TILT ============
document.addEventListener('DOMContentLoaded', function() {
  const tiltCards = document.querySelectorAll('.stat-card, .form-card');
  tiltCards.forEach(function(card) {
    card.addEventListener('mousemove', function(e) {
      const rect = card.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      card.style.transform = 'translateY(-2px) rotateX(' + (-y * 3) + 'deg) rotateY(' + (x * 3) + 'deg)';
    });
    card.addEventListener('mouseleave', function() { card.style.transform = ''; });
  });
});
