const form = document.getElementById("match-form");
const statusNode = document.getElementById("match-status");
const resultsNode = document.getElementById("match-results");
const hybridFields = document.getElementById("hybrid-fields");
const dialog = document.getElementById("job-dialog");
const dialogBody = document.getElementById("job-dialog-body");

function selectedMode() {
  const chosen = form.querySelector("input[name='mode']:checked");
  return chosen ? chosen.value : "tfidf";
}

function toggleMode() {
  hybridFields.hidden = selectedMode() !== "hybrid";
}

Array.from(form.querySelectorAll("input[name='mode']")).forEach((input) => {
  input.addEventListener("change", toggleMode);
});
toggleMode();

function tags(items, className) {
  if (!items || !items.length) return "<span class='meta'>None</span>";
  return `<div class="tags">${items.map((item) => `<span class="tag ${className || ""}">${escapeHtml(item)}</span>`).join("")}</div>`;
}

function componentRow(label, value, used) {
  if (!used) {
    return `<div class="bar-row"><span>${escapeHtml(label)}</span><span class="meta">N/A</span><span>N/A</span></div>`;
  }
  const width = Math.max(0, Math.min(100, Number(value) * 100));
  return `<div class="bar-row">
    <span>${escapeHtml(label)}</span>
    <div class="bar" aria-hidden="true"><span style="width:${width}%"></span></div>
    <span>${Number(value).toFixed(2)}</span>
  </div>`;
}

function renderTfidf(jobs, limit) {
  const sliced = jobs.slice(0, limit);
  if (!sliced.length) {
    setStatus(statusNode, "empty", "No matches returned.");
    resultsNode.innerHTML = "";
    return;
  }
  clearStatus(statusNode);
  resultsNode.innerHTML = sliced.map((job) => `
    <article class="job-card">
      <h3>${escapeHtml(job.title || "Untitled")}</h3>
      <p class="meta">${escapeHtml(job.company || "Unknown company")} · ${escapeHtml(job.location || "Unknown location")}</p>
      <p class="score">Match score ${Number(job.hybrid_score).toFixed(3)}</p>
      <p class="meta">Ranking method: Pairwise TF-IDF baseline</p>
      <div class="bars">
        ${componentRow("TF-IDF cosine", job.match_score, true)}
        ${componentRow("Skills", job.skill_score, true)}
      </div>
      <p><strong>Matched skills</strong></p>
      ${tags(job.matched_skills)}
      <p><strong>Missing skills</strong></p>
      ${tags(job.missing_skills, "warn")}
      <button type="button" class="secondary" data-job-id="${job.id}">View job</button>
    </article>
  `).join("");
}

function renderHybrid(payload) {
  const results = payload.results || [];
  if (!results.length) {
    setStatus(statusNode, "empty", "No matches returned.");
    resultsNode.innerHTML = "";
    return;
  }
  clearStatus(statusNode);
  const weights = payload.weights || {};
  const similarityLabel = payload.embedding_kind === "semantic"
    ? "Semantic similarity"
    : "Lexical similarity";
  const method = payload.ranking_label || "Lexical vector + structured hybrid";
  const gapCounts = {};
  results.forEach((job) => {
    (job.missing_skills || []).forEach((skill) => {
      gapCounts[skill] = (gapCounts[skill] || 0) + 1;
    });
  });
  const topGaps = Object.entries(gapCounts).sort((a, b) => b[1] - a[1]).slice(0, 6);
  const gapHtml = topGaps.length
    ? `<section class="panel"><h2>Gaps in these top matches</h2>
        <p class="meta">Count of current results that list the skill as missing. This is not a market-wide trend.</p>
        <ul>${topGaps.map(([skill, count]) => `<li>${escapeHtml(skill)} — ${count}</li>`).join("")}</ul>
      </section>`
    : "";
  resultsNode.innerHTML = `${gapHtml}${results.map((job) => `
    <article class="job-card">
      <h3>${escapeHtml(job.title || "Untitled")}</h3>
      <p class="meta">${escapeHtml(job.company || "Unknown company")} · ${escapeHtml(job.location || "Unknown location")}</p>
      <p class="score">Match score ${Number(job.hybrid_score).toFixed(3)}</p>
      <p class="meta">Ranking method: ${escapeHtml(method)}</p>
      <div class="bars">
        ${componentRow(similarityLabel, job.components.semantic, (weights.semantic || 0) > 0)}
        ${componentRow("Skills", job.components.skills, (weights.skill || 0) > 0)}
        ${componentRow("Recency", job.components.recency, (weights.recency || 0) > 0)}
        ${componentRow("Experience", job.components.experience, (weights.experience || 0) > 0)}
        ${componentRow("Location", job.components.location, (weights.location || 0) > 0)}
      </div>
      <p><strong>Matched skills</strong></p>
      ${tags(job.matched_skills)}
      <p><strong>Missing skills</strong></p>
      ${tags(job.missing_skills, "warn")}
      <details class="details">
        <summary>Weights used for this ranking</summary>
        <p class="meta">Unused preferences are dropped and remaining weights are renormalized. The overall score is not a hiring probability.</p>
        <ul>
          <li>Similarity ${Number(weights.semantic || 0).toFixed(2)}</li>
          <li>Skills ${Number(weights.skill || 0).toFixed(2)}</li>
          <li>Experience ${Number(weights.experience || 0).toFixed(2)}</li>
          <li>Recency ${Number(weights.recency || 0).toFixed(2)}</li>
          <li>Location ${Number(weights.location || 0).toFixed(2)}</li>
        </ul>
      </details>
      <button type="button" class="secondary" data-job-id="${job.job_id}">View job</button>
    </article>
  `).join("")}`;
}

