// Thin client: every action calls an /api endpoint and shows the
// equivalent CLI command returned by the server. No business logic here.

async function loadMeta() {
  const v = await (await fetch('/api/version')).json();
  document.getElementById('version').textContent = v.version;
  const f = await (await fetch('/api/formats')).json();
  document.getElementById('formats').textContent = f.formats.join(' ');
  if (v.auth_required) {
    document.getElementById('auth-card').style.display = '';
    const saved = localStorage.getItem('autodoc_token');
    if (saved) document.getElementById('token').value = saved;
    document.getElementById('token').addEventListener('input', (e) => {
      localStorage.setItem('autodoc_token', e.target.value);
    });
  }
}

function authHeaders() {
  const el = document.getElementById('token');
  const t = el ? el.value.trim() : '';
  return t ? { 'X-Autodoc-Token': t } : {};
}

function fileInput() { return document.getElementById('file'); }

function requireFile() {
  const f = fileInput().files[0];
  if (!f) { alert('请先选择文档'); return null; }
  return f;
}

async function downloadFromResponse(resp, fallbackName) {
  const blob = await resp.blob();
  const cd = resp.headers.get('Content-Disposition') || '';
  let name = fallbackName;
  const m = cd.match(/filename="?([^"]+)"?/);
  if (m) name = m[1];
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = name; document.body.appendChild(a); a.click();
  a.remove(); URL.revokeObjectURL(url);
}

document.getElementById('btn-parse').addEventListener('click', async () => {
  const f = requireFile(); if (!f) return;
  const fd = new FormData(); fd.append('file', f);
  const resp = await fetch('/api/parse', { method: 'POST', body: fd, headers: authHeaders() });
  const data = await resp.json();
  const ul = document.getElementById('questions');
  ul.innerHTML = '';
  (data.questions || []).forEach(q => {
    const li = document.createElement('li');
    li.innerHTML = `<span class="badge">${q.qtype}</span>${q.text}`;
    ul.appendChild(li);
  });
  document.getElementById('cli-parse').textContent = data.equivalent_cli || '';
});

document.getElementById('btn-edit').addEventListener('click', async () => {
  const f = requireFile(); if (!f) return;
  const fd = new FormData();
  fd.append('file', f);
  fd.append('answers', document.getElementById('answers').value);
  const resp = await fetch('/api/edit', { method: 'POST', body: fd, headers: authHeaders() });
  if (!resp.ok) { alert('编辑失败: ' + resp.status); return; }
  document.getElementById('cli-edit').textContent =
    (resp.headers.get('X-Equivalent-Cli') || '') +
    `\n# answers_written=${resp.headers.get('X-Answers-Written')}`;
  await downloadFromResponse(resp, f.name);
});

document.getElementById('btn-answer').addEventListener('click', async () => {
  const f = requireFile(); if (!f) return;
  const fd = new FormData();
  fd.append('file', f);
  fd.append('model', document.getElementById('model').value);
  fd.append('base_url', document.getElementById('base_url').value);
  fd.append('api_key', document.getElementById('api_key').value);
  fd.append('mode', document.getElementById('mode').value);
  const resp = await fetch('/api/answer', { method: 'POST', body: fd, headers: authHeaders() });
  if (!resp.ok) { alert('自动答题失败: ' + resp.status); return; }
  document.getElementById('cli-answer').textContent =
    (resp.headers.get('X-Equivalent-Cli') || '') +
    `\n# mode=${resp.headers.get('X-Mode')} answers_written=${resp.headers.get('X-Answers-Written')}`;
  await downloadFromResponse(resp, f.name);
});

loadMeta();
