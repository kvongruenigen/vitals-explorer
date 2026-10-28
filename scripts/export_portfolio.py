"""Export a reviewable source snapshot without research history or legacy assets.

This copies an explicit allowlist. It never initializes Git, pushes, overwrites
an existing export, or changes the original repository's history.
"""
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_REPO_URL = 'https://github.com/kvongruenigen/vitals-explorer.git'
FILES = (
    '.env.example', '.gitignore', 'README.md', 'SECURITY.md', 'LICENSE', 'COPYRIGHT',
    'requirements.txt', 'requirements-dev.txt', 'pytest.ini', 'ruff.toml',
    'main.py', 'run_demo.py', 'run_demo.command', 'run_demo.cmd',
    'build_app.sh', 'building.ps1', 'version_info.txt', '.github/workflows/tests.yml',
    'biobeat/auth.py', 'biobeat/config.py', 'biobeat/demo.py',
    'biobeat/errors.py', 'biobeat/fetch.py', 'biobeat/plot.py', 'biobeat/utils.py',
    'biobeat/quality.py', 'biobeat/results.py',
    'res/app-icon.svg', 'res/app-icon.png', 'res/app-icon.ico',
    'scripts/demo_screenshots.py', 'scripts/record_demo.py', 'scripts/export_portfolio.py',
    'tests/test_core.py', 'tests/test_gui.py', 'tests/test_publication.py',
    'tests/test_quality.py', 'tests/test_launcher.py',
    'docs/images/main-synthetic.png', 'docs/images/plots-synthetic.png',
    'docs/images/table-synthetic.png', 'docs/videos/demo-synthetic.mp4', 'docs/PUBLISHING.md',
)


def public_readme(text):
    text = re.sub(
        r'(?m)^git clone \S+\ncd [^\n]+',
        f'git clone {PUBLIC_REPO_URL}\ncd vitals-explorer',
        text,
    )
    start = text.find('For publication findings and redacted affected commit/path metadata,')
    if start != -1:
        end = text.index('\n## Limitations', start)
        text = text[:start] + 'For privacy and demonstration scope, see [SECURITY.md](SECURITY.md).\n' + text[end:]
    start = text.find('## Publishing a recruiter demo')
    if start != -1:
        end = text.index('## License', start)
        text = text[:start] + (
            '## Privacy\n\n'
            'This portfolio uses synthetic data and original neutral branding. '
            'See [SECURITY.md](SECURITY.md) for privacy and demo scope.\n\n'
        ) + text[end:]
    return text


def export_snapshot(parent=None):
    sources = list(FILES)
    for name in sources:
        source = ROOT / name
        if source.is_symlink() or not source.is_file():
            raise ValueError(f'Expected a regular publication source file: {name}')
    parent = Path(parent) if parent is not None else ROOT / 'publication'
    parent.mkdir(parents=True, exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix='vitals-explorer-review-', dir=parent))
    for name in sources:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    readme = destination / 'README.md'
    readme.write_text(public_readme(readme.read_text()))
    (destination / 'PUBLICATION_REVIEW.txt').write_text(
        'DRAFT SOURCE SNAPSHOT — review before publication.\n'
        '1. Verify LICENSE and COPYRIGHT specify the intended GPL-3.0-only release.\n'
        '2. Verify the README clone URL points to kvongruenigen/vitals-explorer.\n'
        '3. Scan this snapshot and inspect its complete file list.\n'
        '4. Initialize a NEW repository here; never merge branches/tags from the research repository.\n'
        '5. Follow docs/PUBLISHING.md. No live API verification is claimed.\n'
        'No .git, old binaries, legacy logos, recordings, or historical audit inventory was copied.\n'
    )
    return destination


if __name__ == '__main__':
    destination = export_snapshot()
    print(f'Draft source snapshot: {destination}')
    print('No history rewritten or published. Complete PUBLICATION_REVIEW.txt before release.')
