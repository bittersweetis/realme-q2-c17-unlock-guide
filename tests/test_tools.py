# SPDX-License-Identifier: AGPL-3.0-only
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from unittest.mock import patch

import q2_tools as tools


class OfflineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Synthetic fixture only: no real phone bytes or identifiers.
        data = bytearray(0x400000)
        data[:10] = b'COMBO_BOOT'
        data[0x1000:0x11000] = bytes(range(256))*256
        data[0x200:0x208] = b'BRLYT\0\0\0'
        data[0x20d] = data[0x21d] = 0x10
        data[0x131c:0x1329] = b'AND_ROMINFO_v'
        data[0x1368] = 0x22
        cls.original = bytes(data)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'original.bin').write_bytes(cls.original)
            result = subprocess.run([sys.executable,'-B','-X','utf8',str(tools.UPSTREAM),str(root/'original.bin'),'boot1.bin'],
                                    input='\n',capture_output=True,text=True,encoding='utf-8',cwd=root,timeout=30)
            if result.returncode:
                raise RuntimeError(result.stdout+result.stderr)
            cls.expected = (root/'preloader_path/boot1.bin').read_bytes()
        cls.synthetic_profile = {'original_boot_sha256':tools.sha(cls.original),
                                 'patched_boot_sha256':tools.sha(cls.expected),
                                 'upstream_script_sha256':tools.file_sha(tools.UPSTREAM)}

    def test_patch_matches_independent_upstream_and_preserves_payload(self):
        with patch.object(tools,'profile',return_value=self.synthetic_profile):
            actual = tools.layout_patch(self.original)
        self.assertEqual(actual,self.expected)
        self.assertEqual(len(actual),0x400000)
        raw=self.original[0x1000:-0x3000]
        self.assertEqual(actual[0x2000:0x2000+len(raw)],raw)
        self.assertEqual(actual[0x104c],0)

    def test_unknown_original_is_rejected(self):
        with patch.object(tools,'profile',return_value=self.synthetic_profile):
            for bad in (self.original[:-1],b'bad'+self.original[3:]):
                with self.assertRaises(ValueError):tools.layout_patch(bad)

    def test_nonblank_discarded_tail_rejected_even_with_known_digest(self):
        bad=self.original[:-1]+b'X'
        p={**self.synthetic_profile,'original_boot_sha256':tools.sha(bad)}
        with patch.object(tools,'profile',return_value=p):
            with self.assertRaisesRegex(ValueError,'tail'):tools.layout_patch(bad)

    def test_patch_writes_new_output_only_and_refuses_changed_upstream(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(tools,'profile',return_value=self.synthetic_profile):
            root=Path(folder); source=root/'source.bin';out=root/'patched.bin'
            source.write_bytes(self.original)
            tools.patch(source,out)
            self.assertEqual(out.read_bytes(),self.expected)
            self.assertEqual(source.read_bytes(),self.original)
            with self.assertRaises(FileExistsError):tools.patch(source,out)
            p={**self.synthetic_profile,'upstream_script_sha256':'0'*64}
            with patch.object(tools,'profile',return_value=p):
                with self.assertRaisesRegex(ValueError,'upstream'):tools.patch(source,root/'other.bin')

    def test_gpt_parses_ranges_and_rejects_truncation(self):
        data=bytearray(8192+128)
        data[4096:4104]=b'EFI PART'
        struct.pack_into('<I',data,4096+12,92)
        struct.pack_into('<QII',data,4096+72,2,1,128)
        data[8192:8208]=b'1'*16
        struct.pack_into('<QQ',data,8192+32,10,11)
        data[8192+56:8192+68]='seccfg'.encode('utf-16-le')
        struct.pack_into('<I',data,4096+88,zlib.crc32(data[8192:]))
        struct.pack_into('<I',data,4096+16,zlib.crc32(data[4096:4096+92]))
        self.assertEqual(tools.parse_gpt(data),{'seccfg':{'offset':40960,'length':8192}})
        with self.assertRaises(ValueError):tools.parse_gpt(data[:-1])
        with self.assertRaises(ValueError):tools.parse_gpt(b'not GPT')

    def test_manifest_rejects_corruption_and_path_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);f=root/'file.bin';f.write_bytes(b'known')
            records={'files':[{'path':'file.bin','size':5,'sha256':tools.sha(b'known')}]}
            m=root/'recovery-manifest.json';m.write_text(json.dumps(records))
            tools.verify(root)
            f.write_bytes(b'other')
            with self.assertRaises(ValueError):tools.verify(root)
            records['files'][0]['path']='../outside.bin';m.write_text(json.dumps(records))
            with self.assertRaises(ValueError):tools.verify(root)

    def test_seccfg_readback_checks_entire_tail(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);before=b'A'*8388608;candidate=b'B'*4096
            (root/'seccfg-before-unlock.bin').write_bytes(before)
            (root/'seccfg-candidate-block.bin').write_bytes(candidate)
            (root/'seccfg-preflight.json').write_text(json.dumps({'hardware_checksum_verified':True,
                'candidate_sha256':tools.sha(candidate),'original_sha256':tools.sha(before)}))
            actual=root/'readback.bin';actual.write_bytes(candidate+before[4096:])
            tools.seccfg_readback(root,actual)
            actual.write_bytes(candidate+before[4096:-1]+b'X')
            with self.assertRaises(ValueError):tools.seccfg_readback(root,actual)


if __name__=='__main__':unittest.main()
