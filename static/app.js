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

const chatLauncher = document.querySelector('#chat-launcher');
const chatPanel = document.querySelector('#chat-panel');
const chatClose = document.querySelector('#chat-close');
const chatMessages = document.querySelector('#chat-messages');
const chatForm = document.querySelector('#chat-form');
const chatOptions = document.querySelector('#chat-options');
const chatInputRow = document.querySelector('#chat-input-row');
const chatInput = document.querySelector('#chat-input');
const booking = {};
let chatStep = 0;

const addMessage = (text, sender = 'assistant') => {
  const message = document.createElement('div');
  message.className = `chat-message ${sender}`;
  message.innerHTML = sender === 'assistant' ? `<span class="message-avatar">M</span><p>${text}</p>` : `<p>${text}</p>`;
  chatMessages.appendChild(message);
  chatMessages.scrollTop = chatMessages.scrollHeight;
};

const setQuestion = (question, options = false, placeholder = 'Type your answer...') => {
  addMessage(question);
  chatOptions.hidden = !options;
  chatInputRow.hidden = options;
  chatInput.placeholder = placeholder;
  if (!options) chatInput.focus();
};

const finishBooking = async () => {
  addMessage('Thanks. I’m sending your request to the Homewise team now...');
  const formData = new FormData();
  Object.entries(booking).forEach(([key, value]) => formData.append(key, value));
  const response = await fetch('/api/lead', { method: 'POST', body: formData });
  const data = await response.json();
  addMessage(response.ok ? `You’re all set. ${data.message} We’ll see you on ${booking.booking_date} at ${booking.booking_time}.` : data.error);
  chatInputRow.hidden = true;
};

const handleChatAnswer = (answer) => {
  const cleanAnswer = answer.trim();
  if (!cleanAnswer) return;
  addMessage(cleanAnswer, 'user');
  chatInput.value = '';
  if (chatStep === 0) { booking.property_type = cleanAnswer; chatStep += 1; setQuestion('Great choice. What day works best for your call?', false, 'e.g. 18 Sep 2026'); return; }
  if (chatStep === 1) { booking.booking_date = cleanAnswer; chatStep += 1; setQuestion('And what time should we aim for?', false, 'e.g. 3:00 PM'); return; }
  if (chatStep === 2) { booking.booking_time = cleanAnswer; chatStep += 1; setQuestion('What’s your name?', false, 'Your full name'); return; }
  if (chatStep === 3) { booking.name = cleanAnswer; chatStep += 1; setQuestion('What’s the best mobile number for confirmation?', false, '+65 8123 4567'); return; }
  if (chatStep === 4) { booking.phone = cleanAnswer; chatStep += 1; setQuestion('Where should we send the booking details?', false, 'you@example.com'); return; }
  booking.email = cleanAnswer;
  finishBooking().catch(() => addMessage('Something went wrong sending that through. Please use the booking form below and we’ll take care of it.'));
};

chatLauncher.addEventListener('click', () => { const open = chatPanel.hidden; chatPanel.hidden = !open; chatLauncher.setAttribute('aria-expanded', String(open)); if (open) chatInput.focus(); });
chatClose.addEventListener('click', () => { chatPanel.hidden = true; chatLauncher.setAttribute('aria-expanded', 'false'); });
chatOptions.addEventListener('click', (event) => { if (event.target.matches('button')) { chatOptions.hidden = true; handleChatAnswer(event.target.dataset.value); } });
chatForm.addEventListener('submit', (event) => { event.preventDefault(); handleChatAnswer(chatInput.value); });
