import os
import sys
import pathlib
import requests
import subprocess

def main():
    temp_dir = pathlib.Path(os.environ.get("TEMP", "."))
    setup_exe = temp_dir / "is_setup.exe"
    target_dir = pathlib.Path(os.environ.get("LOCALAPPDATA", ".")) / "InnoSetup"

    print(f"Downloading Inno Setup compiler to {setup_exe}...")
    r = requests.get("https://www.jrsoftware.org/download.php/is.exe", timeout=30)
    setup_exe.write_bytes(r.content)
    print("Download complete.")

    print(f"Installing Inno Setup compiler silently to {target_dir}...")
    cmd = f'"{setup_exe}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="{target_dir}"'
    res = subprocess.run(cmd, shell=True)
    
    iscc_path = target_dir / "ISCC.exe"
    if iscc_path.exists():
        print(f"🟢 Success! Inno Setup Compiler ISCC.exe is ready at: {iscc_path}")
    else:
        print(f"⚠️ ISCC.exe not found at expected path: {iscc_path}")

if __name__ == "__main__":
    main()
