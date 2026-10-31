# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only flash inspection; SEJ uses volatile RAM/register writes.

Builds a candidate on the PC. Never calls flash write/erase/reset APIs.
Ported from the device-tested private prototype; this public version has not
been run against a phone. Read the validation status in README.md.
"""
from pathlib import Path
import argparse
import json
import logging
import os
import struct
import sys
from q2_tools import ROOT, checked_backup, verify, profile, sha, new_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=ROOT/'private')
    args = parser.parse_args()
    directory = args.directory.resolve()
    verify(directory)
    checked_backup(directory)
    # This root is shared with mtk.cmd; it contains the user's own DA session.
    state_dir = ROOT
    identity_file = ROOT/'hwparam.json'
    if not identity_file.is_file() or not (state_dir/'.state').is_file():
        raise ValueError('Missing this user\'s MTKClient session; run the read-only backup first')
    identity = json.loads(identity_file.read_text(encoding='utf-8'))
    sys.path.insert(0,str(ROOT/'vendor/mtkclient'))
    from mtk_api import init,connect
    from mtkclient.Library.Partitions.gpt import GptSettings
    from mtkclient.Library.Hardware.seccfg import SecCfgV4
    os.chdir(ROOT)
    mtk = init(preloader=None,loader=None)
    mtk.config.gpt_settings = GptSettings(0,0,0)
    mtk,_ = connect(mtk,directory=str(state_dir),loglevel=logging.INFO)
    if mtk is None or mtk.config.hwcode != 0x996:
        raise ValueError('Wrong chip or connection failed')
    ufs = mtk.daloader.da.get_ufs_info(display=False)
    if ufs is None or not identity['cid'].lower().startswith(ufs.cid.hex().lower()):
        raise ValueError('Live UFS CID differs from saved session')
    if not identity['cid'].lower().endswith(ufs.serial.hex().lower()):
        raise ValueError('Live UFS serial differs from saved session')
    meid = mtk.config.get_meid()
    if meid is None and mtk.reinited:
        meid = bytes.fromhex(json.loads((state_dir/'.state').read_text(encoding='utf-8'))['meid'])
    if meid is None or meid.hex().lower()!=identity['meid'].lower():
        raise ValueError('BROM identity differs')
    mtk.config.meid = meid
    raw,gpt = mtk.daloader.get_gpt()
    page = mtk.daloader.daconfig.pagesize
    if gpt is None or page!=4096:
        raise ValueError('Unexpected storage geometry')
    parts = {p.name:{'offset':p.sector*page,'length':p.sectors*page} for p in gpt.partentries}
    p = profile()
    if parts!=p['partitions'] or ufs.lu0_size!=p['ufs_user_size']:
        raise ValueError('Live layout/capacity differs from reviewed profile')

    def read(name):
        item = parts[name]
        blob = mtk.daloader.readflash(addr=item['offset'],length=item['length'],filename='',parttype='user',display=False)
        if not isinstance(blob,(bytes,bytearray)) or len(blob)!=item['length']:
            raise ValueError('Incomplete live read: '+name)
        return bytes(blob)

    for name,record in p['stock_files'].items():
        if sha(read(name.removesuffix('.bin'))) != record['sha256']:
            raise ValueError('Live stock image differs: '+name)
    original = read('seccfg')
    if original!=(directory/'backup/seccfg.bin').read_bytes() or read('seccfg')!=original:
        raise ValueError('Live seccfg differs from independent original backup')
    if struct.unpack('<7I',original[:28])!=(0x4d4d4d4d,4,60,1,0,0,0x45454545):
        raise ValueError('Expected original locked V4 header')
    if mtk.daloader.xft is None:
        raise ValueError('XFLASH hardware crypto interface unavailable')
    hwc = mtk.daloader.xft.cryptosetup()
    source = SecCfgV4(hwc,mtk)
    if not source.parse(original) or source.hwtype!='V4':
        raise ValueError('Original hardware checksum/variant does not match the tested case')
    ok,generated = source.create('unlock')
    if not ok or len(generated)!=512:
        raise ValueError('Candidate generation failed')
    candidate = bytes(generated[:60])+original[60:4096]
    check = SecCfgV4(hwc,mtk)
    if not check.parse(candidate) or check.hwtype!='V4' or (check.lock_state,check.critical_lock_state)!=(3,1):
        raise ValueError('Independent candidate hardware validation failed')
    changes = [i for i,(a,b) in enumerate(zip(original[:4096],candidate)) if a!=b]
    if not changes or any(i not in (12,16) and not 28<=i<60 for i in changes):
        raise ValueError('Unexpected candidate modifications')
    for name in ('seccfg-before-unlock.bin','seccfg-candidate-block.bin','seccfg-preflight.json'):
        if (directory/name).exists():raise ValueError('Keep existing preflight; use a fresh reviewed backup directory')
    new_file(directory/'seccfg-before-unlock.bin',original)
    new_file(directory/'seccfg-candidate-block.bin',candidate)
    report={'hardware_checksum_verified':True,'crypto_variant':'V4',
            'original_sha256':sha(original),'candidate_sha256':sha(candidate),
            'flash_written':False,'write_offset':parts['seccfg']['offset'],'write_length':4096}
    new_file(directory/'seccfg-preflight.json',json.dumps(report,indent=2).encode())
    print('PASS: original and candidate verified with hardware SEJ; no flash write/erase/reset.')
    print('Keep the same phone connected. Candidate saved locally under private/.')


if __name__=='__main__':
    main()
