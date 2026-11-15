"""Metadata admission boundaries for the faster inventory, without audio/model."""
import os
from pathlib import Path
import stat
import subprocess
import sys
from types import SimpleNamespace

import pytest
from scripts.native_chunk_journal import Limits, inventory


def test_nested_directory_is_not_a_regular_journal_entry(tmp_path):
    (tmp_path / 'nested').mkdir()
    with pytest.raises(ValueError):
        inventory(tmp_path, Limits())


def test_symbolic_link_metadata_is_rejected_before_content_read(tmp_path, monkeypatch):
    path = tmp_path / 'foreign.json'
    path.write_bytes(b'{}')
    original = Path.lstat

    def lstat(value, *args, **kwargs):
        if value == path:
            return SimpleNamespace(st_mode=stat.S_IFLNK | 0o600, st_size=2)
        return original(value, *args, **kwargs)

    monkeypatch.setattr(Path, 'lstat', lstat)
    with pytest.raises(ValueError):
        inventory(tmp_path, Limits())


def test_regular_looking_windows_reparse_metadata_is_rejected(tmp_path, monkeypatch):
    path = tmp_path / 'foreign.json'
    path.write_bytes(b'{}')
    original = Path.lstat

    def lstat(value, *args, **kwargs):
        if value == path:
            return SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_size=2,
                st_file_attributes=getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))
        return original(value, *args, **kwargs)

    monkeypatch.setattr(Path, 'lstat', lstat)
    with pytest.raises(ValueError):
        inventory(tmp_path, Limits())


def test_real_directory_junction_or_symlink_never_admitted(tmp_path):
    journal = tmp_path / 'journal'
    outside = tmp_path / 'outside'
    journal.mkdir()
    outside.mkdir()
    marker = outside / 'retained.txt'
    marker.write_bytes(b'original')
    link = journal / 'linked-directory'
    if sys.platform == 'win32':
        # Binary output avoids interpreting cmd's OEM messages as UTF-8.
        result = subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(link), str(outside)],
                                capture_output=True, check=False)
        assert result.returncode == 0, result.stderr
    else:
        link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        inventory(journal, Limits())
    assert marker.read_bytes() == b'original'


def test_hardlinked_names_are_counted_conservatively(tmp_path):
    source = tmp_path / 'one.pending'
    linked = tmp_path / 'two.intent'
    source.write_bytes(b'original')
    os.link(source, linked)
    value = inventory(tmp_path, Limits())
    assert set(value['paths']) == {source, linked}
    assert value['bytes'] == 2 * len(b'original')


def test_foreign_enumeration_entry_refused(tmp_path, monkeypatch):
    journal = tmp_path / 'journal'
    journal.mkdir()
    outside = tmp_path / 'outside.json'
    outside.write_bytes(b'original')
    original = Path.iterdir

    def iterdir(path):
        return iter([outside]) if path == journal else original(path)

    monkeypatch.setattr(Path, 'iterdir', iterdir)
    with pytest.raises(ValueError):
        inventory(journal, Limits())
    assert outside.read_bytes() == b'original'
