"""Exclusive secret-file creation with owner-only access from creation time."""
from contextlib import contextmanager
import os


def _windows_create(path):
    import ctypes
    from ctypes import wintypes
    import msvcrt
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    class SecurityAttributes(ctypes.Structure):
        _fields_ = [('length', wintypes.DWORD), ('descriptor', ctypes.c_void_p), ('inherit', wintypes.BOOL)]
    convert = advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW
    convert.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.DWORD)]
    convert.restype = wintypes.BOOL
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    class SidAndAttributes(ctypes.Structure):
        _fields_ = [('sid', ctypes.c_void_p), ('attributes', wintypes.DWORD)]
    class TokenGroups(ctypes.Structure):
        _fields_ = [('count', wintypes.DWORD), ('groups', SidAndAttributes * 1)]
    def information(kind):
        size = wintypes.DWORD()
        advapi.GetTokenInformation(token, kind, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not advapi.GetTokenInformation(token, kind, buffer, size, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        return buffer
    def sid_string(pointer):
        text = ctypes.c_void_p()
        if not advapi.ConvertSidToStringSidW(pointer, ctypes.byref(text)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return ctypes.wstring_at(text)
        finally:
            kernel.LocalFree(text)
    try:
        user = information(1)  # TokenUser
        principals = [sid_string(SidAndAttributes.from_buffer(user).sid)]
        restricted = information(11)  # TokenRestrictedSids
        count = wintypes.DWORD.from_buffer(restricted).value
        groups = (SidAndAttributes * count).from_buffer(restricted, TokenGroups.groups.offset)
        # Restricted tokens perform a second access check against these SIDs.
        # No broad inherited groups (Users/Everyone/Administrators) are granted.
        restricted_sids = [sid_string(group.sid) for group in groups]
        specific = [sid for sid in restricted_sids if sid == principals[0] or sid.startswith(('S-1-5-21-', 'S-1-5-5-', 'S-1-15-2-', 'S-1-15-3-'))]
        if restricted_sids and not specific:
            raise PermissionError('Cannot create a private secret file for this restricted Windows identity.')
        principals += specific
    finally:
        kernel.CloseHandle(token)
    descriptor = ctypes.c_void_p()
    sddl = 'D:P' + ''.join('(A;;FA;;;' + sid + ')' for sid in dict.fromkeys(principals))
    if not convert(sddl, 1, ctypes.byref(descriptor), None):
        raise ctypes.WinError(ctypes.get_last_error())
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(SecurityAttributes), wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    attributes = SecurityAttributes(ctypes.sizeof(SecurityAttributes), descriptor, False)
    try:
        handle = create(os.path.abspath(path), 0x40000000, 0, ctypes.byref(attributes), 1, 0x80, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return msvcrt.open_osfhandle(handle, os.O_WRONLY | os.O_BINARY)
        except BaseException:
            kernel.CloseHandle(handle)
            raise
    finally:
        kernel.LocalFree(descriptor)


@contextmanager
def secret_destination(path):
    """Reserve before HTTP. Refuse existing files/symlinks; never create parents."""
    fd = _windows_create(path) if os.name == 'nt' else os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
        # The open descriptor remains the destination throughout the request.
        yield stream


def write_secret(stream, response):
    secret = response.get('secret') if isinstance(response, dict) else None
    if not isinstance(secret, str) or not secret:
        raise ValueError('The response did not contain a usable signing secret; inspect the resource before retrying.')
    stream.write(secret + '\n')
    stream.flush()
    os.fsync(stream.fileno())
