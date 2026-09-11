const filtersForm = document.getElementById("filters");
const statusNode = document.getElementById("market-status");
const overviewNode = document.getElementById("overview");
const skillsBody = document.getElementById("skills-body");
const categoriesBody = document.getElementById("categories-body");
const experienceBody = document.getElementById("experience-body");
const locationsBody = document.getElementById("locations-body");
const companiesBody = document.getElementById("companies-body");
const freshnessBody = document.getElementById("freshness-body");

const charts = {};

function filters() {
  const data = new FormData(filtersForm);
  return {
    title: data.get("title"),
    location: data.get("location"),
    experience: data.get("experience"),
    limit: data.get("limit") || "15",
  };
}

function renderOverview(data) {
  const cards = [
    ["Active jobs", formatNumber(data.active_jobs)],
    ["Jobs with skill data", formatNumber(data.jobs_with_skills)],
    ["Canonical skills", formatNumber(data.canonical_skills)],
    ["Most demanded skill", data.top_skill ? data.top_skill.skill : "—"],
    ["Latest ingestion", formatWhen(data.latest_ingestion_at)],
    ["Latest job seen", formatWhen(data.latest_job_seen_at)],
  ];
  overviewNode.innerHTML = cards.map(([k, v]) => (
    `<article class="card"><div class="k">${escapeHtml(k)}</div><div class="v">${escapeHtml(v)}</div></article>`
  )).join("");
}

function renderRows(body, rows, cells) {
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="${cells}">No rows for the current filters.</td></tr>`;
    return;
  }
  body.innerHTML = rows.join("");
}

function barChart(id, labels, values, label) {
  const canvas = document.getElementById(id);
  if (!canvas || typeof Chart === "undefined") return;
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [{ label, data: values, backgroundColor: "#3d9cf0" }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#a8b3c7" }, grid: { color: "#2a364d" } },
        y: { ticks: { color: "#e8eef9" }, grid: { display: false } },
      },
    },
  });
}

async function loadMarket() {
  const f = filters();
  const q = queryString({
    title: f.title,
    location: f.location,
    experience: f.experience,
  });
  const limitQ = queryString({
    title: f.title,
    location: f.location,
    experience: f.experience,
    limit: f.limit,
  });
  setStatus(statusNode, "info", "Loading market data…");
  try {
    const [overview, skills, categories, experience, locations, companies, freshness] = await Promise.all([
      apiGet(`/api/v1/analytics/overview${q}`),
      apiGet(`/api/v1/analytics/skills${limitQ}`),
      apiGet(`/api/v1/analytics/categories${q}`),
      apiGet(`/api/v1/analytics/experience${queryString({ title: f.title, location: f.location })}`),
      apiGet(`/api/v1/analytics/locations${queryString({ title: f.title, experience: f.experience, limit: f.limit })}`),
      apiGet(`/api/v1/analytics/companies${limitQ}`),
      apiGet(`/api/v1/analytics/freshness${q}`),
    ]);
    if (!overview.active_jobs) {
      setStatus(statusNode, "empty", "No active jobs match these filters. Ingest jobs or clear filters.");
    } else {
      clearStatus(statusNode);
    }
    renderOverview(overview);
    renderRows(skillsBody, (skills.skills || []).map((item) => (
      `<tr>
        <td>${escapeHtml(item.skill)}</td>
        <td>${escapeHtml(item.category)}</td>
        <td>${formatNumber(item.job_count)}</td>
        <td>${formatShare(item.job_share)}</td>
      </tr>`
    )), 4);
    barChart(
      "skills-chart",
      (skills.skills || []).slice(0, 10).map((item) => item.skill),
      (skills.skills || []).slice(0, 10).map((item) => item.job_count),
      "Jobs containing skill",
    );
    renderRows(categoriesBody, (categories.categories || []).map((item) => (
      `<tr>
        <td>${escapeHtml(item.category)}</td>
        <td>${formatNumber(item.job_count)}</td>
        <td>${formatShare(item.job_share)}</td>
      </tr>`
    )), 3);
    renderRows(experienceBody, (experience.items || []).map((item) => (
      `<tr><td>${escapeHtml(item.experience_level)}</td><td>${formatNumber(item.job_count)}</td></tr>`
    )), 2);
    barChart(
      "experience-chart",
      (experience.items || []).map((item) => item.experience_level),
      (experience.items || []).map((item) => item.job_count),
      "Jobs",
    );
    renderRows(locationsBody, (locations.items || []).map((item) => (
      `<tr><td>${escapeHtml(item.location)}</td><td>${formatNumber(item.job_count)}</td></tr>`
    )), 2);
    barChart(
      "locations-chart",
      (locations.items || []).slice(0, 10).map((item) => item.location),
      (locations.items || []).slice(0, 10).map((item) => item.job_count),
      "Jobs",
    );
    renderRows(companiesBody, (companies.items || []).map((item) => (
      `<tr><td>${escapeHtml(item.company)}</td><td>${formatNumber(item.job_count)}</td></tr>`
    )), 2);
    renderRows(freshnessBody, (freshness.items || []).map((item) => (
      `<tr><td>${escapeHtml(item.bucket)}</td><td>${formatNumber(item.job_count)}</td></tr>`
    )), 2);
    barChart(
      "freshness-chart",
      (freshness.items || []).map((item) => item.bucket),
      (freshness.items || []).map((item) => item.job_count),
      "Jobs",
    );
  } catch (error) {
    const message = error.status === 503
      ? "Database is not configured or unavailable. Market counts need PostgreSQL."
      : error.message || "Could not load market data.";
    setStatus(statusNode, "error", message);
  }
}

filtersForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loadMarket();
});

loadMarket();
