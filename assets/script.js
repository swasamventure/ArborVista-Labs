const menu = document.querySelector('.menu');
const links = document.querySelector('.links');
if (menu && links) {
  menu.setAttribute('aria-expanded', 'false');
  menu.addEventListener('click', () => {
    const open = links.classList.toggle('open');
    menu.setAttribute('aria-expanded', String(open));
  });
  links.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
    links.classList.remove('open');
    menu.setAttribute('aria-expanded', 'false');
  }));
}

document.querySelectorAll('[data-year]').forEach((element) => {
  element.textContent = new Date().getFullYear();
});

function safeStorageGet(key) {
  try { return localStorage.getItem(key); } catch (_) { return null; }
}
function safeStorageSet(key, value) {
  try { localStorage.setItem(key, value); return true; } catch (_) { return false; }
}
function safeStorageRemove(key) {
  try { localStorage.removeItem(key); } catch (_) { /* Storage unavailable. */ }
}

function localDateISO(value = new Date()) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function showSuccess(form, id) {
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const data = {};
    [...form.elements].forEach((element) => {
      if (!element.name) return;
      data[element.name] = element.type === 'checkbox' ? element.checked : element.value;
    });
    safeStorageSet(id, JSON.stringify({ ...data, submittedAt: new Date().toISOString() }));
    document.querySelector(`[data-success="${id}"]`)?.classList.add('show');
    form.reset();
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
  });
}

document.querySelectorAll('form[data-save]').forEach((form) => showSuccess(form, form.dataset.save));

const arrival = document.querySelector('[data-arrival]');
if (arrival) {
  const arrivalDate = new Date(`${arrival.dataset.arrival}T16:00:00`);
  const days = Math.max(0, Math.ceil((arrivalDate - new Date()) / 86400000));
  arrival.textContent = days === 0 ? 'Today' : `${days} day${days === 1 ? '' : 's'}`;
}

const portalGate = safeStorageGet('gate-pass-demo');
if (portalGate) {
  document.querySelectorAll('[data-gate-status]').forEach((element) => {
    element.textContent = 'Information received — processing';
  });
  document.querySelectorAll('[data-gate-pill]').forEach((element) => element.classList.add('done'));
}

