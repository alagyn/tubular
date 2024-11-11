import zipfile
import os
import glob


def compressArchive(archivePath: str, out: str):
    with zipfile.ZipFile(out, mode='w', compression=zipfile.ZIP_LZMA) as f:
        for x in glob.iglob(f"**", root_dir=archivePath, recursive=True):
            fullPath = os.path.join(archivePath, x)
            f.write(fullPath, x)


def decompressArchive(archiveZip: str, archivePath: str):
    with zipfile.ZipFile(archiveZip, mode='r',
                         compression=zipfile.ZIP_LZMA) as f:
        f.extractall(archivePath)


def compressOutputFile(outputFile: str) -> str:
    outpath = f'{outputFile}.zip'
    with zipfile.ZipFile(outpath, mode='w', compression=zipfile.ZIP_LZMA) as f:
        innerfile = os.path.split(outputFile)[1]
        f.write(outputFile, innerfile)
    return outpath


def decompressOutputFile(zippedOutput: str, outputDir: str):
    with zipfile.ZipFile(zippedOutput, mode='r',
                         compression=zipfile.ZIP_LZMA) as f:
        # strip .zip
        innerFile = os.path.splitext(zippedOutput)[0]
        # remove parents
        innerFile = os.path.split(innerFile)[1]
        f.extract(innerFile, outputDir)


def sanitizeFilepath(parent, path) -> str:
    fullpath = os.path.realpath(os.path.join(parent, path))

    if not fullpath.startswith(parent):
        raise RuntimeError(
            f"path: '{fullpath}' is not contained in '{parent}'")

    return fullpath
