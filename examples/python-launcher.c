/* python-launcher.c
 * Launch a python interpreter to run a bundled python application.
 *
 * Copyright 2016       John Ralls <jralls@ceridwen.us>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

#include <Python.h>
#include <CoreFoundation/CoreFoundation.h>
#include <sys/syslimits.h>

#define PYLIB "/lib/python3.13"

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

static inline void
check_status(PyConfig* config, PyStatus status)
{
  if (PyStatus_Exception(status))
    {
      if (config)
        PyConfig_Clear(config);
      Py_ExitStatusException(status);
    }
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
set_python_path(PyConfig *config)
{
    CFBundleRef bundle = CFBundleGetMainBundle();
    CFURLRef bundle_url = CFBundleCopyResourcesDirectoryURL(bundle);
    CFMutableStringRef mstr;
    wchar_t *path;
    CFStringRef str = make_filesystem_string(bundle_url);
    CFIndex base_length, curr_length;

    CFRelease(bundle_url);
    path = widen_cfstring(str);
    check_status(config, PyConfig_SetString(config, &config->home, path));
    free(path);
    mstr = CFStringCreateMutableCopy(NULL, PATH_MAX, str);
    CFRelease(str);
    CFStringAppendCString(mstr, PYLIB,
                          kCFStringEncodingUTF8);
    base_length = CFStringGetLength(mstr);
    path = widen_cfstring(mstr);
    check_status(config, PyWideStringList_Insert(&config->module_search_paths, 0, path));
    free (path);
    CFStringAppendCString(mstr, "/lib-dynload",
                          kCFStringEncodingUTF8);
    path = widen_cfstring(mstr);
    check_status(config, PyWideStringList_Insert(&config->module_search_paths, 1, path));
    free (path);
    curr_length = CFStringGetLength(mstr);
    CFStringDelete(mstr, CFRangeMake(base_length, curr_length - base_length));
    CFStringAppendCString(mstr, "/site-packages",
                          kCFStringEncodingUTF8);
    path = widen_cfstring(mstr);
    CFRelease(mstr);
    check_status(config, PyWideStringList_Insert(&config->module_search_paths, 2, path));
    free (path);
    config->module_search_paths_set = 1;
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

static void
set_command_args(PyConfig* config, int argc, char **argv)
{
  wchar_t *wargv;
  wargv = get_bundle_dir();
  check_status(config, PyWideStringList_Insert(&config->argv, 0, wargv));
  free(wargv);
  for (int i = 1; i < argc; ++i)
    {
      if (strncmp(argv[i], "-psn", 4) == 0)
        {
          for (int j = i; j < argc; ++j)
            argv[j] = argv[j+1];
          --argc;
        }
      wargv = widen_c_string(argv[i]);
      check_status(config, PyWideStringList_Insert(&config->argv, i, wargv));
      free (wargv);
    }
  config->parse_argv = 0;
}

int
main(int argc, char *argv[])
{
  int retval = 0;
  FILE *fd = open_scriptfile();
  PyConfig config;

  if (fd == NULL)
    {
      return -1;
    }

  PyConfig_InitPythonConfig(&config);
  set_python_path(&config);
  config.optimization_level = 1;
  set_command_args(&config, argc, argv);
  check_status(&config, Py_InitializeFromConfig(&config));
  retval = PyRun_SimpleFile(fd, "");
  if (retval != 0)
    printf ("Run Simple File returned %d\n", retval);
  Py_Finalize();
  fclose(fd);
  return 0;
}
