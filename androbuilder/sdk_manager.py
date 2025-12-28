import os
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional
import shutil
import subprocess

class SDKManager:
    """Manages Android SDK installation"""
    
    SDK_URLS = {
        "linux": "https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip",
        "darwin": "https://dl.google.com/android/repository/commandlinetools-mac-9477386_latest.zip",
        "win32": "https://dl.google.com/android/repository/commandlinetools-win-9477386_latest.zip",
    }
    
    def __init__(self, project_path: Path, verbose: bool = False):
        self.project_path = project_path
        self.verbose = verbose
        self.sdk_root = project_path / ".androbuilder" / "sdk"
    
    def _log(self, *args):
        if self.verbose:
            print("[SDK Manager]", *args)
    
    def detect_sdk(self) -> Optional[Path]:
        """Detect existing Android SDK"""
        sdk_paths = [
            os.environ.get('ANDROID_HOME'),
            os.environ.get('ANDROID_SDK_ROOT'),
            Path.home() / "Android" / "Sdk",
            Path.home() / "Library" / "Android" / "sdk",
            self.sdk_root,
        ]
        
        for path in sdk_paths:
            if path and Path(path).exists():
                self._log("Found SDK at:", path)
                return Path(path)
        
        return None
    
    def install_sdk(self, version: str, buildtools: str) -> Path:
        """Download and install Android SDK"""
        self._log(f"Installing SDK {version}...")
        
        self.sdk_root.mkdir(parents=True, exist_ok=True)
        
        # Download command line tools
        platform = sys.platform
        url = self.SDK_URLS.get(platform)
        if not url:
            raise Exception(f"Unsupported platform: {platform}")
        
        tools_zip = self.sdk_root / "cmdline-tools.zip"
        
        if not tools_zip.exists():
            self._log("Downloading SDK tools...")
            urllib.request.urlretrieve(url, tools_zip)
        
        # Extract
        cmdline_tools = self.sdk_root / "cmdline-tools"
        if not cmdline_tools.exists():
            self._log("Extracting SDK tools...")
            with zipfile.ZipFile(tools_zip, 'r') as zip_ref:
                zip_ref.extractall(self.sdk_root)
            
            # Move to correct location
            extracted = self.sdk_root / "cmdline-tools"
            latest = cmdline_tools / "latest"
            latest.mkdir(parents=True, exist_ok=True)
            
            for item in extracted.iterdir():
                if item.name != "latest":
                    shutil.move(str(item), str(latest / item.name))
        
        # Accept licenses first
        self._log("Accepting SDK licenses...")
        self.accept_licenses()
        
        # Install platform and build-tools
        self.install_platform(version)
        self.install_build_tools(buildtools)
        
        return self.sdk_root
    
    def install_platform(self, version: str):
        """Install Android platform"""
        self._log(f"Installing platform android-{version}...")
        sdkmanager = self._get_sdkmanager()
        
        try:
            subprocess.run(
                [sdkmanager, f"--sdk_root={self.sdk_root}", f"platforms;android-{version}"],
                check=True,
                capture_output=not self.verbose,
                text=True
            )
            self._log(f"Platform android-{version} installed successfully")
        except subprocess.CalledProcessError as e:
            self._log(f"Failed to install platform: {e}")
            if e.stderr:
                self._log(f"Error output: {e.stderr}")
            raise
    
    def install_build_tools(self, version: str):
        """Install Android build-tools"""
        self._log(f"Installing build-tools {version}...")
        sdkmanager = self._get_sdkmanager()
        
        try:
            subprocess.run(
                [sdkmanager, f"--sdk_root={self.sdk_root}", f"build-tools;{version}"],
                check=True,
                capture_output=not self.verbose,
                text=True
            )
            self._log(f"Build-tools {version} installed successfully")
        except subprocess.CalledProcessError as e:
            self._log(f"Failed to install build-tools: {e}")
            if e.stderr:
                self._log(f"Error output: {e.stderr}")
            raise
    
    def _get_sdkmanager(self) -> str:
        """Get sdkmanager path"""
        sdkmanager = self.sdk_root / "cmdline-tools" / "latest" / "bin" / "sdkmanager"
        if sys.platform == "win32":
            sdkmanager = sdkmanager.with_suffix(".bat")
        return str(sdkmanager)
    
    def accept_licenses(self):
        """Accept all SDK licenses"""
        sdkmanager = self._get_sdkmanager()

        try:
            # Accept all licenses by piping 'y' responses
            process = subprocess.Popen(
                [sdkmanager, f"--sdk_root={self.sdk_root}", "--licenses"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Send 'y' for each license prompt (need many for all licenses)
            output, errors = process.communicate(input='y\n' * 100)
            
            if process.returncode == 0:
                self._log("SDK licenses accepted")
            else:
                self._log(f"License acceptance returned code {process.returncode}")
                if self.verbose and errors:
                    self._log("Errors:", errors)

        except Exception as e:
            self._log(f"Warning: Could not accept licenses: {e}")