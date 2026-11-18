"""Checkpoint tests use a fake codec and temporary fictional hashes only."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from portal_migration_state import read_state,write_state,MigrationStateError


def encrypt(value):return b'fake-encrypted:'+value
def decrypt(value):
    if not value.startswith(b'fake-encrypted:'):raise ValueError('fake corruption')
    return value[len(b'fake-encrypted:'):]

PROFILE='a'*20


class MigrationStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'state';self.entry={'engine':'qt','port':17842,'localEntries':1,'audioChunks':2,'digest':'a'*64}

    def test_round_trip_is_sorted_and_contains_no_draft_values(self):
        other={**self.entry,'engine':'tauri','port':17843,'digest':'b'*64}
        self.assertIsNone(read_state(self.path,PROFILE,decrypt))
        value=write_state(self.path,PROFILE,17841,[other,self.entry],encrypt,decrypt)
        self.assertEqual(value['sources'],[self.entry,other]);self.assertEqual(read_state(self.path,PROFILE,decrypt),value)
        self.assertNotIn(b'brouillon fictif',self.path.read_bytes())
        before=self.path.read_bytes();write_state(self.path,PROFILE,17841,[self.entry,other],encrypt,decrypt)
        self.assertEqual(before,self.path.read_bytes())

    def test_unreadable_existing_file_is_preserved(self):
        self.path.write_bytes(b'corruption fictive');before=self.path.read_bytes()
        with self.assertRaises(MigrationStateError):read_state(self.path,PROFILE,decrypt)
        with self.assertRaises(MigrationStateError):write_state(self.path,PROFILE,17841,[self.entry],encrypt,decrypt)
        self.assertEqual(self.path.read_bytes(),before)

    def test_failed_replace_preserves_previous_checkpoint(self):
        write_state(self.path,PROFILE,17841,[self.entry],encrypt,decrypt);before=self.path.read_bytes()
        with patch('portal_migration_state.os.replace',side_effect=OSError('fictif')):
            with self.assertRaises(MigrationStateError):write_state(self.path,PROFILE,17841,[{**self.entry,'digest':'c'*64}],encrypt,decrypt)
        self.assertEqual(self.path.read_bytes(),before)

    def test_protected_source_is_recorded_without_draft_values_or_silent_downgrade(self):
        old=write_state(self.path,PROFILE,17841,[self.entry],encrypt,decrypt)
        self.assertEqual(old['format'],1)
        value=write_state(self.path,PROFILE,17841,[self.entry],encrypt,decrypt,protected={('qt',17842)})
        self.assertEqual(value['format'],2);self.assertEqual(value['protected'],[{'engine':'qt','port':17842}])
        self.assertEqual(read_state(self.path,PROFILE,decrypt),value)
        before=self.path.read_bytes()
        with self.assertRaises(MigrationStateError):write_state(self.path,PROFILE,17841,[self.entry],encrypt,decrypt)
        self.assertEqual(self.path.read_bytes(),before)

    def test_archive_fingerprints_cannot_be_silently_removed_or_downgraded(self):
        value=write_state(self.path,PROFILE,17841,[self.entry],encrypt,decrypt,
                          archives={('qt',17842):{'b'*64,'c'*64}})
        self.assertEqual(value['format'],3)
        self.assertEqual(value['protected'],[{'engine':'qt','port':17842,'ids':['b'*64,'c'*64]}])
        self.assertEqual(read_state(self.path,PROFILE,decrypt),value)
        before=self.path.read_bytes()
        with self.assertRaises(MigrationStateError):
            write_state(self.path,PROFILE,17841,[self.entry],encrypt,decrypt,archives={('qt',17842):{'b'*64}})
        with self.assertRaises(MigrationStateError):
            write_state(self.path,PROFILE,17841,[self.entry],encrypt,decrypt,protected={('qt',17842)})
        self.assertEqual(self.path.read_bytes(),before)
        with self.assertRaises(ValueError):write_state(self.path,PROFILE,17841,[self.entry],encrypt,decrypt,protected={('qt',17843)})
        self.assertEqual(self.path.read_bytes(),before)

    def test_duplicate_unknown_and_wrong_port_are_rejected(self):
        for sources in ([self.entry,self.entry],[{**self.entry,'digest':'A'*64}],
                        [{**self.entry,'extra':'private'}],[{**self.entry,'engine':'tauri','port':17841}]):
            with self.subTest(sources=sources),self.assertRaises(ValueError):write_state(self.path,PROFILE,17841,sources,encrypt,decrypt)
        write_state(self.path,PROFILE,17841,[self.entry],encrypt,decrypt);before=self.path.read_bytes()
        with self.assertRaises(MigrationStateError):write_state(self.path,PROFILE,17842,[],encrypt,decrypt)
        with self.assertRaises(MigrationStateError):read_state(self.path,'b'*20,decrypt)
        self.assertEqual(self.path.read_bytes(),before)

    def test_typed_audio_fingerprints_upgrade_without_losing_local_protection(self):
        local='b'*64;audio='audio-'+'c'*64
        old=write_state(self.path,PROFILE,17841,[self.entry],encrypt,decrypt,
                        archives={('qt',17842):{local}})
        self.assertEqual(old['format'],3)
        value=write_state(self.path,PROFILE,17841,[self.entry],encrypt,decrypt,
                          archives={('qt',17842):{local,audio}})
        self.assertEqual(value['format'],4)
        self.assertEqual(value['protected'][0]['ids'],sorted([local,audio]))
        self.assertEqual(read_state(self.path,PROFILE,decrypt),value)
        before=self.path.read_bytes()
        for ids in ({local},{audio},{'audio-'+('C'*64)}, {'audio-'+('d'*63)}):
            with self.subTest(ids=ids),self.assertRaises((MigrationStateError,ValueError)):
                write_state(self.path,PROFILE,17841,[self.entry],encrypt,decrypt,archives={('qt',17842):ids})
            self.assertEqual(self.path.read_bytes(),before)

    def test_extended_sources_track_archive_counts_and_cannot_downgrade(self):
        local='b'*64;audio='audio-'+'c'*64;source={**self.entry,'audioArchives':2}
        write_state(self.path,PROFILE,17841,[self.entry],encrypt,decrypt,archives={('qt',17842):{local}})
        state=write_state(self.path,PROFILE,17841,[source],encrypt,decrypt,archives={('qt',17842):{local,audio}})
        self.assertEqual(state['format'],5);self.assertEqual(state['sources'],[source]);self.assertEqual(read_state(self.path,PROFILE,decrypt),state)
        before=self.path.read_bytes()
        for sources,ids in (([self.entry],{local,audio}),([source],{local}),([{**source,'audioArchives':3001}],{local,audio})):
            with self.subTest(sources=sources),self.assertRaises((ValueError,MigrationStateError)):
                write_state(self.path,PROFILE,17841,sources,encrypt,decrypt,archives={('qt',17842):ids})
            self.assertEqual(self.path.read_bytes(),before)

    def test_extended_empty_checkpoint_has_explicit_empty_protection(self):
        state=write_state(self.path,PROFILE,17841,[],encrypt,decrypt,archives={},extended=True)
        self.assertEqual(state['format'],5);self.assertEqual(state['protected'],[])
        self.assertEqual(read_state(self.path,PROFILE,decrypt),state)
        before=self.path.read_bytes()
        with self.assertRaises(MigrationStateError):write_state(self.path,PROFILE,17841,[],encrypt,decrypt)
        self.assertEqual(self.path.read_bytes(),before)

    def test_destination_archive_manifest_is_protected_and_never_silently_shrinks(self):
        source={**self.entry,'audioArchives':1};protected={('qt',17842):{'audio-'+'a'*64}}
        state=write_state(self.path,PROFILE,17841,[source],encrypt,decrypt,archives=protected,
                          destination_archives={'a'*64,'b'*64})
        self.assertEqual(state['format'],6);self.assertEqual(state['destinationArchives'],['a'*64,'b'*64])
        self.assertEqual(read_state(self.path,PROFILE,decrypt),state);before=self.path.read_bytes()
        for ids in ({'a'*64}, {'b'*64}, {'a'*64,'B'*64}):
            with self.subTest(ids=ids),self.assertRaises((ValueError,MigrationStateError)):
                write_state(self.path,PROFILE,17841,[source],encrypt,decrypt,archives=protected,destination_archives=ids)
            self.assertEqual(self.path.read_bytes(),before)
        with self.assertRaises(MigrationStateError):
            write_state(self.path,PROFILE,17841,[source],encrypt,decrypt,archives=protected)
        self.assertEqual(self.path.read_bytes(),before)

    def test_empty_destination_manifest_can_record_a_new_empty_profile(self):
        state=write_state(self.path,PROFILE,17841,[],encrypt,decrypt,archives={},extended=True,destination_archives=[])
        self.assertEqual(state['format'],6);self.assertEqual(state['destinationArchives'],[])
        self.assertEqual(read_state(self.path,PROFILE,decrypt),state)

    def test_duplicate_json_and_symlink_are_refused(self):
        self.path.write_bytes(encrypt(b'{"format":1,"format":1,"port":17841,"sources":[]}'))
        with self.assertRaises(MigrationStateError):read_state(self.path,PROFILE,decrypt)
        target=Path(self.tmp.name)/'target';target.write_bytes(b'preserve')
        link=Path(self.tmp.name)/'link'
        try:link.symlink_to(target)
        except (OSError,NotImplementedError):self.skipTest('Lien symbolique indisponible.')
        with self.assertRaises(MigrationStateError):write_state(link,PROFILE,17841,[],encrypt,decrypt)
        self.assertEqual(target.read_bytes(),b'preserve')


if __name__=='__main__':unittest.main()
