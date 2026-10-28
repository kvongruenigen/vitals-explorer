from pathlib import Path

from scripts.export_portfolio import FILES, PUBLIC_REPO_URL, export_snapshot, public_readme


def test_snapshot_uses_only_explicit_allowlist(tmp_path):
    snapshot = export_snapshot(tmp_path)
    files = {p.relative_to(snapshot).as_posix() for p in snapshot.rglob('*') if p.is_file()}
    assert files == set(FILES) | {'PUBLICATION_REVIEW.txt'}
    assert not (snapshot / '.git').exists()
    assert not (snapshot / 'build').exists()
    assert not (snapshot / 'res/logo.webp').exists()
    assert not (snapshot / 'docs/security-scan.json').exists()
    assert not (snapshot / '.env').exists()
    assert (snapshot / '.env.example').exists()
    readme = (snapshot / 'README.md').read_text()
    assert 'docs/SECURITY_AUDIT.md' not in readme
    assert f'git clone {PUBLIC_REPO_URL}' in readme
    assert 'GPL-3.0-only' in (snapshot / 'COPYRIGHT').read_text()
    assert 'GNU GENERAL PUBLIC LICENSE' in (snapshot / 'LICENSE').read_text()
    assert 'pending-license' not in readme
    assert not (snapshot / 'docs/synthetic-demo.csv').exists()


def test_export_never_overwrites_previous_snapshot(tmp_path):
    first = export_snapshot(tmp_path)
    (first / 'PUBLICATION_REVIEW.txt').write_text('private review note')
    second = export_snapshot(tmp_path)
    assert first != second
    assert (first / 'PUBLICATION_REVIEW.txt').read_text() == 'private review note'


def test_public_readme_does_not_link_research_remote():
    source = (Path(__file__).resolve().parents[1] / 'README.md').read_text()
    result = public_readme(source)
    assert f'git clone {PUBLIC_REPO_URL}' in result
    assert '<YOUR_NEW_PUBLIC_REPOSITORY_URL>' not in result
    assert 'SECURITY.md' in result
