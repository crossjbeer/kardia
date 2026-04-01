const API = "http://localhost:8000";
let currentDocId = null;
let allDocs = [];

const docList    = document.getElementById("docList");
const docCount   = document.getElementById("docCount");
const docTitle   = document.getElementById("docTitle");
const docSubtitle = document.getElementById("docSubtitle");
const docContent = document.getElementById("docContent");
const statusPill = document.getElementById("statusPill");

function setStatus(text, type = "ready") {
  statusPill.textContent = text;
  statusPill.className = "status-pill" + (type !== "ready" ? " " + type : "");
}

// ---- Document list ----

async function loadDocuments() {
  try {
    const res = await fetch(API + "/documents");
    allDocs = await res.json();

    docCount.textContent = allDocs.length;
    docList.innerHTML = "";

    if (!allDocs.length) {
      docList.innerHTML = '<div class="empty-state">No documents indexed yet.</div>';
      return;
    }

    allDocs.forEach(doc => {
      const btn = document.createElement("button");
      btn.className = "list-btn";
      btn.dataset.id = doc.id;
      btn.onclick = () => loadDocument(doc.id);
      btn.innerHTML = `
        <span class="doc-name" title="${doc.filename}">${doc.filename}</span>
        <small>${doc.chunk_count} chunk${doc.chunk_count === 1 ? "" : "s"}</small>
      `;
      docList.appendChild(btn);
    });
  } catch (err) {
    console.error(err);
    docList.innerHTML = '<div class="empty-state">Could not load documents.</div>';
  }
}

function setActiveDoc(docId) {
  docList.querySelectorAll(".list-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.id === String(docId));
  });
}

// ---- Document detail ----

async function loadDocument(docId) {
  try {
    setStatus("Loading\u2026", "loading");
    currentDocId = docId;
    setActiveDoc(docId);

    const [docRes, chunksRes] = await Promise.all([
      fetch(`${API}/documents/${docId}`),
      fetch(`${API}/chunks/${docId}`),
    ]);

    const doc    = await docRes.json();
    const chunks = await chunksRes.json();

    docTitle.textContent   = doc.filename;
    docSubtitle.textContent = `Document #${doc.id} \u00b7 ${chunks.length} chunk${chunks.length === 1 ? "" : "s"}`;

    renderDocDetail(doc, chunks);
    setStatus("Ready");
  } catch (err) {
    console.error(err);
    setStatus("Error", "error");
  }
}

