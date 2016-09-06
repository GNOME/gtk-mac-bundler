#include <Python.h>
#include <CoreFoundation/CoreFoundation.h>
#include <sys/syslimits.h>

static wchar_t*
widen_cfstring(CFStringRef str)
{
    int i;
    CFRange range = {0, 0};
    long len = CFStringGetLength(str);
    size_t size = sizeof(wchar_t) * (len + 1);
    size_t unisize = sizeof(UniChar) * (len + 1);
    wchar_t *buf = malloc(size);
    UniChar *unibuf = malloc(unisize);
    if (buf == NULL || unibuf == NULL)
    {
	if (unibuf != NULL)
	    free(unibuf);
	if (buf != NULL)
	    free(buf);
	return NULL;
    }
    memset(buf, 0, size);
    memset(unibuf, 0, unisize);
    range.length = len;
    CFStringGetCharacters(str, range, unibuf);
    for (i = 0; i < len; ++i)
	buf[i] = unibuf[i];
    free(unibuf);
    return buf;
}

static CFStringRef
make_filesystem_string(CFURLRef url)
{
    unsigned char cbuf[PATH_MAX + 1];
    CFStringRef str;
    memset(cbuf, 0, PATH_MAX + 1);
    if (!CFURLGetFileSystemRepresentation(url, 1, cbuf, PATH_MAX))
    {
	return NULL;
    }
    str = CFStringCreateWithBytes(NULL, cbuf, strlen((char*)cbuf),
				  kCFStringEncodingUTF8, 0);
    return str;
}

static wchar_t*
get_bundle_dir(void)
{
    CFBundleRef bundle = CFBundleGetMainBundle();
    CFURLRef bundle_url = CFBundleCopyBundleURL(bundle);
    CFStringRef str = make_filesystem_string(bundle_url);
    wchar_t *retval = widen_cfstring(str);
    CFRelease(bundle_url);
    CFRelease(str);
    return retval;
}

static void
set_python_path(void)
{
    CFBundleRef bundle = CFBundleGetMainBundle();
    CFURLRef bundle_url = CFBundleCopyResourcesDirectoryURL(bundle);
    CFMutableStringRef mstr;
    wchar_t *path;
    CFStringRef str = make_filesystem_string(bundle_url);
    CFRelease(bundle_url);
    mstr = CFStringCreateMutableCopy(NULL, 5 * PATH_MAX, str);
    CFStringAppendCString(mstr, "/lib/python34.zip:", kCFStringEncodingUTF8);
    CFStringAppend(mstr, str);
    CFStringAppendCString(mstr, "/lib/python3.4:",
			  kCFStringEncodingUTF8);
    CFStringAppend(mstr, str);
    CFStringAppendCString(mstr, "/lib/python3.4/plat-darwin:",
			  kCFStringEncodingUTF8);
    CFStringAppend(mstr, str);
    CFStringAppendCString(mstr, "/lib/python3.4/lib-dynload:",
			  kCFStringEncodingUTF8);
    CFStringAppend(mstr, str);
    CFStringAppendCString(mstr, "/lib/python3.4/site-packages",
			  kCFStringEncodingUTF8);
    CFRelease(str);
    path = widen_cfstring(mstr);
    CFRelease(mstr);
    Py_SetPath(path);
}

static wchar_t*
widen_c_string(char* string)
{
    CFStringRef str;
    wchar_t *retval;
    if (string == NULL) return NULL;
    str = CFStringCreateWithCString(NULL, string, kCFStringEncodingUTF8);
    retval = widen_cfstring(str);
    CFRelease(str);
    return retval;
}

static FILE*
open_scriptfile(void)
{
    FILE *fd = NULL;
    char full_path[PATH_MAX + 1];
    CFBundleRef bundle = CFBundleGetMainBundle();
    CFURLRef bundle_url = CFBundleCopyResourcesDirectoryURL(bundle);
    CFStringRef key = CFStringCreateWithCString(NULL, "GtkOSXLaunchScriptFile",
						kCFStringEncodingUTF8);
    CFStringRef str = make_filesystem_string(bundle_url);
    CFMutableStringRef mstr = CFStringCreateMutableCopy(NULL, PATH_MAX, str);
    CFStringRef filename = CFBundleGetValueForInfoDictionaryKey(bundle, key);
    CFStringAppendCString(mstr, "/", kCFStringEncodingUTF8);
    CFStringAppend(mstr, filename);
    CFRelease(key);
    if (CFStringGetCString(mstr, full_path, PATH_MAX, kCFStringEncodingUTF8))
	fd = fopen(full_path, "r");
    if (fd == NULL)
	printf("Failed to open script file %s\n", full_path);
    CFRelease(bundle_url);
    CFRelease(str);
    return fd;
}

int
main(int argc, char *argv[])
{
    int retval = 0, i;
    wchar_t **wargv = malloc(sizeof(wchar_t*) * argc);
    FILE *fd = open_scriptfile();
    if (fd == NULL)
    {
	return -1;
    }
    set_python_path();
    Py_Initialize();
    wargv[0] = get_bundle_dir();
    for (i = 1; i < argc; ++i) {
	if (strncmp(argv[i], "-psn", 4) == 0) {
	    int j;
	    for (j = i; j < argc; ++j)
		argv[j] = argv[j+1];
	    --argc;
	}
	wargv[i] = widen_c_string(argv[i]);
    }
    PySys_SetArgvEx(argc, wargv, 0);
    retval = PyRun_SimpleFile(fd, "");
    if (retval != 0)
	printf ("Run Simple File returned %d\n", retval);
    Py_Finalize();
    fclose(fd);
    for (i = 0; i < argc; ++i)
	free(wargv[i]);
    free(wargv);
    return 0;
}