async function openJob(jobId) {
  dialogBody.innerHTML = "<p>Loading job…</p>";
  dialog.showModal();
  try {
    const job = await apiGet(`/jobs/${jobId}`);
    const salary = [job.salary_min, job.salary_max].filter((v) => v !== null && v !== undefined);
    const salaryText = salary.length
      ? `${salary.join("–")}${job.salary_currency ? ` ${job.salary_currency}` : ""}`
      : "Not provided";
    dialogBody.innerHTML = `
      <h2>${escapeHtml(job.title || "Untitled")}</h2>
      <p><strong>Company:</strong> ${escapeHtml(job.company || "—")}</p>
      <p><strong>Location:</strong> ${escapeHtml(job.location || "—")}</p>
      <p><strong>Employment type:</strong> ${escapeHtml(job.employment_type || "—")}</p>
      <p><strong>Experience level:</strong> ${escapeHtml(job.experience_level || "—")}</p>
      <p><strong>Salary:</strong> ${escapeHtml(salaryText)}</p>
      <p><strong>Posted:</strong> ${escapeHtml(formatWhen(job.posted_at))}</p>
      <p><strong>Source:</strong> ${escapeHtml(job.source || "—")}</p>
      ${job.source_url ? `<p><a href="${escapeHtml(job.source_url)}" rel="noopener noreferrer">Source link</a></p>` : ""}
      <p><strong>Canonical skills</strong></p>
      ${tags((job.skills || []).map((item) => item.name || item))}
      <p><strong>Description</strong></p>
      <div class="job-desc">${escapeHtml(job.description || "—")}</div>
    `;
  } catch (error) {
    dialogBody.innerHTML = `<p class="status error">${escapeHtml(error.message || "Could not load job.")}</p>`;
  }
}

resultsNode.addEventListener("click", (event) => {
  const button = event.target.closest("[data-job-id]");
  if (!button) return;
  openJob(button.getAttribute("data-job-id"));
});

document.getElementById("close-dialog").addEventListener("click", () => dialog.close());

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = form.elements.namedItem("resume").files[0];
  if (!file) {
    setStatus(statusNode, "error", "Choose a PDF résumé first.");
    return;
  }
  const limit = Number(form.elements.namedItem("limit").value || 20);
  const body = new FormData();
  body.append("file", file);
  setStatus(statusNode, "info", "Matching résumé…");
  resultsNode.innerHTML = "";
  try {
    if (selectedMode() === "tfidf") {
      const payload = await apiUpload("/upload-resume", body);
      renderTfidf(payload.jobs || [], limit);
    } else {
      const location = form.elements.namedItem("preferred_location").value;
      const experience = form.elements.namedItem("preferred_experience").value;
      if (location.trim()) body.append("preferred_location", location.trim());
      if (experience) body.append("preferred_experience", experience);
      body.append("limit", String(limit));
      const payload = await apiUpload("/api/v1/matches/upload", body);
      renderHybrid(payload);
    }
  } catch (error) {
    const message = error.status === 503
      ? "Database is unavailable, so jobs cannot be ranked."
      : error.message || "Matching failed.";
    setStatus(statusNode, "error", message);
  }
});
