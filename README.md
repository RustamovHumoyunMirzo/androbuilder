# AndroBuilder

A pure Python Android APK builder with automatic SDK/NDK management. Build Android apps without Gradle!

## Features

- 🚀 **Pure Python** - No Gradle or Android Studio required
- 📦 **Auto SDK/NDK Management** - Automatically downloads and installs required tools
- 🔧 **Full Control** - Complete control over the build process
- 🎯 **Multi-DEX Support** - Handle large apps with 65k+ methods
- 🔒 **ProGuard Integration** - Code shrinking and obfuscation
- 📱 **NDK Support** - Compile native C/C++ libraries
- ⚡ **Fast Builds** - Optimized build pipeline
- 🎨 **AAPT2 Support** - Modern resource compilation
- 🔐 **Flexible Signing** - Debug or release keystores

## Installation

```bash
pip install androbuilder
```

## Quick Start

### Python API

```python
from androbuilder import Builder

# Simple build
builder = Builder(path="./MyApp", sdk="34")
apk_path = builder.build("./output")
print(f"APK built: {apk_path}")

# Advanced build
builder = Builder(
    path="./MyApp",
    sdk="34",                    # Auto-downloads SDK 34
    ndk="25.1.8937393",         # Auto-downloads NDK
    multidex=True,
    proguard=True,
    proguardconfig={
        'rules': ['proguard-rules.pro'],
        'optimize': True
    },
    sign=True,
    signconfig={
        'path': 'release.keystore',
        'alias': 'mykey',
        'password': 'mypassword'
    },
    versioncode=2,
    versionname="1.0.1",
    verbose=True
)

apk_path = builder.build("./output")
```

### Command Line

```bash
# Basic build
androbuilder build ./MyApp

# Advanced build
androbuilder build ./MyApp \
    --sdk 34 \
    --ndk 25.1.8937393 \
    --multidex \
    --proguard \
    --signconfig release.keystore mykey mypass \
    --verbose \
    --output ./dist

# Show project info
androbuilder info ./MyApp

# Show version
androbuilder version
```

## Project Structure

Your Android project should have this structure:

```
MyApp/
├── AndroidManifest.xml
├── src/
│   └── com/
│       └── example/
│           └── app/
│               └── MainActivity.java
├── res/
│   ├── layout/
│   │   └── activity_main.xml
│   ├── values/
│   │   └── strings.xml
│   └── drawable/
├── libs/                    # Optional: JAR dependencies
├── jni/                     # Optional: Native code
│   ├── Android.mk
│   └── native-lib.cpp
└── proguard-rules.pro      # Optional: ProGuard rules
```

## Configuration Options

### Builder Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | str | Required | Path to Android project |
| `sdk` | str | None | SDK version or path |
| `ndk` | str | None | NDK version or path |
| `multidex` | bool | False | Enable multi-DEX |
| `proguard` | bool | False | Enable ProGuard |
| `proguardconfig` | dict | None | ProGuard configuration |
| `sign` | bool | True | Sign the APK |
| `signconfig` | dict | None | Signing configuration |
| `buildtools` | str | "34.0.0" | Build tools version |
| `target` | str | "34" | Target SDK version |
| `minsdkversion` | int | 21 | Minimum SDK version |
| `versioncode` | int | 1 | Version code |
| `versionname` | str | "1.0.0" | Version name |
| `aapt2` | bool | True | Use AAPT2 |
| `optimize` | bool | True | Optimize APK |
| `verbose` | bool | False | Verbose output |
| `clean` | bool | True | Clean before build |
| `java_home` | str | None | Path to java home |
| `java_path` | str | None | Path to java |
| `allow_missing_resources` | bool | False | Skips missing resources exception |

### Sign Configuration

```python
signconfig = {
    'path': 'my-release.keystore',  # Path to keystore
    'alias': 'mykey',                # Key alias
    'password': 'mypassword',        # Key password
    'storepass': 'storepassword'     # Store password (optional)
}
```

### ProGuard Configuration

```python
proguardconfig = {
    'rules': ['proguard-rules.pro'],  # Rule files
    'optimize': True                   # Enable optimization
}
```

## SDK/NDK Management

AndroBuilder automatically manages SDK and NDK installations:

### Automatic Download

```python
# Downloads SDK 34 automatically
builder = Builder(path="./MyApp", sdk="34")

# Downloads NDK 25.1.8937393 automatically
builder = Builder(path="./MyApp", sdk="34", ndk="25.1.8937393")
```

SDKs are installed in: `<project>/.androbuilder/sdk/`
NDKs are installed in: `<project>/.androbuilder/ndk/`

### Using Existing SDK/NDK

```python
# Use existing SDK
builder = Builder(path="./MyApp", sdk="/path/to/android-sdk")

# Use existing NDK
builder = Builder(path="./MyApp", ndk="/path/to/android-ndk")
```

### SDK Detection

AndroBuilder automatically detects SDKs in:
- `$ANDROID_HOME`
- `$ANDROID_SDK_ROOT`
- `~/Android/Sdk`
- `~/Library/Android/sdk`
- `<project>/.androbuilder/sdk`

## Examples

### Basic App

```python
from androbuilder import Builder

builder = Builder(
    path="./HelloWorld",
    sdk="34",
    versionname="1.0.0",
    verbose=True
)

apk = builder.build("./output")
```

### App with Native Code

```python
from androbuilder import Builder

builder = Builder(
    path="./NativeApp",
    sdk="34",
    ndk="25.1.8937393",
    verbose=True
)

apk = builder.build("./output")
```

### Release Build

```python
from androbuilder import Builder

builder = Builder(
    path="./MyApp",
    sdk="34",
    proguard=True,
    proguardconfig={'rules': ['proguard-rules.pro']},
    sign=True,
    signconfig={
        'path': 'release.keystore',
        'alias': 'release',
        'password': 'release123'
    },
    versioncode=10,
    versionname="1.0.9",
    optimize=True
)

apk = builder.build("./release")
```

### Large App with Multi-DEX

```python
from androbuilder import Builder

builder = Builder(
    path="./LargeApp",
    sdk="34",
    multidex=True,
    minsdkversion=21,
    verbose=True
)

apk = builder.build("./output")
```

## Error Handling

```python
from androbuilder import Builder, BuildError, SDKError

try:
    builder = Builder(path="./MyApp", sdk="34")
    apk = builder.build("./output")
except SDKError as e:
    print(f"SDK error: {e}")
except BuildError as e:
    print(f"Build error: {e}")
```

## Requirements

- Python 3.7+
- Java JDK 8+ (for javac and keytool)
- Internet connection (for SDK/NDK downloads)

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## LICENSE (MIT)

```
MIT License

Copyright (c) 2025 Rustamov Humoyun Mirzo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
