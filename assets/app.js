const translations = {
  en: {
    documentTitle: "QUANTACT publication list",
    metaDescription: "QuantAct member directory and automatically refreshed publication feed from 2000 onward based on verified ORCID identifiers.",
    skipToContent: "Skip to content",
    brandAriaLabel: "QuantAct publications home",
    brandSubtitle: "Publication list",
    primaryNavigation: "Primary navigation",
    publications: "Publications",
    members: "Members",
    languageSelector: "Language",
    heroEyebrow: "Actuarial & financial mathematics",
    heroTitle: "QUANTACT publication list",
    browsePublications: "Browse publications",
    viewMembers: "View members",
    siteStatus: "Site status",
    publicationMonitor: "Publication monitor",
    refreshEnabled: "Two-week refresh enabled",
    refreshDescription: "Refreshes every two weeks through GitHub Actions.",
    membersLower: "members",
    orcidLinked: "ORCID-linked",
    since2000: "since 2000",
    researchOutput: "Research output",
    publicationsSince2000: "Publications since 2000",
    lastDataRefresh: "Last data refresh:",
    notYetRun: "not yet run",
    publicationFilters: "Publication filters",
    searchPublications: "Search publications",
    publicationSearchPlaceholder: "Search title, journal, or member…",
    filterPublicationsByMember: "Filter publications by member",
    allMembers: "All members",
    filterPublicationsByYear: "Filter publications by year",
    allYears: "All years",
    directory: "Directory",
    quantactMembers: "QuantAct members",
    missingOrcidExplanation: "Missing ORCID values are left blank by design.",
    memberFilters: "Member filters",
    searchMembers: "Search members",
    memberSearchPlaceholder: "Search member or institution…",
    filterMembersByInstitution: "Filter members by institution",
    allInstitutions: "All institutions",
    footerTitle: "QUANTACT publication list",
    footerDescription: "Publication index for the QuantAct laboratory.",
    footerSource: "Member source: Centre de recherches mathématiques (CRM). Publication metadata is drawn from public scholarly APIs using stored ORCID identifiers.",
    orcidNotListed: "ORCID not listed",
    noMembersMatch: "No members match this filter.",
    noPublicationsMatch: "No publications match this filter.",
    noPublicationData: "No publication data yet. Add verified ORCID identifiers to data/members.json, then run the GitHub workflow manually or wait for the next two-week refresh.",
    publicationFallback: "Publication",
    untitled: "Untitled",
    open: "Open ↗",
    dataLoadError: "The site data could not be loaded."
  },
  fr: {
    documentTitle: "Liste des publications de QUANTACT",
    metaDescription: "Répertoire des membres de QuantAct et liste des publications depuis 2000, actualisée automatiquement à partir d’identifiants ORCID vérifiés.",
    skipToContent: "Aller au contenu",
    brandAriaLabel: "Accueil des publications de QuantAct",
    brandSubtitle: "Liste des publications",
    primaryNavigation: "Navigation principale",
    publications: "Publications",
    members: "Membres",
    languageSelector: "Langue",
    heroEyebrow: "Mathématiques actuarielles et financières",
    heroTitle: "Liste des publications de QUANTACT",
    browsePublications: "Parcourir les publications",
    viewMembers: "Voir les membres",
    siteStatus: "État du site",
    publicationMonitor: "Suivi des publications",
    refreshEnabled: "Mise à jour toutes les deux semaines",
    refreshDescription: "Les données sont actualisées toutes les deux semaines avec GitHub Actions.",
    membersLower: "membres",
    orcidLinked: "liés à ORCID",
    since2000: "depuis 2000",
    researchOutput: "Production scientifique",
    publicationsSince2000: "Publications depuis 2000",
    lastDataRefresh: "Dernière actualisation des données :",
    notYetRun: "pas encore effectuée",
    publicationFilters: "Filtres des publications",
    searchPublications: "Rechercher des publications",
    publicationSearchPlaceholder: "Rechercher par titre, revue ou membre…",
    filterPublicationsByMember: "Filtrer les publications par membre",
    allMembers: "Tous les membres",
    filterPublicationsByYear: "Filtrer les publications par année",
    allYears: "Toutes les années",
    directory: "Répertoire",
    quantactMembers: "Membres de QuantAct",
    missingOrcidExplanation: "Les identifiants ORCID manquants sont laissés vides intentionnellement.",
    memberFilters: "Filtres des membres",
    searchMembers: "Rechercher des membres",
    memberSearchPlaceholder: "Rechercher un membre ou un établissement…",
    filterMembersByInstitution: "Filtrer les membres par établissement",
    allInstitutions: "Tous les établissements",
    footerTitle: "Liste des publications de QUANTACT",
    footerDescription: "Index des publications du laboratoire QuantAct.",
    footerSource: "Source des membres : Centre de recherches mathématiques (CRM). Les métadonnées des publications proviennent d’API savantes publiques et d’identifiants ORCID enregistrés.",
    orcidNotListed: "ORCID non indiqué",
    noMembersMatch: "Aucun membre ne correspond à ce filtre.",
    noPublicationsMatch: "Aucune publication ne correspond à ce filtre.",
    noPublicationData: "Aucune donnée de publication pour le moment. Ajoutez des identifiants ORCID vérifiés dans data/members.json, puis lancez manuellement le flux GitHub ou attendez la prochaine mise à jour bimensuelle.",
    publicationFallback: "Publication",
    untitled: "Sans titre",
    open: "Ouvrir ↗",
    dataLoadError: "Les données du site n’ont pas pu être chargées."
  }
};

