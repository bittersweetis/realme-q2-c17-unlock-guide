# SPDX-License-Identifier: AGPL-3.0-only
"""Check the known Q2 F.12 -> C.17 OUTER archive and optionally copy it.

Local files only. No USB, network, installation, erase or phone-write APIs.
The vendor archive is kept byte-for-byte; it is never extracted/repacked.
"""
from pathlib import Path
import argparse
import hashlib
import os
import sys

EXPECTED_SIZE=3997003120
EXPECTED_SHA256='1313770a2618a2b4037e8b1e297cbc07a07790a7fe838fa957f85a2294add646'
PHONE_FILENAME='oplus_ota_downgrade.zip'


def file_hash(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda:stream.read(8*1024*1024),b''):digest.update(data)
    return digest.hexdigest()


def check(path):
    path=Path(path).resolve()
    if not path.is_file() or path.stat().st_size!=EXPECTED_SIZE:
        raise ValueError('Expected the complete outer C.17 rollback archive, exactly 3997003120 bytes')
    if file_hash(path)!=EXPECTED_SHA256:
        raise ValueError('SHA-256 differs from the reviewed outer archive; stop')
    return path


def prepare(path,copy_to=None):
    source=check(path)
    print('PASS: original outer rollback archive size and SHA-256 match.',flush=True)
    if copy_to is None:return source
    directory=Path(copy_to).resolve()
    directory.mkdir(parents=True,exist_ok=True)
    destination=directory/PHONE_FILENAME
    if destination.exists():
        check(destination)
        print('PASS: destination already contains the same verified archive; not overwritten.')
        return destination
    digest=hashlib.sha256()
    with source.open('rb') as stream,destination.open('xb') as output:
        for data in iter(lambda:stream.read(8*1024*1024),b''):
            output.write(data);digest.update(data)
        output.flush();os.fsync(output.fileno())
    if digest.hexdigest()!=EXPECTED_SHA256:
        raise ValueError('Source changed during copying; do not use the copied file')
    check(destination)
    print('PASS: copied byte-for-byte and reread successfully as '+PHONE_FILENAME)
    return destination


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    parser.add_argument('--copy-to',type=Path,help='Copy to this local folder with the phone-required filename')
    args=parser.parse_args()
    prepare(args.archive,args.copy_to)
    print('No phone accessed. System signature/compatibility checks and installation remain manual.')


if __name__=='__main__':
    try:main()
    except (OSError,ValueError) as error:
        print('STOP:',error,file=sys.stderr)
        sys.exit(1)
