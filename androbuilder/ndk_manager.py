import os
import sys
import urllib.request
import zipfile
from pathlib import Path

class NDKManager:
    """Manages Android NDK installation"""
    
    NDK_BASE_URL = "https://dl.google.com/android/repository/"
    
    def __init__(self, project_path: Path, verbose: bool = False):
        self.project_path = project_path
        self.verbose = verbose
        self.ndk_root = project_path / ".androbuilder" / "ndk"
    
    def _log(self, *args):
        if self.verbose:
            print("[NDK Manager]", *args)
    
    def install_ndk(self, version: str) -> Path:
        """Download and install Android NDK"""
        self._log(f"Installing NDK {version}...")
        
        self.ndk_root.mkdir(parents=True, exist_ok=True)
        
        # Determine platform
        if sys.platform == "linux":
            platform = "linux"
        elif sys.platform == "darwin":
            platform = "darwin"
        elif sys.platform == "win32":
            platform = "windows"
        else:
            raise Exception(f"Unsupported platform: {sys.platform}")
        
        # NDK filename pattern
        ndk_filename = f"android-ndk-r{version}-{platform}.zip"
        ndk_url = f"{self.NDK_BASE_URL}{ndk_filename}"
        
        ndk_zip = self.ndk_root / ndk_filename
        ndk_extracted = self.ndk_root / f"android-ndk-r{version}"
        
        if ndk_extracted.exists():
            self._log(f"NDK {version} already installed")
            return ndk_extracted
        
        # Download NDK
        if not ndk_zip.exists():
            self._log(f"Downloading NDK from {ndk_url}...")
            try:
                urllib.request.urlretrieve(ndk_url, ndk_zip)
            except Exception as e:
                raise Exception(f"Failed to download NDK: {e}")
        
        # Extract NDK
        self._log("Extracting NDK...")
        with zipfile.ZipFile(ndk_zip, 'r') as zip_ref:
            zip_ref.extractall(self.ndk_root)
        
        self._log(f"NDK {version} installed successfully")
        return ndk_extracted