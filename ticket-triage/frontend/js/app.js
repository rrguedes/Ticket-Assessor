/**
 * Ticket Triage — frontend application
 * Plain vanilla JS, no build step required.
 */

const API_BASE = '/api/tickets';

// ── Element references ────────────────────────────────────────────────────────
const form        = document.getElementById('evaluate-form');
const ticketInput = document.getElementById('ticket-id');
const submitBtn   = document.getElementById('submit-btn');
const btnLabel    = document.getElementById('btn-label');
const btnSpinner  = document.getElementById('btn-spinner');
const errorMsg    = document.getElementById('error-msg');

const resultCard  = document.getElementById('result-card');
const scoreCircle = document.getElementById('score-circle');
const scoreRing   = document.getElementById('score-ring');
const scoreValue  = document.getElementById('score-value');

const resultType     = document.getElementById('result-type');
const resultTitle    = document.getElementById('result-title');
const resultId       = document.getElementById('result-id');
const resultState    = document.getElementById('result-state');
const resultFeedback = document.getElementById('result-feedback');

const strengthsSection = document.getElementById('strengths-section');
const strengthsList    = document.getElementById('strengths-list');
const questionsSection = document.getElementById('questions-section');
const questionsList    = document.getElementById('questions-list');

const historyList    = document.getElementById('history-list');
const historyLoading = document.getElementById('history-loading');
const historyTotal   = document.getElementById('history-total');
const refreshBtn     = document.getElementById('refresh-history-btn');

// ── Helpers ───────────────────────────────────────────────────────────────────
function scoreClass(score) {
  if (score >= 8) return 'success';
  if (score >= 5) return 'warn';
  return 'danger';
}

function renderScoreCircle(score) {
  const circumference = 2 * Math.PI * 34; // r=34
  const filled = (score / 10) * circumference;
  const offset = circumference - filled;

  scoreRing.style.strokeDashoffset = offset;
  scoreValue.textContent = score.toFixed(1);

  const cls = scoreClass(score);
  scoreCircle.className = `score-circle score-circle--${cls}`;
}

function setLoading(loading) {
  submitBtn.disabled = loading;
  btnLabel.textContent = loading ? 'Analisando…' : 'Analisar Ticket';
  btnSpinner.classList.toggle('hidden', !loading);
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.classList.remove('hidden');
}

function clearError() {
  errorMsg.textContent = '';
  errorMsg.classList.add('hidden');
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

// ── Render result ─────────────────────────────────────────────────────────────
function renderResult(data) {
  resultType.textContent  = data.ticket_type || 'Ticket';
  resultTitle.textContent = data.ticket_title || `#${data.ticket_id}`;
  resultId.textContent    = `#${data.ticket_id}`;
  resultState.textContent = data.ticket_state || '—';
  resultFeedback.textContent = data.feedback;

  renderScoreCircle(data.score);

  // Strengths
  strengthsList.innerHTML = '';
  if (data.strengths && data.strengths.length) {
    data.strengths.forEach(s => {
      const li = document.createElement('li');
      li.textContent = s;
      strengthsList.appendChild(li);
    });
    strengthsSection.classList.remove('hidden');
  } else {
    strengthsSection.classList.add('hidden');
  }

  // Additional questions (only when score < 8)
  questionsList.innerHTML = '';
  if (data.additional_questions && data.additional_questions.length && data.score < 8) {
    data.additional_questions.forEach(q => {
      const li = document.createElement('li');
      li.textContent = q;
      questionsList.appendChild(li);
    });
    questionsSection.classList.remove('hidden');
  } else {
    questionsSection.classList.add('hidden');
  }

  resultCard.classList.remove('hidden');
  resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Render history ────────────────────────────────────────────────────────────
function renderHistory(evaluations, total) {
  historyList.innerHTML = '';

  if (!evaluations.length) {
    const li = document.createElement('li');
    li.className = 'history-list__empty';
    li.textContent = 'Nenhuma avaliação ainda.';
    historyList.appendChild(li);
    historyTotal.classList.add('hidden');
    return;
  }

  evaluations.forEach(ev => {
    const cls = scoreClass(ev.score);
    const li = document.createElement('li');
    li.className = 'history-item';
    li.innerHTML = `
      <div class="history-item__badge history-item__badge--${cls}">${ev.score.toFixed(1)}</div>
      <div class="history-item__info">
        <div class="history-item__title" title="${ev.ticket_title || ''}">
          #${ev.ticket_id} — ${ev.ticket_title || '(sem título)'}
        </div>
        <div class="history-item__meta">${formatDate(ev.evaluated_at)}</div>
      </div>
    `;
    li.addEventListener('click', () => renderResult(ev));
    historyList.appendChild(li);
  });

  if (total > evaluations.length) {
    historyTotal.textContent = `Exibindo ${evaluations.length} de ${total} avaliações.`;
    historyTotal.classList.remove('hidden');
  } else {
    historyTotal.classList.add('hidden');
  }
}

// ── Load history ──────────────────────────────────────────────────────────────
async function loadHistory() {
  historyLoading.classList.remove('hidden');
  try {
    const res = await fetch(`${API_BASE}/evaluations?limit=20&offset=0`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderHistory(data.evaluations, data.total);
  } catch (err) {
    console.error('Error loading history:', err);
    historyList.innerHTML = '<li class="history-list__empty">Erro ao carregar histórico.</li>';
  } finally {
    historyLoading.classList.add('hidden');
  }
}

// ── Form submit ───────────────────────────────────────────────────────────────
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearError();

  const ticketId = ticketInput.value.trim();
  if (!ticketId) {
    showError('Por favor, informe o número do ticket.');
    return;
  }
  if (!/^\d+$/.test(ticketId)) {
    showError('O número do ticket deve conter apenas dígitos.');
    return;
  }

  setLoading(true);
  try {
    const res = await fetch(`${API_BASE}/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticket_id: ticketId }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = err.detail || `Erro ${res.status}`;
      if (res.status === 404) {
        showError(`Ticket #${ticketId} não encontrado no Azure DevOps.`);
      } else {
        showError(detail);
      }
      return;
    }

    const data = await res.json();
    renderResult(data);
    await loadHistory();
  } catch (err) {
    showError('Não foi possível conectar ao servidor. Tente novamente.');
    console.error(err);
  } finally {
    setLoading(false);
  }
});

// ── Refresh history button ────────────────────────────────────────────────────
refreshBtn.addEventListener('click', loadHistory);

// ── Initial load ──────────────────────────────────────────────────────────────
loadHistory();