// v2.8 hardened guided Book Direct flow with safe rendering and 24-hour draft autosave.
(() => {
  const form = document.getElementById('bookingFlow');
  if (!form) return;

  const DRAFT_KEY = 'arbor-vista-booking-draft-v2';
  const REQUEST_KEY = 'arbor-vista-booking-request';
  const DRAFT_TTL = 24 * 60 * 60 * 1000;
  const MAX_REQUESTED_GUESTS = 8;
  const panels = [...form.querySelectorAll('[data-booking-step]')];
  const nav = [...document.querySelectorAll('[data-step-nav]')];
  const progress = document.querySelector('[data-progress-bar]');
  let current = 1;
  let saveTimer;

  const iso = localDateISO();
  const checkIn = form.elements.check_in;
  const checkOut = form.elements.check_out;
  const agreementDate = form.elements.agreement_date;
  if (checkIn) checkIn.min = iso;
  if (checkOut) checkOut.min = iso;
  if (agreementDate) {
    agreementDate.min = iso;
    agreementDate.max = iso;
  }

  function normalizeName(value) {
    return String(value || '').trim().replace(/\s+/g, ' ').toLocaleLowerCase();
  }

  function formValues() {
    const values = {};
    [...form.elements].forEach((element) => {
      if (!element.name) return;
      values[element.name] = element.type === 'checkbox' ? element.checked : element.value;
    });
    return values;
  }

  function saveDraft(immediate = false) {
    const write = () => safeStorageSet(DRAFT_KEY, JSON.stringify({
      savedAt: Date.now(),
      step: Math.min(current, 4),
      values: formValues(),
    }));
    clearTimeout(saveTimer);
    if (immediate) write();
    else saveTimer = setTimeout(write, 250);
  }

  function clearDraft() { safeStorageRemove(DRAFT_KEY); }

  function updateCheckoutConstraint() {
    if (!checkIn?.value || !checkOut) return;
    const next = new Date(`${checkIn.value}T12:00:00`);
    next.setDate(next.getDate() + 1);
    checkOut.min = localDateISO(next);
    if (checkOut.value && checkOut.value <= checkIn.value) checkOut.value = '';
  }

  function restoreDraft() {
    let draft;
    try { draft = JSON.parse(safeStorageGet(DRAFT_KEY) || 'null'); } catch (_) {
      clearDraft();
      return false;
    }
    if (!draft?.savedAt || Date.now() - draft.savedAt > DRAFT_TTL) {
      clearDraft();
      return false;
    }
    Object.entries(draft.values || {}).forEach(([name, value]) => {
      const element = form.elements[name];
      if (!element) return;
      if (element.type === 'checkbox') element.checked = Boolean(value);
      else element.value = value ?? '';
    });
    current = Math.max(1, Math.min(Number(draft.step) || 1, 4));
    updateCheckoutConstraint();
    return true;
  }

  const restored = restoreDraft();
  if (agreementDate && !agreementDate.value) agreementDate.value = iso;

  checkIn?.addEventListener('change', () => {
    updateCheckoutConstraint();
    saveDraft();
  });

  form.elements.first_name?.addEventListener('input', syncLegalName);
  form.elements.last_name?.addEventListener('input', syncLegalName);
  function syncLegalName() {
    const name = `${form.elements.first_name.value} ${form.elements.last_name.value}`.trim();
    if (!form.elements.legal_name.dataset.edited) form.elements.legal_name.value = name;
    saveDraft();
  }
  form.elements.legal_name?.addEventListener('input', () => {
    form.elements.legal_name.dataset.edited = 'true';
    saveDraft();
  });

  form.addEventListener('input', () => saveDraft());
  form.addEventListener('change', () => saveDraft());
  window.addEventListener('pagehide', () => saveDraft(true));

  function setStep(step, { scroll = true, save = true } = {}) {
    current = step;
    panels.forEach((panel) => panel.classList.toggle('active', Number(panel.dataset.bookingStep) === step));
    nav.forEach((button, index) => {
      button.classList.toggle('active', index + 1 === step);
      button.classList.toggle('complete', index + 1 < step);
      if (index + 1 === step) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    });
    if (progress) progress.style.width = `${Math.min(step, 4) * 25}%`;
    if (step === 4) renderReview();
    if (save && step <= 4) saveDraft(true);
    if (scroll) document.querySelector('.booking-shell')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function clearErrors(panel) {
    panel?.querySelectorAll('.invalid').forEach((element) => element.classList.remove('invalid'));
    panel?.querySelectorAll('.field-error').forEach((element) => element.remove());
  }

  function addError(element, message) {
    const field = element.closest('.field');
    field?.classList.add('invalid');
    if (field && !field.querySelector('.field-error')) {
      const error = document.createElement('span');
      error.className = 'field-error';
      error.textContent = message;
      field.append(error);
    }
    return element;
  }

  function validateStep(step) {
    const panel = panels.find((candidate) => Number(candidate.dataset.bookingStep) === step);
    if (!panel) return true;
    clearErrors(panel);
    let firstBad = null;

    [...panel.querySelectorAll('[required]')].forEach((element) => {
      const valid = element.type === 'checkbox' ? element.checked : element.checkValidity();
      if (!valid) {
        const invalidElement = addError(element, 'Please complete this field.');
        firstBad ||= invalidElement;
      }
    });

    if (step === 1) {
      if (checkIn.value && checkOut.value && checkOut.value <= checkIn.value) {
        firstBad ||= addError(checkOut, 'Check-out must be after check-in.');
      }
      const adults = Number(form.elements.adults.value || 0);
      const children = Number(form.elements.children.value || 0);
      if (adults + children > MAX_REQUESTED_GUESTS) {
        firstBad ||= addError(form.elements.children, 'Stay requests are limited to eight guests total.');
      }
    }

    if (step === 2) {
      const digits = String(form.elements.phone.value || '').replace(/\D/g, '');
      if (digits.length < 7) firstBad ||= addError(form.elements.phone, 'Enter a valid mobile phone number.');
    }

    if (step === 3) {
      if (agreementDate.value && agreementDate.value !== iso) {
        firstBad ||= addError(agreementDate, 'Agreement date must be today.');
      }
      if (
        form.elements.electronic_signature.value
        && normalizeName(form.elements.electronic_signature.value) !== normalizeName(form.elements.legal_name.value)
      ) {
        firstBad ||= addError(form.elements.electronic_signature, 'Signature must match the guest legal name.');
      }
    }

    firstBad?.focus();
    return !firstBad;
  }

  function canOpenStep(target) {
    if (target <= current) return true;
    for (let step = 1; step < target; step += 1) {
      if (!validateStep(step)) {
        setStep(step);
        return false;
      }
    }
    return true;
  }

  nav.forEach((button) => button.addEventListener('click', () => {
    const target = Number(button.dataset.stepNav);
    if (target >= 1 && target <= 4 && canOpenStep(target)) setStep(target);
  }));

  form.querySelectorAll('[data-next]').forEach((button) => button.addEventListener('click', () => {
    if (validateStep(current)) setStep(current + 1);
  }));
  form.querySelectorAll('[data-back]').forEach((button) => button.addEventListener('click', () => setStep(Math.max(1, current - 1))));

  function prettyDate(value) {
    if (!value) return '—';
    return new Date(`${value}T12:00:00`).toLocaleDateString(undefined, {
      month: 'long', day: 'numeric', year: 'numeric',
    });
  }

  function reviewItem(key, values) {
    const item = document.createElement('div');
    item.className = 'review-item';
    const label = document.createElement('small');
    label.textContent = key;
    const strong = document.createElement('strong');
    const list = Array.isArray(values) ? values : [values];
    list.forEach((value, index) => {
      if (index) strong.append(document.createElement('br'));
      strong.append(document.createTextNode(String(value ?? '—')));
    });
    item.append(label, strong);
    return item;
  }

  function renderReview() {
    const review = document.querySelector('[data-booking-review]');
    if (!review) return;
    review.replaceChildren(
      reviewItem('Stay', `${prettyDate(checkIn.value)} – ${prettyDate(checkOut.value)}`),
      reviewItem('Guests', `${form.elements.adults.value} adult(s) · ${form.elements.children.value} child(ren)`),
      reviewItem('Primary guest', `${form.elements.first_name.value} ${form.elements.last_name.value}`.trim()),
      reviewItem('Contact', [form.elements.email.value, form.elements.phone.value]),
      reviewItem('Vehicles', form.elements.vehicles.value),
      reviewItem('Electronic signature', form.elements.electronic_signature.value),
    );
  }

  function slugify(value) {
    return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'guest';
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (!validateStep(3)) {
      setStep(3);
      return;
    }
    const data = {};
    [...form.elements].forEach((element) => {
      if (!element.name) return;
      data[element.name] = element.type === 'checkbox' ? element.checked : element.value;
    });
    const random = String(Math.floor(1000 + Math.random() * 9000));
    const slug = `${slugify(`${data.first_name} ${data.last_name}`)}-${random}`;
    data.guestSlug = slug;
    data.submittedAt = new Date().toISOString();
    safeStorageSet(REQUEST_KEY, JSON.stringify(data));
    clearDraft();
    const confirmName = document.querySelector('[data-confirm-name]');
    if (confirmName) confirmName.textContent = data.first_name;
    const guestLink = document.querySelector('[data-guest-link]');
    if (guestLink) {
      const previewUrl = new URL('guest/', document.baseURI);
      previewUrl.searchParams.set('id', slug);
      guestLink.href = previewUrl.href;
      guestLink.textContent = `Open ${data.first_name}'s guest portal preview`;
    }
    setStep(5, { save: false });
  });

  if (restored) {
    const shell = document.querySelector('.booking-shell');
    const notice = document.createElement('div');
    notice.className = 'draft-restored';
    notice.append(document.createTextNode('Your saved booking draft was restored. '));
    const startOver = document.createElement('button');
    startOver.type = 'button';
    startOver.textContent = 'Start over';
    notice.append(startOver);
    shell?.insertBefore(notice, shell.firstChild);
    startOver.addEventListener('click', () => {
      clearDraft();
      form.reset();
      agreementDate.value = iso;
      form.elements.legal_name.dataset.edited = '';
      checkOut.min = iso;
      notice.remove();
      setStep(1, { save: false });
    });
  }

  setStep(current, { scroll: false, save: false });
})();

