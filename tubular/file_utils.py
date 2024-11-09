import zipfile
import os
import glob


def compressArchive(archivePath: str, out: str):
    with zipfile.ZipFile(out, mode='w', compression=zipfile.ZIP_LZMA) as f:
        print("Archiving", archivePath)
        for x in glob.iglob(f"**", root_dir=archivePath, recursive=True):
            print("Compressing", x)
            fullPath = os.path.join(archivePath, x)
            f.write(fullPath, x)


def decompressArchive(archiveZip: str, archivePath: str):
    with zipfile.ZipFile(archiveZip, mode='r',
                         compression=zipfile.ZIP_LZMA) as f:
        f.extractall(archivePath)
