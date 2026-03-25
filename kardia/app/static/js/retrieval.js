const API = "http://localhost:8000";

const strategySelect = document.getElementById("strategy");
const topKInput      = document.getElementById("topK");
const queryInput     = document.getElementById("queryInput");
const retrieveBtn    = document.getElementById("retrieveBtn");
const resultsEl      = document.getElementById("results");
const statusPill     = document.getElementById("statusPill");
const resultsMeta    = document.getElementById("resultsMeta");

function setStatus(text, type = "ready") {
  statusPill.textContent = text;
  statusPill.className = "status-pill" + (type !== "ready" ? " " + type : "");
}

async function fetchStrategies() {
  try {
    const res = await fetch(`${API}/retrieval-strategies`);
    if (!res.ok) throw new Error("Failed to fetch strategies");
    const data = await res.json();
    strategySelect.innerHTML = "";
    for (const s of data.strategies) {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s.charAt(0).toUpperCase() + s.slice(1);
      strategySelect.appendChild(opt);
    }
  } catch (e) {
    strategySelect.innerHTML = '<option value="">Error loading strategies</option>';
  }
}

async function retrieve() {
  const query    = queryInput.value.trim();
  const strategy = strategySelect.value;
  const top_k    = parseInt(topKInput.value, 10) || 5;

  if (!query) return;

  try {
    retrieveBtn.disabled = true;
    setStatus("Retrieving\u2026", "loading");
    resultsEl.innerHTML = "";
    resultsMeta.textContent = "";

    const res = await fetch(`${API}/retrieve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, strategy, top_k }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Error retrieving results");
    }

    const data = await res.json();

    if (!data.results || !data.results.length) {
      resultsMeta.textContent = "No results found";
      resultsEl.innerHTML = '<div class="empty-state">No chunks matched your query.</div>';
      setStatus("Ready");
      return;
    }

    resultsMeta.textContent = `${data.results.length} result${data.results.length === 1 ? "" : "s"}`;

    data.results.forEach((chunk, i) => {
      const card = document.createElement("div");
      card.className = "result-card";

      const similarity = chunk.similarity !== undefined
        ? chunk.similarity.toFixed(3)
        : null;

      card.innerHTML = `
        <div class="result-card-header">
          <span class="result-num">Result ${i + 1}</span>
          <div class="result-meta-pills">
            <span class="result-pill">Doc ${chunk.document_id}</span>
            <span class="result-pill">Chunk ${chunk.chunk_id ?? chunk.id}</span>
            ${similarity !== null ? `<span class="result-pill accent">Score ${similarity}</span>` : ""}
            ${chunk.metric ? `<span class="result-pill">Metric: ${escapeHtml(chunk.metric)}</span>` : ""}
          </div>
        </div>
        <div class="result-content">${escapeHtml(chunk.content ?? "")}</div>
      `;

      resultsEl.appendChild(card);
    });

    setStatus("Ready");
  } catch (e) {
    setStatus("Error", "error");
    resultsEl.innerHTML = `<div class="empty-state">${escapeHtml(e.message)}</div>`;
  } finally {
    retrieveBtn.disabled = false;
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

queryInput.addEventListener("input", () => {
  queryInput.style.height = "auto";
  queryInput.style.height = `${Math.min(queryInput.scrollHeight, 160)}px`;
});

queryInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    retrieve();
  }
});

retrieveBtn.addEventListener("click", retrieve);

fetchStrategies();