function renderDocDetail(doc, chunks) {
  const created = doc.created_at
    ? new Date(doc.created_at).toLocaleString()
    : "\u2014";

  docContent.innerHTML = "";

  // --- Metadata card ---
  const metaCard = document.createElement("div");
  metaCard.className = "meta-card";
  metaCard.innerHTML = `
    <div class="meta-card-header">
      <h3>Document Info</h3>
    </div>

    <div class="meta-static">
      <div class="meta-item">
        <label>Filename</label>
        <div class="meta-value">${doc.filename}</div>
      </div>
      <div class="meta-item">
        <label>Created</label>
        <div class="meta-value">${created}</div>
      </div>
      <div class="meta-item">
        <label>Filepath</label>
        <div class="meta-value dim">${doc.filepath || "\u2014"}</div>
      </div>
      <div class="meta-item">
        <label>File Hash (sha256)</label>
        <div class="meta-value dim" style="font-size:12px;">${doc.file_hash || "\u2014"}</div>
      </div>
    </div>

    <div class="fields-grid">
      <div class="field field-full">
        <label>Description</label>
        <textarea id="f_description" placeholder="Brief description of this document\u2026">${doc.description ?? ""}</textarea>
      </div>
      <div class="field">
        <label>Corpus</label>
        <input id="f_corpus" type="text" placeholder="e.g. lore, house_rule, supplement" value="${doc.corpus ?? ""}">
      </div>
      <div class="field">
        <label>Campaign</label>
        <input id="f_campaign" type="text" placeholder="Campaign or world name" value="${doc.campaign ?? ""}">
      </div>
      <div class="field">
        <label>Game System</label>
        <input id="f_game_system" type="text" placeholder="e.g. dnd5e, pathfinder2e" value="${doc.game_system ?? ""}">
      </div>
      <div class="field">
        <label>Author</label>
        <input id="f_author" type="text" placeholder="Author name" value="${doc.author ?? ""}">
      </div>
      <div class="field field-full">
        <label>Tags</label>
        <input id="f_tags" type="text" placeholder="Comma-separated tags, e.g. combat,magic,underdark" value="${doc.tags ?? ""}">
        <div class="field-hint">Separate tags with commas. Used to filter retrieval.</div>
      </div>
    </div>

    <div class="save-row" style="margin-top:18px;">
      <button class="save-btn" id="saveBtn" onclick="saveDocument()">Save Changes</button>
      <span class="save-feedback" id="saveFeedback"></span>
    </div>
  `;
  docContent.appendChild(metaCard);

  // --- Chunks card ---
  const chunksCard = document.createElement("div");
  chunksCard.className = "chunks-card";

  const chunkHeader = document.createElement("div");
  chunkHeader.className = "chunks-card-header";
  chunkHeader.innerHTML = `
    <h3>Indexed Chunks</h3>
    <span>${chunks.length} chunk${chunks.length === 1 ? "" : "s"}</span>
  `;
  chunksCard.appendChild(chunkHeader);

  const chunkListEl = document.createElement("div");
  chunkListEl.className = "chunk-list";

  if (!chunks.length) {
    chunkListEl.innerHTML = '<div class="empty-state">No chunks found for this document.</div>';
  } else {
    chunks.forEach((c, i) => {
      const item = document.createElement("div");
      item.className = "chunk-item";
      item.innerHTML = `
        <div class="chunk-item-header">
          <span class="chunk-num">Chunk ${i + 1}</span>
          ${c.start_index != null
            ? `<span class="chunk-range">chars ${c.start_index}\u2013${c.end_index}</span>`
            : ""}
        </div>
        <div class="chunk-text">${escapeHtml(c.content)}</div>
      `;
      chunkListEl.appendChild(item);
    });
  }

  chunksCard.appendChild(chunkListEl);
  docContent.appendChild(chunksCard);
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function saveDocument() {
  if (currentDocId === null) return;
  const saveBtn      = document.getElementById("saveBtn");
  const saveFeedback = document.getElementById("saveFeedback");

  const payload = {
    description: document.getElementById("f_description").value || null,
    corpus:      document.getElementById("f_corpus").value      || null,
    campaign:    document.getElementById("f_campaign").value    || null,
    game_system: document.getElementById("f_game_system").value || null,
    author:      document.getElementById("f_author").value      || null,
    tags:        document.getElementById("f_tags").value        || null,
  };

  try {
    saveBtn.disabled = true;
    setStatus("Saving\u2026", "loading");
    saveFeedback.className = "save-feedback";
    saveFeedback.textContent = "";

    const res = await fetch(`${API}/documents/${currentDocId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Save failed");
    }

    saveFeedback.textContent = "Saved!";
    saveFeedback.className = "save-feedback visible";
    setStatus("Ready");

    // Refresh sidebar to pick up any changes
    await loadDocuments();
    setActiveDoc(currentDocId);

    setTimeout(() => {
      saveFeedback.className = "save-feedback";
    }, 2500);
  } catch (err) {
    console.error(err);
    saveFeedback.textContent = "Save failed: " + err.message;
    saveFeedback.className = "save-feedback visible err";
    setStatus("Error", "error");
  } finally {
    saveBtn.disabled = false;
  }
}

// ---- Init ----
loadDocuments();

// ---- Lore Seed ----

async function openLoreSeed() {
  try {
    setStatus("Loading\u2026", "loading");
    currentDocId = null;
    setActiveDoc(null);

    const res = await fetch(`${API}/lore-seed`);
    if (!res.ok) throw new Error("Failed to load lore seed");
    const data = await res.json();

    docTitle.textContent = "Lore Seed";
    docSubtitle.textContent = "Edit the lore seed prompt used to ground the AI agent.";
    renderLoreSeedEditor(data.content);
    setStatus("Ready");
  } catch (err) {
    console.error(err);
    setStatus("Error", "error");
  }
}

function renderLoreSeedEditor(content) {
  docContent.innerHTML = "";

  const card = document.createElement("div");
  card.className = "meta-card";
  card.innerHTML = `
    <div class="meta-card-header">
      <h3>Lore Seed</h3>
    </div>
    <p style="font-size:13px; color:var(--muted); margin:0 0 16px;">
      This prompt grounds the AI agent with campaign and world information.
      Changes are written directly to <code style="background:rgba(255,255,255,0.08);padding:1px 5px;border-radius:5px;">prompts/lore-seed.md</code>.
    </p>
    <div class="field" style="grid-column:1/-1;">
      <label>Lore Content</label>
      <textarea id="loreSeedText" style="min-height:440px; resize:vertical; font-family:monospace; font-size:13px; line-height:1.6;">${escapeHtml(content)}</textarea>
    </div>
    <div class="save-row" style="margin-top:18px;">
      <button class="save-btn" id="loreSeedSaveBtn" onclick="saveLoreSeed()">Save Lore Seed</button>
      <span class="save-feedback" id="loreSeedFeedback"></span>
    </div>
  `;
  docContent.appendChild(card);
}

async function saveLoreSeed() {
  const saveBtn = document.getElementById("loreSeedSaveBtn");
  const feedback = document.getElementById("loreSeedFeedback");
  const content = document.getElementById("loreSeedText").value;

  try {
    saveBtn.disabled = true;
    setStatus("Saving\u2026", "loading");
    feedback.className = "save-feedback";
    feedback.textContent = "";

    const res = await fetch(`${API}/lore-seed`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Save failed");
    }

    feedback.textContent = "Saved!";
    feedback.className = "save-feedback visible";
    setStatus("Ready");

    setTimeout(() => {
      feedback.className = "save-feedback";
    }, 2500);
  } catch (err) {
    console.error(err);
    feedback.textContent = "Save failed: " + err.message;
    feedback.className = "save-feedback visible err";
    setStatus("Error", "error");
  } finally {
    saveBtn.disabled = false;
  }
}
