"""Actual anchored IO: exclusive publication, persistent identity and junction guards."""
import hashlib
import os
import subprocess

from fastapi import HTTPException
import pytest

from backend.app.services.document_publication_io import AnchoredDirectory


@pytest.fixture
def destination(tmp_path):
    root = tmp_path / 'authorized'
    folder = root / 'project' / 'documents'
    folder.mkdir(parents=True)
    return root, folder


def failure(code, action):
    with pytest.raises(HTTPException) as raised:
        action()
    assert raised.value.status_code == code


def test_real_exclusive_candidate_promote_and_reopen_identity(destination):
    root, folder = destination
    content = b'Copie preparee et verifiee'
    with AnchoredDirectory(root, folder) as directory:
        directory_id = directory.identity
        assert not directory.exists('Affaire-CE.docx')
        receipt = directory.create_candidate('.agent-unique.pending', content)
        assert receipt['sha256'] == hashlib.sha256(content).hexdigest()
        assert receipt['size_bytes'] == len(content)
        assert directory.promote('.agent-unique.pending', 'Affaire-CE.docx', receipt) == receipt
        assert directory.exists('Affaire-CE.docx')
    with AnchoredDirectory(root, folder) as reopened:
        assert reopened.identity == directory_id
        assert reopened.verify('Affaire-CE.docx', receipt) == receipt
    assert (folder / 'Affaire-CE.docx').read_bytes() == content
    if os.name == 'nt':
        assert not (folder / '.agent-unique.pending').exists()
    else:
        assert (folder / '.agent-unique.pending').read_bytes() == content


def test_collision_never_replaces_even_identical_bytes(destination):
    root, folder = destination
    content = b'Identical bytes do not prove ownership'
    existing = folder / 'CE.docx'
    existing.write_bytes(content)
    with AnchoredDirectory(root, folder) as directory:
        with directory._open('CE.docx') as stream:
            original = directory._inspect(stream)
        receipt = directory.create_candidate('.agent-candidate.pending', content)
        assert receipt['identity'] != original['identity']
        failure(409, lambda:directory.promote('.agent-candidate.pending', 'CE.docx', receipt))
        assert directory.verify('CE.docx', original) == original
        failure(409, lambda:directory.verify('CE.docx', receipt))
    assert existing.read_bytes() == content
    assert (folder / '.agent-candidate.pending').read_bytes() == content


def test_candidate_collision_keeps_both_content_and_existing_file(destination):
    root, folder = destination
    existing = folder / '.agent-candidate.pending'
    existing.write_bytes(b'Existing diagnostic file')
    with AnchoredDirectory(root, folder) as directory:
        failure(409, lambda:directory.create_candidate(existing.name, b'New content'))
    assert existing.read_bytes() == b'Existing diagnostic file'


def test_tampered_candidate_is_not_promoted(destination):
    root, folder = destination
    with AnchoredDirectory(root, folder) as directory:
        receipt = directory.create_candidate('.agent-candidate.pending', b'Original bytes')
        (folder / '.agent-candidate.pending').write_bytes(b'Corrupted bytes')
        failure(409, lambda:directory.promote('.agent-candidate.pending', 'CE.docx', receipt))
        assert not directory.exists('CE.docx')


def test_same_bytes_with_another_identity_are_not_adopted(destination):
    root, folder = destination
    with AnchoredDirectory(root, folder) as directory:
        receipt = directory.create_candidate('.agent-first.pending', b'Copied bytes')
        directory.create_candidate('.agent-second.pending', b'Copied bytes')
        failure(409, lambda:directory.promote('.agent-second.pending', 'CE.docx', receipt))
        assert not directory.exists('CE.docx')


@pytest.mark.parametrize('name', ['../CE.docx','dir/CE.docx',r'dir\CE.docx','C:CE.docx','CON.docx','CE.docx.','.', '', 'CE\x00.docx'])
def test_untrusted_filename_cannot_create_files(destination, name):
    root, folder = destination
    with AnchoredDirectory(root, folder) as directory:
        failure(422, lambda:directory.create_candidate(name, b'New content'))
    assert not list(folder.iterdir())


