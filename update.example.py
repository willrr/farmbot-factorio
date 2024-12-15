import json, subprocess, re, urllib.request, lzma, tarfile, tempfile, shutil, os

FactorioVersionRequest = urllib.request.Request('https://factorio.com/api/latest-releases', headers={'User-Agent' : "Update Check Script v2"})
FactorioVersions = urllib.request.urlopen(FactorioVersionRequest).read()
FactorioVersionsObj = json.loads(FactorioVersions)

FactorioVersionOutput = subprocess.check_output(['/opt/factorio/bin/x64/factorio', '--version'], universal_newlines=True)
FactorioVersionCurrent = re.search(r'^Version: (\d+\.[0-9.]+) ', FactorioVersionOutput).group(1)

if (FactorioVersionCurrent != FactorioVersionsObj['stable']['headless']):
    DownloadRequest = urllib.request.Request('https://factorio.com/get-download/stable/headless/linux64', headers={'User-Agent' : "Update Check Script 3"})
    
    with urllib.request.urlopen(DownloadRequest) as response:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                        shutil.copyfileobj(response, tmp_file)

    with tarfile.open(tmp_file.name) as f:
            f.extractall('/opt')

    os.remove(tmp_file.name)
