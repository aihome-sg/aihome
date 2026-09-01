const money = (value) => new Intl.NumberFormat('en-SG', { style: 'currency', currency: 'SGD', maximumFractionDigits: 0 }).format(value);

const calculator = document.querySelector('#calculator-form');
calculator.addEventListener('submit', async (event) => {
  event.preventDefault();
  const response = await fetch('/api/estimate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.fromEntries(new FormData(calculator))) });
  const data = await response.json();
  if (response.ok) document.querySelector('#savings').textContent = money(data.savings);
});

const leadForm = document.querySelector('#lead-form');
leadForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const status = leadForm.querySelector('.form-status');
  status.textContent = 'Sending your request...';
  const response = await fetch('/api/lead', { method: 'POST', body: new FormData(leadForm) });
  const data = await response.json();
  status.textContent = response.ok ? data.message : data.error;
  if (response.ok) leadForm.reset();
});

document.querySelectorAll('a[href^="#"]').forEach((link) => link.addEventListener('click', (event) => {
  const target = document.querySelector(link.getAttribute('href'));
  if (target) { event.preventDefault(); target.scrollIntoView({ behavior: 'smooth' }); }
}));
