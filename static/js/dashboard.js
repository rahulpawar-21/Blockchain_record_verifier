const recordForm = document.getElementById('record-form');
const formMessage = document.getElementById('form-message');
const tamperButton = document.getElementById('tamper-btn');
const resetButton = document.getElementById('reset-btn');
const correctionForm = document.getElementById('correction-form');

const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

recordForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(recordForm).entries());
  payload.marks = Number(payload.marks);
  formMessage.innerHTML = '<div class="alert">Creating a sealed block...</div>';
  const response = await fetch('/api/records', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
  const data = await response.json();
  if (response.ok) {
    formMessage.innerHTML = `<div class="alert success-alert">✓ Block #${data.block.index} created. Hash: <span class="small-code">${escapeHtml(data.block.hash)}</span></div>`;
    setTimeout(() => location.reload(), 1000);
  } else formMessage.innerHTML = `<div class="alert danger">${escapeHtml(data.error || 'Could not create record.')}</div>`;
});

tamperButton?.addEventListener('click', async () => {
  if (!confirm('This intentionally breaks the blockchain for the demonstration. Continue?')) return;
  const blockIndex = Number(document.getElementById('tamper-block').value);
  const marks = Number(document.getElementById('tamper-marks').value);
  const output = document.getElementById('tamper-message');
  output.innerHTML = '<div class="alert">Running attack simulation...</div>';
  const response = await fetch('/api/tamper', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({block_index:blockIndex, field:'marks', value:marks})});
  const data = await response.json();
  if (!response.ok) { output.innerHTML = `<div class="alert danger">${escapeHtml(data.error)}</div>`; return; }
  output.innerHTML = `<div class="alert danger"><strong>✕ TAMPERING DETECTED</strong><br>Blockchain valid: ${data.valid}<br>${data.errors.map(e => escapeHtml(e.message)).join('<br>')}</div>`;
  setTimeout(() => location.reload(), 2200);
});

resetButton?.addEventListener('click', async () => {
  const response = await fetch('/api/reset-demo', {method:'POST'});
  const data = await response.json();
  if (data.success) location.reload();
});

correctionForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(correctionForm).entries());
  const output = document.getElementById('correction-message');
  output.innerHTML = '<div class="alert">Recording correction as a new block...</div>';
  const response = await fetch(`/api/records/${encodeURIComponent(data.certificate_id)}/correct`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({marks:Number(data.marks), reason:data.reason})});
  const result = await response.json();
  if (!response.ok) { output.innerHTML = `<div class="alert danger">${escapeHtml(result.error || 'Correction failed.')}</div>`; return; }
  output.innerHTML = `<div class="alert success-alert">✓ Correction stored in Block #${result.block.index}. The historical block was not edited.</div>`;
  setTimeout(() => location.reload(), 1200);
});