def test_no_implicit_directory_creation_and_no_outside_root(destination, tmp_path):
    root, folder = destination
    missing = folder / 'missing'
    failure(409, lambda:AnchoredDirectory(root, missing).__enter__())
    assert not missing.exists()
    outside = tmp_path / 'other'
    outside.mkdir()
    failure(403, lambda:AnchoredDirectory(root, outside))
    assert not list(outside.iterdir())


def test_rejects_empty_and_oversized_candidates_before_open(destination):
    root, folder = destination
    with AnchoredDirectory(root, folder) as directory:
        failure(413, lambda:directory.create_candidate('.agent-empty.pending', b''))
        failure(413, lambda:directory.create_candidate('.agent-large.pending', b'x' * (50 * 1024 * 1024 + 1)))
    assert not list(folder.iterdir())


def test_real_junction_or_symlink_to_another_project_refused(destination, tmp_path):
    root, folder = destination
    outside = tmp_path / 'foreign'
    outside.mkdir()
    linked = folder / 'linked'
    if os.name == 'nt':
        # One native PowerShell shell, exact owned paths, no deletion/cleanup shell.
        script = "New-Item -ItemType Junction -Path '{}' -Target '{}' | Out-Null".format(
            str(linked).replace("'", "''"), str(outside).replace("'", "''"))
        subprocess.run(['powershell.exe','-NoProfile','-Command',script],check=True,capture_output=True)
    else:
        linked.symlink_to(outside, target_is_directory=True)
    failure(409, lambda:AnchoredDirectory(root, linked).__enter__())
    assert not list(outside.iterdir())


@pytest.mark.skipif(os.name != 'nt', reason='Windows handle sharing invariant')
def test_open_ancestors_cannot_be_renamed_or_replaced(destination):
    root, folder = destination
    with AnchoredDirectory(root, folder) as directory:
        with pytest.raises(OSError):
            folder.rename(folder.with_name('renamed'))
        with pytest.raises(OSError):
            folder.parent.rename(folder.parent.with_name('renamed-parent'))
        receipt = directory.create_candidate('.agent-held.pending', b'Anchored despite attempted rename')
        directory.promote('.agent-held.pending', 'CE.docx', receipt)
    assert (folder / 'CE.docx').is_file()


def test_reconcile_after_promotion_without_second_creation(destination):
    root, folder = destination
    with AnchoredDirectory(root, folder) as directory:
        receipt = directory.create_candidate('.agent-intent.pending', b'Committed intent; receipt not yet committed')
        directory.promote('.agent-intent.pending', 'CE.docx', receipt)
    # Simulates a process dying after the atomic move, before SQL success receipt.
    with AnchoredDirectory(root, folder) as directory:
        assert directory.verify('CE.docx', receipt) == receipt
    assert [path.name for path in folder.iterdir() if not path.name.startswith('.agent-')] == ['CE.docx']


def test_utf16_filename_retains_accents_and_non_bmp_characters(destination):
    root, folder = destination
    filename = 'Affaire-Déclaration-📄.docx'
    with AnchoredDirectory(root, folder) as directory:
        receipt = directory.create_candidate('.agent-unicode.pending', b'UTF16 name')
        assert directory.promote('.agent-unicode.pending', filename, receipt) == receipt
    assert (folder / filename).read_bytes() == b'UTF16 name'


def test_fsync_failure_keeps_diagnostic_candidate_without_final_file(destination, monkeypatch):
    root, folder = destination
    def failed(_descriptor):
        raise OSError('Simulated disk failure')
    monkeypatch.setattr(os, 'fsync', failed)
    with AnchoredDirectory(root, folder) as directory:
        failure(409, lambda:directory.create_candidate('.agent-partial.pending', b'Diagnostic bytes'))
        assert not directory.exists('CE.docx')
    assert (folder / '.agent-partial.pending').read_bytes() == b'Diagnostic bytes'


def test_closed_or_nested_context_cannot_reuse_a_native_handle(destination):
    root, folder = destination
    with AnchoredDirectory(root, folder) as directory:
        with pytest.raises(RuntimeError, match='déjà ouvert'):
            directory.__enter__()
    assert directory.handle is None
    with pytest.raises(RuntimeError, match='non ouvert'):
        directory.create_candidate('.agent-stale.pending', b'Never write through a stale handle')
    assert not list(folder.iterdir())
