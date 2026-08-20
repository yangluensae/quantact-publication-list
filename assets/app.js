const state = { members: [], publications: [], publicationQuery: "", publicationMember: "", memberQuery: "", year: "", institution: "" };
const MIN_PUBLICATION_YEAR = 2000;

const normalize = (value = "") => value.toLocaleLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

async function loadData() {
  let siteData = typeof QUANTACT_SITE_DATA === "undefined" ? null : QUANTACT_SITE_DATA;
  if (!siteData) {
    const [memberResponse, publicationResponse] = await Promise.all([
      fetch("data/members.json", { cache: "no-store" }),
      fetch("data/publications.json", { cache: "no-store" })
    ]);
    if (!memberResponse.ok || !publicationResponse.ok) throw new Error("Unable to load site data.");
    const memberData = await memberResponse.json();
    const publicationData = await publicationResponse.json();
    siteData = {
      members: memberData.members || [],
      publications: publicationData.publications || [],
      generated_at: publicationData.generated_at
    };
  }
  state.members = siteData.members || [];
  state.publications = (siteData.publications || []).filter(publication => Number(publication.year) >= MIN_PUBLICATION_YEAR);
  updateStats(siteData.generated_at);
  populateFilters();
  renderMembers();
  renderPublications();
}

function updateStats(generatedAt) {
  document.getElementById("stat-members").textContent = state.members.length;
  document.getElementById("stat-orcid").textContent = state.members.filter(m => m.orcid).length;
  document.getElementById("stat-publications").textContent = state.publications.length;
  document.getElementById("last-updated").textContent = generatedAt ? new Date(generatedAt).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }) : "not yet run";
}

function populateFilters() {
  const institutionFilter = document.getElementById("institution-filter");
  [...new Set(state.members.map(m => m.institution))].sort((a,b) => a.localeCompare(b)).forEach(institution => {
    const option = document.createElement("option");
    option.value = institution;
    option.textContent = institution;
    institutionFilter.appendChild(option);
  });
  const yearFilter = document.getElementById("year-filter");
  [...new Set(state.publications.map(p => p.year).filter(Boolean))].sort((a,b) => b-a).forEach(year => {
    const option = document.createElement("option");
    option.value = String(year);
    option.textContent = year;
    yearFilter.appendChild(option);
  });
  const publicationMemberFilter = document.getElementById("publication-member-filter");
  state.members.map(m => m.name).sort((a,b) => a.localeCompare(b)).forEach(name => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    publicationMemberFilter.appendChild(option);
  });
}

function renderMembers() {
  const grid = document.getElementById("member-grid");
  const q = normalize(state.memberQuery);
  const filtered = state.members.filter(member => {
    const matchesQuery = !q || normalize(`${member.name} ${member.institution}`).includes(q);
    const matchesInstitution = !state.institution || member.institution === state.institution;
    return matchesQuery && matchesInstitution;
  });
  grid.innerHTML = filtered.map(member => `
    <article class="member-card">
      <div>
        <h3>${escapeHtml(member.name)}</h3>
        <p>${escapeHtml(member.institution)}</p>
      </div>
      <div class="member-bottom">
        ${member.orcid ? `<a class="orcid" href="https://orcid.org/${encodeURIComponent(member.orcid)}" target="_blank" rel="noopener">${escapeHtml(member.orcid)}</a>` : `<span class="no-orcid">ORCID not listed</span>`}
      </div>
    </article>`).join("") || `<div class="empty">No members match this filter.</div>`;
}

function renderPublications() {
  const list = document.getElementById("publication-list");
  const q = normalize(state.publicationQuery);
  const filtered = state.publications.filter(publication => {
    const haystack = normalize([publication.title, publication.journal, ...(publication.quantact_members || [])].join(" "));
    const matchesQuery = !q || haystack.includes(q);
    const matchesMember = !state.publicationMember || (publication.quantact_members || []).includes(state.publicationMember);
    const matchesYear = !state.year || String(publication.year || "") === state.year;
    return matchesQuery && matchesMember && matchesYear;
  });
  if (!filtered.length) {
    list.innerHTML = `<div class="empty">${state.publications.length ? "No publications match this filter." : "No publication data yet. Add verified ORCID identifiers to data/members.json, then run the GitHub workflow manually or wait for the next two-week refresh."}</div>`;
    return;
  }
  list.innerHTML = filtered.map(pub => {
    const link = pub.doi ? `https://doi.org/${pub.doi}` : pub.url;
    const journal = pub.journal || pub.type || "Publication";
    const tags = (pub.quantact_members || []).map(name => `<span class="tag">${escapeHtml(name)}</span>`).join("");
    return `<article class="publication-card">
      <div class="pub-year">${escapeHtml(pub.year || "—")}</div>
      <div>
        <h3 class="pub-title">${escapeHtml(pub.title || "Untitled")}</h3>
        <p class="pub-meta">${escapeHtml(journal)}${pub.doi ? ` · DOI ${escapeHtml(pub.doi)}` : ""}</p>
        <div class="pub-members">${tags}</div>
      </div>
      ${link ? `<a class="pub-link" href="${escapeHtml(link)}" target="_blank" rel="noopener">Open ↗</a>` : ""}
    </article>`;
  }).join("");
}

document.getElementById("publication-search").addEventListener("input", e => { state.publicationQuery = e.target.value; renderPublications(); });
document.getElementById("publication-member-filter").addEventListener("change", e => { state.publicationMember = e.target.value; renderPublications(); });
document.getElementById("year-filter").addEventListener("change", e => { state.year = e.target.value; renderPublications(); });
document.getElementById("member-search").addEventListener("input", e => { state.memberQuery = e.target.value; renderMembers(); });
document.getElementById("institution-filter").addEventListener("change", e => { state.institution = e.target.value; renderMembers(); });

loadData().catch(error => {
  console.error(error);
  document.getElementById("publication-list").innerHTML = `<div class="empty">The site data could not be loaded.</div>`;
});
