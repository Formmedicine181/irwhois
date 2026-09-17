let RESULTS = [];

function badgeCls(s) {
  return s === 'free' ? 'free' : (s === 'taken' ? 'taken' : (s === 'reserved' ? 'res' : 'err'));
}

function setSingleLoading() {
  document.getElementById('singleRes').innerHTML = '<div class="result-box">⏳ در حال استعلام از whois.nic.ir ...</div>';
}

async function checkSingle() {
  const v = document.getElementById('single').value.trim();
  if (!v) {
    alert('دامنه را وارد کنید');
    return;
  }
  setSingleLoading();

  try {
    const resp = await fetch('/api/check?domain=' + encodeURIComponent(v));
    const r = await resp.json();

    if (!resp.ok) {
      document.getElementById('singleRes').innerHTML = '<div class="result-box">❌ ' + (r.error || ('خطای سرور (' + resp.status + ')')) + '</div>';
      return;
    }

    if (r.error && !r.domain) {
      document.getElementById('singleRes').innerHTML = '<div class="result-box">❌ ' + r.error + '</div>';
      return;
    }

    const cls = badgeCls(r.status);
    let html = '<div class="result-box"><table><tr>' +
      '<td><b>' + (r.domain || '') + '</b></td>' +
      '<td><span class="badge ' + cls + '">' + (r.label_fa || r.status) + '</span></td>' +
      '<td><a target="_blank" href="' + (r.whois_url || '#') + '">مشاهده در whois.nic.ir ↗</a></td>' +
      '</tr></table>';

    if (r.error && r.status !== 'free' && r.status !== 'taken') {
      html += '<div class="hint">⚠️ ' + r.error + '</div>';
    }
    html += '</div>';

    document.getElementById('singleRes').innerHTML = html;
  } catch (e) {
    document.getElementById('singleRes').innerHTML = '<div class="result-box">❌ ارتباط با سرور محلی قطع شد؛ مطمئن شوید ترمینال باز است و اسکریپت با --web در حال اجراست.</div>';
  }
}

document.getElementById('single').addEventListener('keydown', function (e) {
  if (e.key === 'Enter') checkSingle();
});

function parseInput() {
  return document.getElementById('batch').value
    .split(/[\n,;|]+/)
    .map(s => s.trim())
    .filter(Boolean);
}

async function checkBatch() {
  const domains = parseInput();
  if (!domains.length) {
    alert('حداقل یک دامنه وارد کنید');
    return;
  }

  RESULTS = [];
  render();
  document.getElementById('prog').style.width = '8%';

  const btns = document.querySelectorAll('button');
  btns.forEach(b => b.disabled = true);

  try {
    const resp = await fetch('/api/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ domains })
    });
    const res = await resp.json();

    if (!resp.ok) {
      alert('❌ ' + (res.error || ('خطای سرور (' + resp.status + ')')));
      btns.forEach(b => b.disabled = false);
      return;
    }

    RESULTS = res.results || [];
  } catch (e) {
    alert('❌ ارتباط با سرور محلی قطع شد؛ مطمئن شوید ترمینال باز است و اسکریپت با --web در حال اجراست.');
    btns.forEach(b => b.disabled = false);
    return;
  }

  btns.forEach(b => b.disabled = false);
  document.getElementById('prog').style.width = '100%';
  render();
}

function stats() {
  const total = RESULTS.length;
  const free = RESULTS.filter(r => r.status === 'free').length;
  const taken = RESULTS.filter(r => r.status === 'taken').length;
  const reserved = RESULTS.filter(r => r.status === 'reserved').length;
  const err = total - free - taken - reserved;

  document.getElementById('sTotal').textContent = total;
  document.getElementById('sFree').textContent = free;
  document.getElementById('sTaken').textContent = taken;
  document.getElementById('sErr').textContent = err;

  if (total) document.getElementById('prog').style.width = '100%';
}

function render() {
  stats();
  const q = document.getElementById('filter').value.trim().toLowerCase();
  const sf = document.getElementById('statusFilter').value;
  const tb = document.getElementById('tbody');

  const rows = RESULTS.filter(r => {
    if (sf === 'error' && ['free', 'taken', 'reserved'].includes(r.status)) return false;
    if (sf && sf !== 'error' && r.status !== sf) return false;
    if (q && !(r.domain || '').toLowerCase().includes(q)) return false;
    return true;
  });

  document.getElementById('tbl').style.display = RESULTS.length ? '' : 'none';

  tb.innerHTML = rows.map((r, i) => {
    const cls = badgeCls(r.status);
    return '<tr>' +
      '<td>' + (i + 1) + '</td>' +
      '<td class="domain-cell">' + (r.domain || '') + '</td>' +
      '<td><span class="badge ' + cls + '">' + (r.label_fa || r.status) + '</span></td>' +
      '<td><a target="_blank" href="' + (r.whois_url || '#') + '">whois ↗</a></td>' +
      '</tr>';
  }).join('');
}

function clearAll() {
  document.getElementById('batch').value = '';
  RESULTS = [];
  render();
  document.getElementById('prog').style.width = '0';
}

function downloadCSV() {
  if (!RESULTS.length) {
    alert('نتیجه‌ای برای خروجی وجود ندارد');
    return;
  }

  const rows = [['domain', 'status', 'label_fa', 'whois_url']].concat(
    RESULTS.map(r => [r.domain, r.status, r.label_fa, r.whois_url])
  );

  const csv = rows.map(r => r.map(c => '"' + String(c || '').replace(/"/g, '""') + '"').join(',')).join('\n');
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'ir-domains.csv';
  a.click();
}

function copyFree() {
  const freeDomains = RESULTS.filter(r => r.status === 'free').map(r => r.domain).join('\n');
  if (!freeDomains) {
    alert('دامنه‌ای در وضعیت آزاد وجود ندارد');
    return;
  }
  navigator.clipboard.writeText(freeDomains).then(() => alert('دامنه‌های آزاد کپی شد ✅'));
}

function loadFile(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function () {
    document.getElementById('batch').value += ('\n' + reader.result);
    alert('فایل خوانده شد؛ حالا روی «بررسی همه» کلیک کنید');
  };
  reader.readAsText(file);
}
