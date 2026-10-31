# SPDX-License-Identifier: AGPL-3.0-only
"""Offline reference helpers. No USB, erase, flash-write, or network APIs."""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import zlib

ROOT = Path(__file__).resolve().parent
PROFILE = ROOT/'profiles/RMX2117CN_C17.json'
UPSTREAM = ROOT/'third_party/path_preloader.py'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def profile():
    return json.loads(PROFILE.read_text(encoding='utf-8'))


def new_file(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)
    if path.read_bytes() != data:
        raise ValueError('Local file readback failed')


def parse_gpt(data, page=4096):
    """Parse the primary GPT dump; compare partition names/ranges, not UUIDs."""
    header = page
    if data[header:header+8] != b'EFI PART':
        raise ValueError('Expected a 4096-byte-sector primary GPT dump')
    header_size, header_crc = struct.unpack_from('<II',data,header+12)
    if not 92 <= header_size <= page or header+header_size > len(data):
        raise ValueError('Invalid GPT header size')
    checked_header=bytearray(data[header:header+header_size])
    checked_header[16:20]=b'\0'*4
    if zlib.crc32(checked_header)!=header_crc:
        raise ValueError('GPT header CRC mismatch')
    lba, count, size = struct.unpack_from('<QII', data, header+72)
    if not 0 < count <= 4096 or not 128 <= size <= 4096:
        raise ValueError('Invalid GPT entry geometry')
    if lba*page + count*size > len(data):
        raise ValueError('Truncated GPT entry array')
    if zlib.crc32(data[lba*page:lba*page+count*size])!=struct.unpack_from('<I',data,header+88)[0]:
        raise ValueError('GPT entries CRC mismatch')
    parts = {}
    for index in range(count):
        entry = data[lba*page+index*size:lba*page+(index+1)*size]
        if not any(entry[:16]):
            continue
        first, last = struct.unpack_from('<QQ', entry, 32)
        name = entry[56:128].decode('utf-16-le').split('\0', 1)[0]
        if not name or name in parts or last < first:
            raise ValueError('Invalid or duplicate GPT partition')
        parts[name] = {'offset': first*page, 'length': (last-first+1)*page}
    return parts


def checked_backup(directory):
    """Validate this exact C.17 layout and required files; no live-device claim."""
    directory = Path(directory).resolve()
    p = profile()
    gpt = directory/'backup/gpt.bin'
    if parse_gpt(gpt.read_bytes()) != p['partitions']:
        raise ValueError('GPT differs from the reviewed C.17 profile; stop')
    for name, rec in p['stock_files'].items():
        path = directory/'backup'/name
        if path.stat().st_size != rec['size'] or file_sha(path) != rec['sha256']:
            raise ValueError('Stock file mismatch: '+name)
    for region in ('boot1', 'boot2'):
        a, b = directory/(region+'.bin'), directory/(region+'-second.bin')
        if a.stat().st_size != 0x400000 or file_sha(a) != p['original_boot_sha256']:
            raise ValueError('Unreviewed original boot region: '+region)
        if a.read_bytes() != b.read_bytes():
            raise ValueError('Independent boot reads differ: '+region)
    seccfg = (directory/'backup/seccfg.bin').read_bytes()
    if len(seccfg) != p['partitions']['seccfg']['length'] or seccfg != (directory/'seccfg-second.bin').read_bytes():
        raise ValueError('seccfg size or independent read mismatch')
    header = struct.unpack('<7I', seccfg[:28])
    if header not in ((0x4d4d4d4d,4,60,1,0,0,0x45454545), (0x4d4d4d4d,4,60,3,1,0,0x45454545)):
        raise ValueError('Unexpected seccfg structure/state; no hardware checksum checked here')
    required = ('nvram','nvdata','nvcfg','protect1','protect2','persist','proinfo','metadata','md_udc')
    for name in required:
        if (directory/'backup'/(name+'.bin')).stat().st_size != p['partitions'][name]['length']:
            raise ValueError('Incomplete backup: '+name)
    return directory


def backup_manifest(directory):
    directory = checked_backup(directory)
    records = []
    for path in sorted(p for p in directory.rglob('*') if p.is_file()):
        if path.name == 'recovery-manifest.json':
            continue
        records.append({'path':path.relative_to(directory).as_posix(),
                        'size':path.stat().st_size,'sha256':file_sha(path)})
    new_file(directory/'recovery-manifest.json', json.dumps({'files':records},ensure_ascii=False,indent=2).encode())
    print('PASS: layout, stock images, double reads and',len(records),'files checked.')
    print('Not a full-device/personal-file backup; hardware seccfg checksum is a separate step.')


def verify(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory/'recovery-manifest.json').read_text(encoding='utf-8'))
    for rec in manifest['files']:
        path = (directory/rec['path']).resolve()
        if not path.is_relative_to(directory) or not path.is_file():
            raise ValueError('Unsafe or missing manifest path')
        if path.stat().st_size != rec['size'] or file_sha(path) != rec['sha256']:
            raise ValueError('Backup hash/size mismatch: '+rec['path'])
    print('PASS: saved backup manifest matches',len(manifest['files']),'files.')


