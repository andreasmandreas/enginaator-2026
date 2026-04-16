const showSuccessToast = (isEdit = false) => {
  const existingToast = document.querySelector('.toast');
  if (existingToast) existingToast.remove();

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');
  const action = isEdit ? 'edited' : 'created';
  toast.innerHTML = `
    <svg class="toast-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M9.2 16.2L4.8 11.8l1.4-1.4 3 3 8-8 1.4 1.4-9.4 9.4z"></path>
    </svg>
    <span>${action}</span>
  `;

  document.body.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('is-visible'));

  setTimeout(() => {
    toast.classList.remove('is-visible');
    setTimeout(() => {
      toast.remove();
      window.location.href = ``; // CHANGE THIS LATER to where the dashboard
    }, 400);
  }, 2400);
};

const showFailureToast = (message = 'Failed.') => {
  const existingToast = document.querySelector('.toast');
  if (existingToast) existingToast.remove();

  const toast = document.createElement('div');
  toast.className = 'toast toast-failure';
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');
  toast.innerHTML = `
    <svg class="toast-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"></path>
    </svg>
    <span>${message}</span>
  `;
}