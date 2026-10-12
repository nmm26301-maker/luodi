"""Check the resource-table installation requirements for Android 11+.

Use the final signed APK: signatures and ZIP assembly can change offsets.
This is a package-format check, not a device installation test.
"""
from pathlib import Path
import json, struct, sys, zipfile

def verify_resource_table(apk):
    apk=Path(apk)
    with zipfile.ZipFile(apk) as archive:
        names=archive.namelist()
        assert len(names)==len(set(names)), 'Duplicate APK entries'
        assert archive.testzip() is None, 'Corrupt ZIP entry'
        assert 'AndroidManifest.xml' in names and 'classes.dex' in names
        table=archive.getinfo('resources.arsc')
        assert table.compress_type==zipfile.ZIP_STORED, 'resources.arsc is compressed: Android error -124'
        with apk.open('rb') as stream:
            stream.seek(table.header_offset)
            header=stream.read(30)
            assert header[:4]==b'PK\x03\x04', 'Invalid local ZIP header'
            filename_size,extra_size=struct.unpack_from('<HH',header,26)
            data_offset=table.header_offset+30+filename_size+extra_size
        assert data_offset%4==0, 'resources.arsc is not 4-byte aligned: Android error -124'
        return {'compression':'stored','dataOffset':data_offset,'alignmentBytes':4,'crcVerified':True}

if __name__=='__main__':
    print(json.dumps(verify_resource_table(sys.argv[1]),indent=2))
