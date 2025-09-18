import importlib.util
import pathlib


def _load_module_from_path(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def test_alembic_versions_have_upgrade_and_downgrade():
    versions_dir = pathlib.Path('migrations/versions')
    assert versions_dir.exists()
    files = sorted(p for p in versions_dir.glob('*.py'))
    assert files, 'no alembic versions found'
    for f in files:
        mod = _load_module_from_path(f)
        assert hasattr(mod, 'revision') and mod.revision, f'missing revision in {f.name}'
        assert hasattr(mod, 'upgrade') and callable(mod.upgrade), f'missing upgrade in {f.name}'
        assert hasattr(mod, 'downgrade') and callable(mod.downgrade), f'missing downgrade in {f.name}'


def test_alembic_chain_is_linear():
    versions_dir = pathlib.Path('migrations/versions')
    files = sorted(p for p in versions_dir.glob('*.py'))
    mods = [_load_module_from_path(f) for f in files]
    by_rev = {m.revision: m for m in mods if hasattr(m, 'revision')}
    # follow the chain backwards from head(s)
    heads = {m.revision for m in mods}
    parents = {getattr(m, 'down_revision', None) for m in mods}
    # head(s) are revisions that are not anyone's down_revision
    true_heads = heads - parents
    assert len(true_heads) == 1, f'expected single head, got {true_heads}'
    # walk down to None
    count = 0
    cur = by_rev[true_heads.pop()]
    seen = set()
    while cur and getattr(cur, 'down_revision', None) is not None:
        assert cur.revision not in seen
        seen.add(cur.revision)
        down = cur.down_revision
        assert down in by_rev, f'missing parent {down}'
        cur = by_rev[down]
        count += 1
    assert count + 1 == len(mods)

