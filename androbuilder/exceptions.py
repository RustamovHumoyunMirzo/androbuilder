class BuildError(Exception):
    """Base exception for build errors"""
    pass

class SDKError(BuildError):
    """SDK related errors"""
    pass

class NDKError(BuildError):
    """NDK related errors"""
    pass

class CompilationError(BuildError):
    """Compilation errors"""
    pass

class SigningError(BuildError):
    """Signing errors"""
    pass

class ResourceError(BuildError):
    """Resource processing errors"""
    pass