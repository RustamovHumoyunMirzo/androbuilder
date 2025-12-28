import argparse
import sys
from pathlib import Path
from .builder import Builder
from .exceptions import BuildError

def main():
    """Command-line interface for AndroBuilder"""
    parser = argparse.ArgumentParser(
        description='AndroBuilder - Pure Python Android APK Builder',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  androbuilder build ./MyApp
  androbuilder build ./MyApp --sdk 34 --sign --verbose
  androbuilder build ./MyApp --ndk 25.1.8937393 --multidex --proguard
  androbuilder build ./MyApp --signconfig keystore.jks myalias mypass --output ./dist
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Build command
    build_parser = subparsers.add_parser('build', help='Build an APK')
    build_parser.add_argument('path', help='Path to Android project')
    build_parser.add_argument('--output', '-o', default='./build', help='Output directory (default: ./build)')
    build_parser.add_argument('--sdk', help='SDK version or path')
    build_parser.add_argument('--ndk', help='NDK version or path')
    build_parser.add_argument('--buildtools', default='34.0.0', help='Build tools version (default: 34.0.0)')
    build_parser.add_argument('--target', default='34', help='Target SDK version (default: 34)')
    build_parser.add_argument('--minsdkversion', type=int, default=21, help='Minimum SDK version (default: 21)')
    build_parser.add_argument('--versioncode', type=int, default=1, help='Version code (default: 1)')
    build_parser.add_argument('--versionname', default='1.0.0', help='Version name (default: 1.0.0)')
    
    # Features
    build_parser.add_argument('--multidex', action='store_true', help='Enable multidex support')
    build_parser.add_argument('--proguard', action='store_true', help='Enable ProGuard code shrinking')
    build_parser.add_argument('--proguard-rules', nargs='+', help='ProGuard rules files')
    build_parser.add_argument('--no-sign', action='store_true', help='Do not sign the APK')
    build_parser.add_argument('--signconfig', nargs=3, metavar=('KEYSTORE', 'ALIAS', 'PASSWORD'), 
                             help='Signing configuration: keystore alias password')
    build_parser.add_argument('--aapt', action='store_true', help='Use AAPT instead of AAPT2')
    build_parser.add_argument('--no-optimize', action='store_true', help='Disable optimization')
    build_parser.add_argument('--no-clean', action='store_true', help='Do not clean before building')
    build_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # Version command
    version_parser = subparsers.add_parser('version', help='Show version')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show project info')
    info_parser.add_argument('path', help='Path to Android project')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'build':
            # Prepare configuration
            signconfig = {}
            if args.signconfig:
                signconfig = {
                    'path': args.signconfig[0],
                    'alias': args.signconfig[1],
                    'password': args.signconfig[2]
                }
            
            proguardconfig = {}
            if args.proguard_rules:
                proguardconfig['rules'] = args.proguard_rules
            
            # Create builder
            builder = Builder(
                path=args.path,
                sdk=args.sdk,
                ndk=args.ndk,
                multidex=args.multidex,
                proguard=args.proguard,
                proguardconfig=proguardconfig if args.proguard else None,
                sign=not args.no_sign,
                signconfig=signconfig,
                buildtools=args.buildtools,
                target=args.target,
                minsdkversion=args.minsdkversion,
                versioncode=args.versioncode,
                versionname=args.versionname,
                aapt2=not args.aapt,
                optimize=not args.no_optimize,
                verbose=args.verbose,
                clean=not args.no_clean
            )
            
            # Build
            apk_path = builder.build(args.output)
            print(f"\n✓ Build successful!")
            print(f"✓ APK: {apk_path}")
            
        elif args.command == 'version':
            from . import __version__
            print(f"AndroBuilder v{__version__}")
            
        elif args.command == 'info':
            show_project_info(args.path)
            
    except BuildError as e:
        print(f"✗ Build failed: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n✗ Build cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

def show_project_info(project_path: str):
    """Show information about an Android project"""
    import xml.etree.ElementTree as ET
    
    project = Path(project_path)
    manifest = project / "AndroidManifest.xml"
    
    if not manifest.exists():
        print(f"✗ AndroidManifest.xml not found in {project_path}")
        return
    
    tree = ET.parse(manifest)
    root = tree.getroot()
    
    package = root.get('package')
    version_code = root.get('{http://schemas.android.com/apk/res/android}versionCode', 'N/A')
    version_name = root.get('{http://schemas.android.com/apk/res/android}versionName', 'N/A')
    
    print("\n" + "="*60)
    print("Android Project Information")
    print("="*60)
    print(f"Project Path:  {project.resolve()}")
    print(f"Package Name:  {package}")
    print(f"Version Code:  {version_code}")
    print(f"Version Name:  {version_name}")
    
    # Count source files
    src_dir = project / "src"
    if src_dir.exists():
        java_files = list(src_dir.rglob("*.java"))
        kt_files = list(src_dir.rglob("*.kt"))
        print(f"Java Files:    {len(java_files)}")
        print(f"Kotlin Files:  {len(kt_files)}")
    
    # Check for native code
    jni_dir = project / "jni"
    if jni_dir.exists():
        print(f"Native Code:   Yes (jni/)")
    else:
        print(f"Native Code:   No")
    
    # Check for ProGuard rules
    proguard_file = project / "proguard-rules.pro"
    if proguard_file.exists():
        print(f"ProGuard:      Yes (proguard-rules.pro)")
    else:
        print(f"ProGuard:      No")
    
    print("="*60 + "\n")

if __name__ == '__main__':
    main()