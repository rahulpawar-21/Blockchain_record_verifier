const form = document.getElementById('verify-form');
const result = document.getElementById('verify-result');
const input = document.getElementById('certificate-id');
const params = new URLSearchParams(location.search);
if (params.get('certificate')) input.value = params.get('certificate');
const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

async function verify(id) {
  result.innerHTML = '<div class="alert">Verifying certificate against the blockchain...</div>';
  const response = await fetch(`/api/records/${encodeURIComponent(id)}`);
  const data = await response.json();
  if (!response.ok) { result.innerHTML = `<div class="result-card fail"><h3>✕ Verification Failed</h3><p>${escapeHtml(data.error)}</p></div>`; return; }
  const r = data.record;
  const corrections = data.corrections || [];
  const latest = corrections.length ? corrections[corrections.length - 1] : r;
  result.innerHTML = `<div class="result-card ${data.verified ? 'success' : 'fail'}">
    <div class="result-top"><div><span class="eyebrow">${data.verified ? 'Authentic record' : 'Integrity alert'}</span><h3>${data.verified ? '✓ Certificate Verified' : '✕ Verification Failed'}</h3></div><span class="status ${data.verified ? 'valid' : 'invalid'}">${data.blockchain_valid ? 'VALID CHAIN' : 'CHAIN INVALID'}</span></div>
    <dl><dt>Certificate</dt><dd>${escapeHtml(r.certificate_id)}</dd><dt>Student</dt><dd>${escapeHtml(r.student_name)}</dd><dt>SRN</dt><dd>${escapeHtml(r.srn)}</dd><dt>Course</dt><dd>${escapeHtml(r.course)}</dd><dt>Subject</dt><dd>${escapeHtml(r.subject)}</dd><dt>Current marks</dt><dd><strong>${escapeHtml(latest.marks)}</strong>${corrections.length ? ' <span class="badge">Corrected</span>' : ''}</dd><dt>Original block</dt><dd>#${r.block_index}</dd><dt>Block hash</dt><dd class="small-code">${escapeHtml(data.block.hash)}</dd></dl>
    <div class="verify-actions"><a class="secondary-button" href="/verify/qr/${encodeURIComponent(r.certificate_id)}">Generate QR</a><button class="secondary" onclick="navigator.clipboard?.writeText(location.href)">Copy verification link</button></div>
    ${corrections.length ? `<div class="history-note"><strong>Correction history</strong><br>${corrections.map(c => `Block #${c.block_index}: ${escapeHtml(c.previous_marks)} → ${escapeHtml(c.new_marks)} (${escapeHtml(c.reason)})`).join('<br>')}</div>` : ''}
  </div>`;
}
form?.addEventListener('submit', async (event) => { event.preventDefault(); const id = input.value.trim(); if (id) { history.replaceState({}, '', `/verify?certificate=${encodeURIComponent(id)}`); await verify(id); } });
if (input.value.trim()) verify(input.value.trim());
