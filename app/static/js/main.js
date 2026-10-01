(() => {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const navToggle = document.querySelector('[data-nav-toggle]');
  const nav = document.querySelector('[data-site-nav]');

  if (navToggle && nav) {
    navToggle.addEventListener('click', () => {
      const isOpen = nav.classList.toggle('is-open');
      navToggle.setAttribute('aria-expanded', String(isOpen));
    });
  }

  const revealItems = document.querySelectorAll('.reveal');
  if (!prefersReducedMotion && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    revealItems.forEach((item) => observer.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add('is-revealed'));
  }

  const loadingOverlay = document.querySelector('[data-loading-overlay]');
  const loadingCopy = document.querySelector('[data-loading-copy]');
  const loadingSubcopy = document.querySelector('[data-loading-subcopy]');
  const loadingStates = [
    ['Analyzing your fitness profile...', 'Reviewing your goal and intensity...'],
    ['Designing your 7-day routine...', 'Balancing recovery and progression...'],
    ['Preparing your recovery guidance...', 'Finalizing the structured response...'],
  ];

  document.querySelectorAll('[data-loading-form]').forEach((form) => {
    form.addEventListener('submit', () => {
      if (!loadingOverlay) return;

      loadingOverlay.hidden = false;
      let step = 0;
      loadingCopy.textContent = loadingStates[0][0];
      loadingSubcopy.textContent = loadingStates[0][1];
      const interval = window.setInterval(() => {
        step += 1;
        const next = loadingStates[Math.min(step, loadingStates.length - 1)];
        loadingCopy.textContent = next[0];
        loadingSubcopy.textContent = next[1];
        if (step >= loadingStates.length - 1) window.clearInterval(interval);
      }, 900);

      window.setTimeout(() => {
        if (!document.hidden && !loadingOverlay.hidden) {
          window.clearInterval(interval);
          loadingOverlay.hidden = true;
          showToast('AI generation is taking too long. Please try again.');
        }
      }, 35000);
    });
  });

  const toastRegion = document.querySelector('[data-toast-region]');
  const showToast = (message) => {
    if (!toastRegion) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    toastRegion.appendChild(toast);
    window.setTimeout(() => toast.remove(), 3200);
  };

  const feedbackInput = document.querySelector('[data-feedback-input]');
  const charCount = document.querySelector('[data-char-count]');
  if (feedbackInput && charCount) {
    const updateCount = () => {
      charCount.textContent = `${feedbackInput.value.length} / 1000`;
    };
    feedbackInput.addEventListener('input', updateCount);
    updateCount();
  }

  document.querySelectorAll('[data-day-card]').forEach((card) => {
    const toggle = card.querySelector('[data-day-toggle]');
    const body = card.querySelector('.day-body');
    const checkbox = card.querySelector('[data-complete-day]');
    const planId = document.querySelector('[data-plan-id]')?.dataset.planId || 'default';
    const dayNumber = card.dataset.dayNumber;
    const storageKey = `fitbuddy-complete-${planId}`;
    const saved = JSON.parse(localStorage.getItem(storageKey) || '[]');

    if (saved.includes(Number(dayNumber))) {
      checkbox.checked = true;
      card.classList.add('is-complete');
    }

    toggle?.addEventListener('click', () => {
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!expanded));
      if (body) body.hidden = expanded;
      const chevron = card.querySelector('.chevron');
      if (chevron) chevron.textContent = expanded ? '+' : '–';
    });

    checkbox?.addEventListener('change', () => {
      const current = new Set(JSON.parse(localStorage.getItem(storageKey) || '[]'));
      const day = Number(dayNumber);
      if (checkbox.checked) {
        current.add(day);
        card.classList.add('is-complete');
        showToast(`Day ${day} marked complete.`);
      } else {
        current.delete(day);
        card.classList.remove('is-complete');
      }
      localStorage.setItem(storageKey, JSON.stringify([...current]));
    });
  });

  const statusMessage = document.querySelector('.success-banner');
  if (statusMessage) {
    showToast(statusMessage.textContent.trim());
  }
})();
