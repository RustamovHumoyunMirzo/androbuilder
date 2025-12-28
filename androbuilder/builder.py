import os
import sys
import subprocess
import zipfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
import xml.etree.ElementTree as ET
import platform
import tarfile
import tempfile
import json
import urllib.request

from .sdk_manager import SDKManager
from .ndk_manager import NDKManager
from .exceptions import *

class Builder:
    """
    Main Android APK Builder class
    """
    
    def __init__(
        self,
        path: str,
        sdk: Optional[str] = None,
        ndk: Optional[str] = None,
        proguard: bool = False,
        proguardconfig: Optional[Dict[str, Any]] = None,
        sign: bool = True,
        signconfig: Optional[Dict[str, str]] = None,
        buildtools: str = "34.0.0",
        target: str = "34",
        minsdkversion: int = 21,
        versioncode: int = 1,
        versionname: str = "1.0.0",
        aapt2: bool = True,
        optimize: bool = True,
        verbose: bool = False,
        clean: bool = True,
        java_home: Optional[str] = None,
        java_path: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the Builder
        
        Args:
            path: Path to Android project source
            sdk: SDK version (e.g. "34") or path to existing SDK
            ndk: NDK version (e.g. "25.1.8937393") or path to existing NDK (optional)
            proguard: Enable ProGuard code shrinking
            proguardconfig: ProGuard configuration dict
            sign: Sign the APK
            signconfig: Signing configuration dict
            buildtools: Build tools version
            target: Target SDK version
            minsdkversion: Minimum SDK version
            versioncode: Version code
            versionname: Version name
            aapt2: Use AAPT2 instead of AAPT
            optimize: Optimize APK
            verbose: Verbose output
            clean: Clean build directories before building
            java_home: Path to java home
            java_path: Path to java
            allow_missing_resources: Skips missing resources exception
        """
        
        self.project_path = Path(path).resolve()
        self.verbose = verbose
        self.clean_build = clean
        self.allow_missing_resources = kwargs.get('allow_missing_resources', False)
        
        if not self.project_path.exists():
            raise BuildError(f"Project path does not exist: {path}")
        
        # Build configuration
        self.proguard = proguard
        self.proguardconfig = proguardconfig or {}
        self.sign = sign
        self.signconfig = signconfig or {}
        self.buildtools_version = buildtools
        self.target_version = target
        self.min_sdk = minsdkversion
        self.version_code = versioncode
        self.version_name = versionname
        self.use_aapt2 = aapt2
        self.optimize = optimize
        
        # SDK/NDK Management
        self.sdk_manager = SDKManager(self.project_path, verbose=verbose)
        self.ndk_manager = NDKManager(self.project_path, verbose=verbose) if ndk else None

        # Java setup
        self.java = None
        self.javac = None
        self.keytool = None

        if java_path:
            self.java = Path(java_path)
        elif java_home:
            self.java = Path(java_home) / "bin" / ("java.exe" if sys.platform == "win32" else "java")
        else:
            try:
                # Try system java first
                java_path = shutil.which("java") or "java"
                version = self._get_java_major_version(java_path)
                if 8 <= version <= 17:
                    self.java = Path(java_path)
                    self._log(f"Using system Java {version} at {self.java}")
                else:
                    # Download locally if system java unsupported or missing
                    self.java = self._get_local_java_path()
            except Exception as e:
                # Download fallback
                self.java = self._get_local_java_path()
        
        self.javac = self.java.with_name("javac")
        self.keytool = self.java.with_name("keytool")
        
        # Setup SDK
        if sdk:
            if Path(sdk).exists():
                self.android_sdk = Path(sdk)
                self._log("Using existing SDK at:", sdk)
            else:
                self._log("Downloading and installing SDK version:", sdk)
                self.android_sdk = self.sdk_manager.install_sdk(sdk, buildtools)
                self.sdk_manager.accept_licenses()
        else:
            self.android_sdk = self.sdk_manager.detect_sdk()
            if not self.android_sdk:
                self._log("No SDK found, installing default SDK...")
                self.android_sdk = self.sdk_manager.install_sdk(target, buildtools)
        
        # Setup NDK if requested
        self.android_ndk = None
        if ndk:
            if Path(ndk).exists():
                self.android_ndk = Path(ndk)
                self._log("Using existing NDK at:", ndk)
            else:
                self._log("Downloading and installing NDK version:", ndk)
                self.android_ndk = self.ndk_manager.install_ndk(ndk)
        
        self.build_tools = self.android_sdk / "build-tools" / self.buildtools_version
        self.platform = self.android_sdk / "platforms" / f"android-{self.target_version}"

        # Install build tools if missing
        if not self.build_tools.exists():
            self._log(f"Build tools {self.buildtools_version} not found, installing...")
            try:
                self.sdk_manager.install_build_tools(self.buildtools_version)
            except Exception as e:
                raise SDKError(f"Failed to install build tools: {e}")

        # Install platform if missing
        if not self.platform.exists():
            self._log(f"Platform android-{self.target_version} not found, installing...")
            try:
                self.sdk_manager.install_platform(self.target_version)
            except Exception as e:
                raise SDKError(f"Failed to install platform: {e}")
        
        # Additional configurations
        self.extra_configs = kwargs
        
        self._log("Builder initialized successfully")
    
    def _log(self, *args):
        """Log message if verbose mode is enabled"""
        if self.verbose:
            print("[AndroBuilder]", *args)

    def _get_local_java_path(self) -> Path:
        """
        Download Java 11 (Eclipse Temurin) inside `.androbuilder/java11`
        and return path to the java executable.
        """
        java_dir = self.project_path / ".androbuilder" / "java11"
        java_bin = java_dir / "bin" / ("java.exe" if sys.platform == "win32" else "java")

        if java_bin.exists():
            self._log(f"Using cached Java 11 at {java_bin}")
            return java_bin

        self._log("Downloading Java 11 (OpenJDK Temurin) locally...")

        # Create directory
        java_dir.mkdir(parents=True, exist_ok=True)

        # Download info from Adoptium API
        release_api = "https://api.adoptium.net/v3/assets/latest/11/hotspot"

        try:
            req = urllib.request.Request(
                release_api,
                headers = {
                    "User-Agent": "Mozilla/5.0 (compatible; AndroBuilder/1.0)"
                }
            )
            with urllib.request.urlopen(req) as resp:
                assets = json.load(resp)
        except Exception as e:
            raise BuildError(f"Failed to fetch Java 11 download info: {e}")

        system = platform.system().lower()
        arch = platform.machine().lower()

        arch_map = {
            'amd64': 'x64',
            'x86_64': 'x64',
            'aarch64': 'aarch64',
            'arm64': 'aarch64',
        }
        arch = arch_map.get(arch, arch)

        asset = None
        for asset_group in assets:
            bin = asset_group.get("binary")
            if not bin or bin.get("image_type") != "jdk":
                continue
            
            os_name = bin.get("os")
            arch_name = bin.get("architecture")
            pkg = bin.get("package")
            if os_name == system and arch_name == arch and pkg and pkg.get("link"):
                asset = pkg
                break

        if not asset:
            raise BuildError(f"Could not find suitable Java 11 binary for {system}/{arch}")

        url = asset["link"]
        filename = url.split("/")[-1]

        archive_path = java_dir / filename

        if not archive_path.exists():
            self._log(f"Downloading {url} ...")
            urllib.request.urlretrieve(url, archive_path)

        self._log(f"Extracting {archive_path} ...")

        if filename.endswith(".zip"):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(java_dir)
        elif filename.endswith((".tar.gz", ".tgz")):
            with tarfile.open(archive_path, 'r:gz') as tar_ref:
                tar_ref.extractall(java_dir)
        else:
            raise BuildError(f"Unknown Java archive format: {filename}")

        # The extracted folder usually starts with 'jdk-11' so find it
        extracted_folders = [d for d in java_dir.iterdir() if d.is_dir() and d.name.startswith("jdk-11")]
        if not extracted_folders:
            raise BuildError("Failed to find extracted Java folder after extraction")

        extracted_dir = extracted_folders[0]

        # Move extracted contents to java_dir root if needed
        # If extraction created a subfolder, move contents up
        if extracted_dir != java_dir:
            for item in extracted_dir.iterdir():
                target = java_dir / item.name
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                shutil.move(str(item), str(java_dir))
            shutil.rmtree(extracted_dir)

        if not java_bin.exists():
            raise BuildError(f"Java executable not found after extraction: {java_bin}")

        self._log(f"Java 11 downloaded and ready at {java_bin}")

        return java_bin

    def _get_java_major_version(self, java_path: str) -> int:
        """Return major version of given java binary"""
        try:
            output = subprocess.check_output(
                [java_path, "-version"], stderr=subprocess.STDOUT, text=True
            )
            import re
            # Java 8 output: 'java version "1.8.0_292"'
            # Java 11+: 'java version "11.0.10"'
            m = re.search(r'version "(1\.)?(\d+)', output)
            if m:
                ver = int(m.group(2))
                return ver
            return 0
        except Exception:
            return 0
    
    def _run_command(self, cmd: List[str], cwd: Optional[Path] = None, shell: bool = False) -> str:
        """Execute shell command with proper encoding handling"""
        self._log("Running:", " ".join(str(c) for c in cmd))
        
        try:
            # Try UTF-8 first
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                shell=shell
            )
        except UnicodeDecodeError:
            # Fallback to system encoding with error handling
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                encoding=sys.getdefaultencoding(),
                errors='replace',
                shell=shell
            )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            self._log("Command failed:")
            self._log("  Return code:", result.returncode)
            self._log("  Error:", error_msg)
            raise BuildError(
                f"Command failed with code {result.returncode}:\n"
                f"Command: {' '.join(str(c) for c in cmd)}\n"
                f"Error: {error_msg}"
            )
        
        return result.stdout
    
    def build(self, output: str = "./build") -> str:
        """
        Build the APK
        
        Args:
            output: Output directory path
            
        Returns:
            Path to the built APK file
        """
        self.output_path = Path(output).resolve()
        
        # Build directories
        self.gen_dir = self.output_path / "gen"
        self.obj_dir = self.output_path / "obj"
        self.bin_dir = self.output_path / "bin"
        self.lib_dir = self.output_path / "lib"
        
        try:
            self._log("="*60)
            self._log("Starting Android APK Build")
            self._log("="*60)
            
            if self.clean_build:
                self._clean()
            
            self._prepare_directories()
            self._validate_project()
            self._update_manifest()
            self._validate_manifest_resources()
            
            # Build pipeline
            self._generate_resources()
            if self.verbose:
                self._debug_r_generation()
            self._compile_java()
            
            if self.android_ndk:
                self._compile_native()
            
            self._process_classes()
            
            if self.proguard:
                self._run_proguard()
            
            self._create_dex()
            apk_path = self._package_apk()
            
            if self.android_ndk:
                self._add_native_libs(apk_path)
            
            if self.optimize:
                apk_path = self._optimize_apk(apk_path)
            
            apk_path = self._align_apk(apk_path)
            
            if self.sign:
                apk_path = self._sign_apk(apk_path)
            
            self._log("="*60)
            self._log("Build successful!")
            self._log(f"APK: {apk_path}")
            self._log("="*60)
            
            return str(apk_path)
            
        except Exception as e:
            self._log("Build failed:", str(e))
            raise BuildError(f"Build failed: {str(e)}")
    
    def _clean(self):
        """Clean build directories"""
        self._log("Cleaning build directories...")
        if self.output_path.exists():
            shutil.rmtree(self.output_path)
    
    def _prepare_directories(self):
        """Create build directories"""
        self._log("Preparing build directories...")
        self.gen_dir.mkdir(parents=True, exist_ok=True)
        self.obj_dir.mkdir(parents=True, exist_ok=True)
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        self.lib_dir.mkdir(parents=True, exist_ok=True)
    
    def _validate_project(self):
        """Validate project structure"""
        self._log("Validating project structure...")
        
        manifest = self.project_path / "AndroidManifest.xml"
        if not manifest.exists():
            raise BuildError("AndroidManifest.xml not found")
        
        src_dir = self.project_path / "src"
        if not src_dir.exists():
            raise BuildError("src directory not found")
        
        res_dir = self.project_path / "res"
        if not res_dir.exists():
            self._log("Warning: res directory not found, creating empty one")
            res_dir.mkdir()

    def _validate_manifest_resources(self):
        """Validate that resources referenced in manifest exist"""
        self._log("Validating manifest resources...")

        manifest = self.obj_dir / "AndroidManifest.xml"
        tree = ET.parse(manifest)
        root = tree.getroot()

        res_dir = self.project_path / "res"

        # Check for common resource references in manifest
        android_ns = '{http://schemas.android.com/apk/res/android}'

        icon = root.get(f'{android_ns}icon')
        label = root.get(f'{android_ns}label')
        theme = root.get(f'{android_ns}theme')

        self._log(f"Manifest references:")
        if icon:
            self._log(f"  Icon: {icon}")
        if label:
            self._log(f"  Label: {label}")
        if theme:
            self._log(f"  Theme: {theme}")

        # List available resources
        self._log("Available resource directories:")
        if res_dir.exists():
            for res_type in res_dir.iterdir():
                if res_type.is_dir():
                    files = list(res_type.iterdir())
                    self._log(f"  {res_type.name}: {len(files)} files")
                    for f in files:
                        self._log(f"    - {f.name}")
    
    def _update_manifest(self):
        """Update manifest with version info"""
        self._log("Updating manifest...")
        
        manifest_path = self.project_path / "AndroidManifest.xml"
        tree = ET.parse(manifest_path)
        root = tree.getroot()
        
        # Update version code and name
        root.set('{http://schemas.android.com/apk/res/android}versionCode', str(self.version_code))
        root.set('{http://schemas.android.com/apk/res/android}versionName', self.version_name)
        
        # Update minSdkVersion if needed
        uses_sdk = root.find('.//uses-sdk')
        if uses_sdk is not None:
            uses_sdk.set('{http://schemas.android.com/apk/res/android}minSdkVersion', str(self.min_sdk))
        
        # Save updated manifest to build dir
        updated_manifest = self.obj_dir / "AndroidManifest.xml"
        tree.write(updated_manifest, encoding='utf-8', xml_declaration=True)

    def _generate_resources(self):
        """Generate R.java and package resources using AAPT2 (Gradle-compatible)."""
        self._log("Generating resources...")

        res_dir = self.project_path / "res"
        manifest = self.obj_dir / "AndroidManifest.xml"

        if not res_dir.exists():
            self._log("No res directory found, skipping resource generation")
            self._create_minimal_r_java(None)
            return

        # Extract package name from manifest
        tree = ET.parse(manifest)
        root = tree.getroot()
        package_name = root.get("package")

        if not package_name:
            raise BuildError("Package name not found in AndroidManifest.xml")

        self._log(f"Package name: {package_name}")

        # Locate AAPT2
        aapt2 = self.build_tools / ("aapt2.exe" if sys.platform == "win32" else "aapt2")
        if not aapt2.exists():
            raise BuildError(f"aapt2 not found at {aapt2}")

        # Prepare output dirs
        compiled_res = self.obj_dir / "compiled_res"
        compiled_res.mkdir(parents=True, exist_ok=True)

        cmd = [
            str(aapt2),
            "compile",
            "--dir", str(res_dir),
            "-o", str(compiled_res)
        ]

        if self.verbose:
            cmd.append("-v")

        self._log("Compiling resources with AAPT2...")
        self._run_command(cmd)

        # Collect compiled .flat files (recursive)
        compiled_files = list(compiled_res.rglob("*.flat"))

        self._log(f"Found {len(compiled_files)} compiled resource files")
        if self.verbose:
            for f in compiled_files:
                self._log(f"  - {f.relative_to(compiled_res)}")

        if not compiled_files:
            if self.allow_missing_resources:
                self._log("Warning: No resources compiled, generating minimal R.java")
                self._create_minimal_r_java(package_name)
                return
            raise BuildError("AAPT2 produced no compiled resource files")

        resources_apk = self.bin_dir / "resources.apk"

        cmd = [
            str(aapt2),
            "link",
            "-I", str(self.platform / "android.jar"),
            "--manifest", str(manifest),
            "--java", str(self.gen_dir),
            "--auto-add-overlay",
            "-o", str(resources_apk),
        ]

        if self.verbose:
            cmd.append("-v")

        # Add all compiled .flat files
        cmd.extend(str(f) for f in compiled_files)

        self._log("Linking resources...")
        self._run_command(cmd)

        r_java_path = self.gen_dir / package_name.replace(".", os.sep) / "R.java"

        if not r_java_path.exists():
            if self.allow_missing_resources:
                self._log("Warning: R.java not generated, creating minimal version")
                self._create_minimal_r_java(package_name)
            else:
                raise BuildError(f"R.java was not generated at {r_java_path}")

        self._log(f"✓ R.java generated at {r_java_path}")

    def _create_minimal_r_java(self, package_name):
        if not package_name:
            return

        pkg_path = self.gen_dir / package_name.replace(".", os.sep)
        pkg_path.mkdir(parents=True, exist_ok=True)

        r_java = pkg_path / "R.java"
        with open(r_java, "w", encoding="utf-8") as f:
            f.write(
                f"package {package_name};\n\n"
                "public final class R {\n"
                "  public static final class id {}\n"
                "}\n"
            )

        self._log("Minimal R.java generated")

    def _compile_java(self):
        """Compile Java sources"""
        self._log("Compiling Java sources...")

        src_dir = self.project_path / "src"
        java_files = list(src_dir.rglob("*.java")) + list(self.gen_dir.rglob("*.java"))

        if not java_files:
            raise CompilationError("No Java source files found")

        self._log(f"Found {len(java_files)} Java files to compile")

        classes_dir = self.obj_dir / "classes"
        classes_dir.mkdir(parents=True, exist_ok=True)

        # Collect dependencies
        classpath = [str(self.platform / "android.jar")]
        libs_dir = self.project_path / "libs"
        if libs_dir.exists():
            classpath.extend([str(f) for f in libs_dir.glob("*.jar")])

        # Write file list
        file_list = self.obj_dir / "java_files.txt"
        with open(file_list, 'w', encoding='utf-8') as f:
            for java_file in java_files:
                f.write(f"{java_file}\n")

        # Use --release instead of -source/-target for better compatibility
        cmd = [
            str(self.javac),
            "-d", str(classes_dir),
            "-classpath", os.pathsep.join(classpath),
            "-sourcepath", f"{src_dir}{os.pathsep}{self.gen_dir}",
            "--release", "8",  # Use --release instead of -source/-target
            "-encoding", "UTF-8",
            "-Xlint:-options",  # Suppress obsolete options warning
            "@" + str(file_list)
        ]

        self._run_command(cmd)

        self._log(f"Java compilation successful")

    def _debug_r_generation(self):
        """Debug helper to check R.java generation"""
        self._log("=" * 60)
        self._log("Debugging R.java generation:")
        self._log("=" * 60)

        # Check gen directory
        self._log(f"Gen directory: {self.gen_dir}")
        self._log(f"Gen directory exists: {self.gen_dir.exists()}")

        if self.gen_dir.exists():
            self._log("Gen directory contents:")
            for item in self.gen_dir.rglob("*"):
                self._log(f"  {item}")

        # Check manifest
        manifest = self.obj_dir / "AndroidManifest.xml"
        if manifest.exists():
            tree = ET.parse(manifest)
            root = tree.getroot()
            package = root.get('package')
            self._log(f"Package from manifest: {package}")

            expected_r_path = self.gen_dir / package.replace('.', os.sep) / "R.java"
            self._log(f"Expected R.java path: {expected_r_path}")
            self._log(f"R.java exists: {expected_r_path.exists()}")

        # Check resources
        res_dir = self.project_path / "res"
        self._log(f"Resources directory: {res_dir}")
        self._log(f"Resources exist: {res_dir.exists()}")

        if res_dir.exists():
            self._log("Resource directories:")
            for item in res_dir.iterdir():
                if item.is_dir():
                    file_count = len(list(item.iterdir()))
                    self._log(f"  {item.name}: {file_count} files")

        self._log("=" * 60)
    
    def _compile_native(self):
        """Compile native libraries with NDK"""
        self._log("Compiling native libraries...")
        
        jni_dir = self.project_path / "jni"
        if not jni_dir.exists():
            self._log("No jni directory found, skipping native compilation")
            return
        
        ndk_build = self.android_ndk / ("ndk-build.cmd" if sys.platform == "win32" else "ndk-build")
        
        cmd = [
            str(ndk_build),
            f"NDK_PROJECT_PATH={self.project_path}",
            f"NDK_OUT={self.obj_dir / 'ndk'}",
            f"NDK_LIBS_OUT={self.lib_dir}"
        ]
        
        self._run_command(cmd, cwd=self.project_path)
    
    def _process_classes(self):
        """Process compiled classes"""
        self._log("Processing classes...")
        
        classes_dir = self.obj_dir / "classes"
        
        # Copy any resources from src
        for src_file in (self.project_path / "src").rglob("*"):
            if not src_file.suffix == ".java" and src_file.is_file():
                rel_path = src_file.relative_to(self.project_path / "src")
                dest = classes_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dest)
    
    def _run_proguard(self):
        """Run ProGuard for code shrinking"""
        self._log("Running ProGuard...")
        
        proguard_jar = self.android_sdk / "tools" / "proguard" / "lib" / "proguard.jar"
        if not proguard_jar.exists():
            self._log("ProGuard not found, skipping...")
            return
        
        classes_dir = self.obj_dir / "classes"
        proguard_dir = self.obj_dir / "proguard"
        proguard_dir.mkdir(exist_ok=True)
        
        # Create ProGuard config
        config = self.obj_dir / "proguard-rules.txt"
        with open(config, 'w') as f:
            f.write("-dontobfuscate\n")
            f.write("-dontoptimize\n")
            f.write("-keepattributes *Annotation*\n")
            f.write("-keep public class * extends android.app.Activity\n")
            
            # Add custom rules
            if 'rules' in self.proguardconfig:
                for rule_file in self.proguardconfig['rules']:
                    rule_path = self.project_path / rule_file
                    if rule_path.exists():
                        f.write(rule_path.read_text())
        
        cmd = [
            "java",
            "-jar", str(proguard_jar),
            "-injars", str(classes_dir),
            "-outjars", str(proguard_dir),
            "-libraryjars", str(self.platform / "android.jar"),
            "@" + str(config)
        ]
        
        self._run_command(cmd)
        
        # Replace classes with proguarded ones
        shutil.rmtree(classes_dir)
        shutil.move(str(proguard_dir), str(classes_dir))
    
    def _create_dex(self):
        """Create DEX file(s) using D8 (multidex is automatic)."""
        self._log("Creating DEX files...")

        classes_dir = self.obj_dir / "classes"
        if not classes_dir.exists():
            raise BuildError("Classes directory not found")

        class_files = list(classes_dir.rglob("*.class"))
        if not class_files:
            raise BuildError("No .class files found for dexing")

        d8_jar = self.build_tools / "lib" / "d8.jar"
        if not d8_jar.exists():
            raise BuildError(f"d8.jar not found at {d8_jar}")

        cmd = [
            str(self.java),
            "-Xms64m",
            "-Xmx512m",
            "-cp", str(d8_jar),
            "com.android.tools.r8.D8",
            "--output", str(self.bin_dir),
            "--lib", str(self.platform / "android.jar"),
            "--min-api", str(self.min_sdk),
        ]

        cmd.extend(str(f) for f in class_files)

        self._run_command(cmd)

        dex_files = list(self.bin_dir.glob("classes*.dex"))
        if not dex_files:
            raise BuildError("D8 did not produce any dex files")

        self._log(f"✓ DEX created: {', '.join(f.name for f in dex_files)}")
    
    def _package_apk(self):
        """Package APK"""
        self._log("Packaging APK...")
        
        apk_path = self.bin_dir / "app-unaligned.apk"
        
        if self.use_aapt2:
            # Resources already packaged
            resources_apk = self.bin_dir / "resources.apk"
            if resources_apk.exists():
                shutil.copy(resources_apk, apk_path)
            else:
                # Create empty APK
                with zipfile.ZipFile(apk_path, 'w') as zipf:
                    pass
        else:
            aapt = self.build_tools / ("aapt.exe" if sys.platform == "win32" else "aapt")
            
            cmd = [
                str(aapt),
                "package",
                "-f",
                "-M", str(self.obj_dir / "AndroidManifest.xml"),
                "-S", str(self.project_path / "res"),
                "-I", str(self.platform / "android.jar"),
                "-F", str(apk_path)
            ]
            
            self._run_command(cmd)
        
        # Add DEX files
        with zipfile.ZipFile(apk_path, 'a', zipfile.ZIP_DEFLATED) as zipf:
            for dex_file in self.bin_dir.glob("*.dex"):
                zipf.write(dex_file, dex_file.name)
        
        return apk_path
    
    def _add_native_libs(self, apk_path: Path):
        """Add native libraries to APK"""
        self._log("Adding native libraries...")
        
        if not self.lib_dir.exists():
            return
        
        with zipfile.ZipFile(apk_path, 'a', zipfile.ZIP_DEFLATED) as zipf:
            for lib_file in self.lib_dir.rglob("*.so"):
                arcname = f"lib/{lib_file.parent.name}/{lib_file.name}"
                zipf.write(lib_file, arcname)
    
    def _optimize_apk(self, apk_path: Path) -> Path:
        """Optimize APK"""
        self._log("Optimizing APK...")
        # Additional optimization can be added here
        return apk_path
    
    def _align_apk(self, apk_path: Path) -> Path:
        """Align APK"""
        self._log("Aligning APK...")
        
        aligned_apk = self.bin_dir / "app-aligned.apk"
        
        zipalign = self.build_tools / ("zipalign.exe" if sys.platform == "win32" else "zipalign")
        
        cmd = [
            str(zipalign),
            "-f",
            "4",
            str(apk_path),
            str(aligned_apk)
        ]
        
        self._run_command(cmd)
        
        return aligned_apk
    
    def _sign_apk(self, apk_path: Path) -> Path:
        """Sign APK"""
        self._log("Signing APK...")
        
        signed_apk = self.bin_dir / f"app-signed-{self.version_name}.apk"
        
        # Get signing config
        if 'path' in self.signconfig:
            keystore = Path(self.signconfig['path'])
            key_alias = self.signconfig.get('alias', 'key0')
            key_pass = self.signconfig.get('password', '')
            store_pass = self.signconfig.get('storepass', key_pass)
        else:
            # Use debug keystore
            keystore = self._get_debug_keystore()
            key_alias = "androiddebugkey"
            key_pass = store_pass = "android"
        
        apksigner = self.build_tools / ("apksigner.bat" if sys.platform == "win32" else "apksigner")
        
        cmd = [
            str(apksigner),
            "sign",
            "--ks", str(keystore),
            "--ks-key-alias", key_alias,
            "--ks-pass", f"pass:{store_pass}",
            "--key-pass", f"pass:{key_pass}",
            "--out", str(signed_apk),
            str(apk_path)
        ]
        
        self._run_command(cmd)
        
        return signed_apk
    
    def _get_debug_keystore(self) -> Path:
        """Get or create debug keystore"""
        keystore = Path.home() / ".android" / "debug.keystore"
        
        if not keystore.exists():
            self._log("Creating debug keystore...")
            keystore.parent.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                "keytool",
                "-genkeypair",
                "-keystore", str(keystore),
                "-alias", "androiddebugkey",
                "-keyalg", "RSA",
                "-keysize", "2048",
                "-validity", "10000",
                "-storepass", "android",
                "-keypass", "android",
                "-dname", "CN=Android Debug,O=Android,C=US"
            ]
            
            self._run_command(cmd)
        
        return keystore