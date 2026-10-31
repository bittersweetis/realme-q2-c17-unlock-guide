# SPDX-License-Identifier: AGPL-3.0-only
from pathlib import Path
import hashlib
import tempfile
import unittest
from unittest.mock import patch

import prepare_rollback as rollback


class RollbackTests(unittest.TestCase):
    def test_checks_content_copies_canonical_name_and_preserves_existing(self):
        data=b'synthetic outer archive fixture'
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(rollback,'EXPECTED_SIZE',len(data)), \
             patch.object(rollback,'EXPECTED_SHA256',hashlib.sha256(data).hexdigest()):
            root=Path(temp);source=root/'download.zip';source.write_bytes(data)
            self.assertEqual(rollback.check(source),source.resolve())
            target=rollback.prepare(source,root/'firmware')
            self.assertEqual(target.name,'oplus_ota_downgrade.zip')
            self.assertEqual(target.read_bytes(),data)
            self.assertEqual(source.read_bytes(),data)
            self.assertEqual(rollback.prepare(source,root/'firmware'),target)
            target.write_bytes(b'X'*len(data))
            with self.assertRaises(ValueError):rollback.prepare(source,root/'firmware')
            self.assertEqual(target.read_bytes(),b'X'*len(data))

    def test_rejects_inner_or_truncated_or_modified_file(self):
        data=b'reviewed outer fixture'
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(rollback,'EXPECTED_SIZE',len(data)), \
             patch.object(rollback,'EXPECTED_SHA256',hashlib.sha256(data).hexdigest()):
            f=Path(temp)/'candidate.zip'
            for bad in (data[:-1],b'X'*len(data)):
                f.write_bytes(bad)
                with self.assertRaises(ValueError):rollback.check(f)


if __name__=='__main__':unittest.main()