const state = {
  members: [],
  publications: [],
  publicationQuery: "",
  publicationMember: "",
  memberQuery: "",
  year: "",
  institution: "",
  language: "en",
  generatedAt: null,
  dataLoaded: false
};
const MIN_PUBLICATION_YEAR = 2000;
const UQAM_NAME = "Université du Québec à Montréal";

const normalize = (value = "") => value.toLocaleLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const t = key => translations[state.language][key] || translations.en[key] || key;
const canonicalInstitution = value => value === "UQAM" ? UQAM_NAME : value;

function preferredLanguage() {
  try {
    const stored = localStorage.getItem("quantact-language");
    if (stored === "en" || stored === "fr") return stored;
  } catch (_) {
    // Local storage may be unavailable when the file is opened directly.
  }
  return (navigator.language || "en").toLowerCase().startsWith("fr") ? "fr" : "en";
}

function applyTranslations() {
  document.documentElement.lang = state.language;
  document.title = t("documentTitle");
  document.getElementById("meta-description").setAttribute("content", t("metaDescription"));
  document.querySelectorAll("[data-i18n]").forEach(element => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach(element => {
    element.setAttribute("aria-label", t(element.dataset.i18nAriaLabel));
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(element => {
    element.setAttribute("placeholder", t(element.dataset.i18nPlaceholder));
  });
  document.querySelectorAll("[data-language]").forEach(button => {
    button.setAttribute("aria-pressed", String(button.dataset.language === state.language));
  });
}

function setLanguage(language, persist = true) {
  state.language = language === "fr" ? "fr" : "en";
  if (persist) {
    try {
      localStorage.setItem("quantact-language", state.language);
    } catch (_) {
      // The language still changes when storage is unavailable.
    }
  }
  applyTranslations();
  if (state.dataLoaded) {
    updateStats(state.generatedAt);
    renderMembers();
    renderPublications();
  }
}

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
  state.members = (siteData.members || []).map(member => ({ ...member, institution: canonicalInstitution(member.institution) }));
  state.publications = (siteData.publications || []).filter(publication => Number(publication.year) >= MIN_PUBLICATION_YEAR);
  state.generatedAt = siteData.generated_at || null;
  state.dataLoaded = true;
  updateStats(state.generatedAt);
  populateFilters();
  renderMembers();
  renderPublications();
}

function updateStats(generatedAt) {
  document.getElementById("stat-members").textContent = state.members.length;
  document.getElementById("stat-orcid").textContent = state.members.filter(member => member.orcid).length;
  document.getElementById("stat-publications").textContent = state.publications.length;
  document.getElementById("last-updated").textContent = generatedAt
    ? new Date(generatedAt).toLocaleDateString(state.language === "fr" ? "fr-CA" : "en-CA", { year: "numeric", month: "long", day: "numeric" })
    : t("notYetRun");
}

function populateFilters() {
  const institutionFilter = document.getElementById("institution-filter");
  [...new Set(state.members.map(member => member.institution))].sort((a, b) => a.localeCompare(b)).forEach(institution => {
    const option = document.createElement("option");
    option.value = institution;
    option.textContent = institution;
    institutionFilter.appendChild(option);
  });
  const yearFilter = document.getElementById("year-filter");
  [...new Set(state.publications.map(publication => publication.year).filter(Boolean))].sort((a, b) => b - a).forEach(year => {
    const option = document.createElement("option");
    option.value = String(year);
    option.textContent = year;
    yearFilter.appendChild(option);
  });
  const publicationMemberFilter = document.getElementById("publication-member-filter");
  state.members.map(member => member.name).sort((a, b) => a.localeCompare(b)).forEach(name => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    publicationMemberFilter.appendChild(option);
  });
}

function renderMembers() {
  const grid = document.getElementById("member-grid");
  const query = normalize(state.memberQuery);
  const filtered = state.members.filter(member => {
    const matchesQuery = !query || normalize(`${member.name} ${member.institution}`).includes(query);
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
        ${member.orcid ? `<a class="orcid" href="https://orcid.org/${encodeURIComponent(member.orcid)}" target="_blank" rel="noopener">${escapeHtml(member.orcid)}</a>` : `<span class="no-orcid">${t("orcidNotListed")}</span>`}
      </div>
    </article>`).join("") || `<div class="empty">${t("noMembersMatch")}</div>`;
}

function renderPublications() {
  const list = document.getElementById("publication-list");
  const query = normalize(state.publicationQuery);
  const filtered = state.publications.filter(publication => {
    const haystack = normalize([publication.title, publication.journal, ...(publication.quantact_members || [])].join(" "));
    const matchesQuery = !query || haystack.includes(query);
    const matchesMember = !state.publicationMember || (publication.quantact_members || []).includes(state.publicationMember);
    const matchesYear = !state.year || String(publication.year || "") === state.year;
    return matchesQuery && matchesMember && matchesYear;
  });
  if (!filtered.length) {
    list.innerHTML = `<div class="empty">${state.publications.length ? t("noPublicationsMatch") : t("noPublicationData")}</div>`;
    return;
  }
  list.innerHTML = filtered.map(publication => {
    const link = publication.doi ? `https://doi.org/${publication.doi}` : publication.url;
    const journal = publication.journal || publication.type || t("publicationFallback");
    const tags = (publication.quantact_members || []).map(name => `<span class="tag">${escapeHtml(name)}</span>`).join("");
    return `<article class="publication-card">
      <div class="pub-year">${escapeHtml(publication.year || "—")}</div>
      <div>
        <h3 class="pub-title">${escapeHtml(publication.title || t("untitled"))}</h3>
        <p class="pub-meta">${escapeHtml(journal)}${publication.doi ? ` · DOI ${escapeHtml(publication.doi)}` : ""}</p>
        <div class="pub-members">${tags}</div>
      </div>
      ${link ? `<a class="pub-link" href="${escapeHtml(link)}" target="_blank" rel="noopener">${t("open")}</a>` : ""}
    </article>`;
  }).join("");
}

document.getElementById("publication-search").addEventListener("input", event => { state.publicationQuery = event.target.value; renderPublications(); });
document.getElementById("publication-member-filter").addEventListener("change", event => { state.publicationMember = event.target.value; renderPublications(); });
document.getElementById("year-filter").addEventListener("change", event => { state.year = event.target.value; renderPublications(); });
document.getElementById("member-search").addEventListener("input", event => { state.memberQuery = event.target.value; renderMembers(); });
document.getElementById("institution-filter").addEventListener("change", event => { state.institution = event.target.value; renderMembers(); });
document.querySelectorAll("[data-language]").forEach(button => {
  button.addEventListener("click", () => setLanguage(button.dataset.language));
});

setLanguage(preferredLanguage(), false);
loadData().catch(error => {
  console.error(error);
  document.getElementById("publication-list").innerHTML = `<div class="empty">${t("dataLoadError")}</div>`;
});
