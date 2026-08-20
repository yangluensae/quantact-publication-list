# QuantAct Publications

A static GitHub Pages site for the QuantAct Actuarial and Financial Mathematics Laboratory. It keeps the full member directory and automatically refreshes publications from 2000 onward for members with an explicitly stored ORCID identifier.

## Design principles

- **No ORCID guessing.** `orcid: null` means the member stays on the site but is skipped by the publication updater.
- **Exact-ORCID retrieval.** The scheduled script verifies that the ORCID record name matches the member, then accepts only works listed on that record or explicitly tagged to a matching author with that exact ORCID in Crossref. It never expands an ORCID into a third-party author cluster.
- **2000-present scope.** Older and undated records are excluded from both the generated data and the browser bundles.
- **Failure-safe.** If an ORCID endpoint fails temporarily, previously retrieved publications for that member are preserved.
- **Every two weeks.** The scheduled workflow refreshes on alternating Mondays. It can also be run manually from GitHub Actions.
- **Static hosting.** No server, database, API key, or paid service is needed for the website itself.

## Add or correct an ORCID

Edit `data/members.json`:

```json
{
  "name": "Example Member",
  "institution": "Example University",
  "orcid": "0000-0000-0000-0000"
}
```

Use `null` when there is no confirmed ORCID to store. The updater validates ORCID check digits before making any network calls.

## Run locally

```bash
python scripts/update_publications.py --check
python scripts/update_publications.py
python scripts/update_publications.py --build-site-data
```

You can now open `index.html` directly in a browser. The generated browser data bundles in `assets/` avoid the restrictions that normally prevent a `file://` page from fetching local JSON files.

To use a local web server instead:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000`.

## Deploy on GitHub Pages

1. Create a repository, for example `quantact-publications`, and put these files on the `main` branch.
2. In **Settings → Pages**, choose **GitHub Actions** as the Pages source.
3. In **Settings → Actions → General → Workflow permissions**, allow read/write permissions if your repository policy does not already permit the workflow's requested `contents: write` permission.
4. Open **Actions → Refresh publications and deploy Pages → Run workflow** once for the first publication refresh and deployment.
5. After that, the workflow refreshes and deploys automatically every two weeks. Ordinary pushes to `main` also redeploy the site without performing a publication refresh.

## Files

- `index.html` — site shell
- `assets/style.css` — responsive visual design
- `assets/app.js` — client-side member/publication filters
- `data/members.json` — curated member + ORCID registry
- `data/publications.json` — generated publication data
- `assets/site-data.js` and `assets/site-publications-*.js` — generated browser bundles for direct `index.html` opening
- `scripts/update_publications.py` — exact-ORCID ORCID/Crossref publication updater
- `tests/` — dependency-free updater tests
- `.github/workflows/pages.yml` — two-week refresh + GitHub Pages deployment

## Member roster source

The initial roster is based on the QuantAct member page of the Centre de recherches mathématiques (CRM), checked 2026-08-19:

`https://www.crmath.ca/en/quantact-actuarial-and-financial-mathematics-laboratory/quantact-members/`