// Guest portal preview: reads only the request saved in the current browser.
(() => {
  const review = document.querySelector('[data-portal-review]');
  if (!review) return;

  const params = new URLSearchParams(location.search);
  const requested = params.get('id') || 'guest-preview';
  let data = null;
  try { data = JSON.parse(safeStorageGet('arbor-vista-booking-request') || 'null'); } catch (_) { data = null; }

  const set = (selector, value) => {
    const element = document.querySelector(selector);
    if (element) element.textContent = value;
  };
  const pretty = (value) => (value
    ? new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
    : 'Pending');

  set('[data-portal-id]', requested.replace(/-/g, ' '));
  if (!data) {
    set('[data-portal-countdown]', 'pending confirmation');
    const item = document.createElement('div');
    item.className = 'review-item';
    const small = document.createElement('small');
    small.textContent = 'Preview unavailable';
    const strong = document.createElement('strong');
    strong.textContent = 'Please complete the Book Direct form in this browser first.';
    item.append(small, strong);
    review.replaceChildren(item);
    return;
  }

  set('[data-portal-first]', data.first_name || 'Guest');
  set('[data-portal-dates]', `${pretty(data.check_in)} – ${pretty(data.check_out)}`);
  set('[data-portal-guests]', `${data.adults || 0} adult(s) · ${data.children || 0} child(ren)`);
  if (data.check_in) {
    const arrivalDate = new Date(`${data.check_in}T16:00:00`);
    const days = Math.max(0, Math.ceil((arrivalDate - new Date()) / 86400000));
    set('[data-portal-countdown]', days === 0 ? 'today' : `${days} day${days === 1 ? '' : 's'}`);
  }

  const rows = [
    ['Primary guest', `${data.first_name || ''} ${data.last_name || ''}`.trim()],
    ['Stay', `${pretty(data.check_in)} – ${pretty(data.check_out)}`],
    ['Guests', `${data.adults || 0} adult(s) · ${data.children || 0} child(ren)`],
    ['Contact', data.email || '—'],
    ['Vehicles', data.vehicles || '—'],
    ['Status', 'Awaiting host review'],
  ];
  review.replaceChildren(...rows.map(([key, value]) => {
    const item = document.createElement('div');
    item.className = 'review-item';
    const small = document.createElement('small');
    small.textContent = key;
    const strong = document.createElement('strong');
    strong.textContent = value;
    item.append(small, strong);
    return item;
  }));
})();