def layout_patch(original):
    """Q2 C.17-specific adaptation of Shocked-Cat/Max_Goblin's algorithm."""
    p = profile()
    if len(original) != 0x400000 or sha(original) != p['original_boot_sha256']:
        raise ValueError('Only the reviewed C.17 original is accepted; no force option')
    if not original.startswith(b'COMBO_BOOT') or original[0x200:0x208] != b'BRLYT\0\0\0':
        raise ValueError('Invalid COMBO_BOOT/BRLYT header')
    if original.find(b'AND_ROMINFO_v') != 0x131c or original[0x1368] != 0x22:
        raise ValueError('Unexpected ROMINFO marker/flag')
    if original[0x20d]*256 != 0x1000 or any(original[-0x3000:]):
        raise ValueError('Unreviewed layout or nonblank discarded tail')
    raw = original[0x1000:-0x3000]
    out = bytearray(original)
    out[0x1000:] = b'\0'*(len(out)-0x1000)
    out[0x2000:0x2000+len(raw)] = raw
    for index, value in ((0x20d,0x20),(0x21d,0x20),(0x211,0x10),(0x212,0x10),(0x221,0x10),(0x222,0x10)):
        out[index] = value
    out[0x1000:0x1078] = original[0x131c:0x1394]
    out[0x104c] = 0
    out = bytes(out)
    if len(out) != len(original) or out[0x2000:0x2000+len(raw)] != raw or sha(out) != p['patched_boot_sha256']:
        raise ValueError('Patch result/payload preservation check failed')
    return out


def patch(input_path, output_path):
    original = Path(input_path).read_bytes()
    expected = layout_patch(original)
    if file_sha(UPSTREAM) != profile()['upstream_script_sha256']:
        raise ValueError('Reviewed upstream source changed')
    with tempfile.TemporaryDirectory(prefix='q2-offline-') as tmp:
        tmp = Path(tmp)
        source = tmp/'original.bin'
        source.write_bytes(original)
        result = subprocess.run([sys.executable,'-B','-X','utf8',str(UPSTREAM),str(source),'boot1.bin'],
                                cwd=tmp,input='\n',capture_output=True,text=True,encoding='utf-8',timeout=30)
        produced = tmp/'preloader_path/boot1.bin'
        if result.returncode or not produced.exists() or produced.read_bytes() != expected:
            raise ValueError('Upstream script and independent result differ')
    new_file(output_path, expected)
    print('PASS: offline candidate, payload preservation and independent upstream result verified.')
    print('SHA256',sha(expected))
    print('No USB access or phone write performed.')


def compare(a, b):
    a, b = Path(a), Path(b)
    if a.stat().st_size != b.stat().st_size or file_sha(a) != file_sha(b):
        raise ValueError('Files differ')
    print('PASS: same size and SHA-256.')


def seccfg_readback(directory, actual_path):
    directory = Path(directory)
    before = (directory/'seccfg-before-unlock.bin').read_bytes()
    candidate = (directory/'seccfg-candidate-block.bin').read_bytes()
    report = json.loads((directory/'seccfg-preflight.json').read_text(encoding='utf-8'))
    if not report['hardware_checksum_verified'] or sha(candidate) != report['candidate_sha256']:
        raise ValueError('Missing or changed hardware-verified candidate')
    if len(before)!=profile()['partitions']['seccfg']['length'] or len(candidate) != 4096 or sha(before) != report['original_sha256']:
        raise ValueError('Preflight original/candidate differs')
    if Path(actual_path).read_bytes() != candidate+before[4096:]:
        raise ValueError('Full 8 MiB seccfg readback differs; do not claim success')
    print('PASS: full seccfg readback matches hardware-verified candidate and unchanged tail.')
    print('Android startup/unlocked properties still need verification.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('backup-check','verify'):
        sub.add_parser(name).add_argument('directory',type=Path)
    p = sub.add_parser('patch-preloader'); p.add_argument('input',type=Path);p.add_argument('output',type=Path)
    p = sub.add_parser('compare');p.add_argument('first',type=Path);p.add_argument('second',type=Path)
    p = sub.add_parser('check-seccfg-readback');p.add_argument('directory',type=Path);p.add_argument('actual',type=Path)
    args = parser.parse_args()
    if args.command=='backup-check':backup_manifest(args.directory)
    elif args.command=='verify':verify(args.directory)
    elif args.command=='patch-preloader':patch(args.input,args.output)
    elif args.command=='compare':compare(args.first,args.second)
    else:seccfg_readback(args.directory,args.actual)


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,struct.error,subprocess.SubprocessError) as error:
        print('STOP:',error,file=sys.stderr)
        sys.exit(1)
