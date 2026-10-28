# Publishing the recruiter portfolio

Use a new public repository with fresh history. Keep the original research repository private. Exporting a snapshot avoids transferring its old device IDs and bundled application copies; merely creating a branch or deleting the files in a new commit does not remove previous commits.

This workflow preserves the research repository and does not require rewriting it. If the original repository or artifacts have already been public, a fresh portfolio does not erase that exposure. Check existing releases/forks/cached references separately. GitHub explains the cleanup limitations in [Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

## Release license

This release uses **GPL-3.0-only**, with the full text in `LICENSE` and the author's notice in `COPYRIGHT`. The original author confirmed independent development; BioBeat supplied separately purchased API access rather than developing the application. The public repository is [kvongruenigen/vitals-explorer](https://github.com/kvongruenigen/vitals-explorer).

GPLv3 permits inspection, modification, redistribution, and commercial use under its conditions, including corresponding-source obligations when distributing covered works. See [GPLv3](https://www.gnu.org/licenses/gpl-3.0.html). PyQt5 and PyQtWebEngine have their own GPLv3/commercial terms; paid BioBeat API access is separate from a Riverbank commercial license. See [Riverbank licensing](https://www.riverbankcomputing.com/software/pyqt/) and [its FAQ](https://www.riverbankcomputing.com/commercial/license-faq).

The source and synthetic screenshots are the initial portfolio release. Before distributing bundled executables, preserve applicable dependency notices and fulfill source and other obligations for the exact bundled components. A top-level LICENSE alone does not cover every dependency requirement.

## Prepare a source snapshot

From the development checkout:

```bash
python scripts/export_portfolio.py
```

The script prints a new directory under ignored `publication/`. It uses an explicit allowlist, copies no `.git`, and leaves the original repository unchanged. It excludes old branding, build output, data exports, logs, filled configuration, private audit reports, and historical commit inventories. It does not create a remote repository or upload anything. Each run creates a new review directory.

Each snapshot includes `LICENSE` and `COPYRIGHT`. In the snapshot:

1. Inspect `PUBLICATION_REVIEW.txt` and every included file. Verify the README clone URL points to `kvongruenigen/vitals-explorer`, and that GPL-3.0-only is stated consistently.
2. Install `requirements-dev.txt` in a new virtual environment. Run `python -m pytest -q` and `python -m ruff check main.py biobeat tests scripts`. Desktop tests are optional; set `RUN_GUI_TESTS=1` in a desktop session.
3. Run `python main.py --demo`, click **Fetch Data**, inspect the charts/table, and export a synthetic CSV. No API access is needed. Keep exported CSVs out of Git.
4. Run `detect-secrets scan --all-files --no-verify` with the environment/caches excluded, and review its results privately. Do not publish scanner output containing sensitive values. Review all configuration and assets as well; scanning is not a guarantee.
5. Once all review items are resolved, remove the temporary `PUBLICATION_REVIEW.txt` from the snapshot and initialize a new Git repository **inside that snapshot directory**.

```bash
git init -b main
git add .
git diff --cached --stat
git status --short
```

Review the staged file list before committing. It must contain no `.env` (except `.env.example`), recordings, build output, virtual environment, private audit inventory, or legacy images. Create an empty private GitHub repository for staging, commit the reviewed snapshot, and push only its new `main` branch. Inspect it on GitHub before changing it to public. Use your chosen new repository URL; do not reuse or push to the research remote. Never use `--mirror`, push old tags, or merge an old research branch into the portfolio.

## Make the project easy for recruiters to assess

- Pin the new public repository on your GitHub profile and link to it from your CV/portfolio.
- Use the synthetic screenshot near the top of the README and keep the credential-free demo command prominent.
- Describe your contribution: independently built a Python/Qt research application integrating an authenticated API, timezone-aware processing, Plotly visualization, and CSV export; added background retrieval and mocked tests.
- State that the demo uses synthetic data, live integration requires authorized access, and this revision's live API behavior has not yet been verified.
- A short recording of the synthetic app can show chart interaction and export without asking recruiters to install it. Review every frame for desktop notifications, real data, and credentials before sharing.

A source repository and screenshots are enough for the first portfolio release. An executable is optional and can follow after target-platform, dependency-license, and signing checks. A fresh Git history is appropriate here; do not fabricate historical commits to replace the private research history.
