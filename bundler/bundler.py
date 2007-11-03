import sys
import os, errno, glob
import dircache, shutil
import re
from plistlib import Plist
from sets import Set
from distutils import dir_util

from project import *
import utils

class Bundler:
    def __init__(self, project):
        self.project = project

        self.project_dir = project.get_project_dir()

        plist_path = self.project.get_plist_path()
        self.plist = Plist.fromFile(plist_path)

        # List of paths that should be recursively searched for
        # binaries that are used to find library dependencies.
        self.binary_paths = []

        # Create the bundle in a temporary location first and move it
        # to the final destination when done.
        dest = project.get_meta().dest
        self.bundle_path = os.path.join(dest, "." + project.get_name() + ".app")

    def recursive_rm(self, dirname):
        # Extra safety ;)
        if dirname in [ "/", os.getenv("HOME"), os.path.join(os.getenv("HOME"), "Desktop") ]:
            raise "Eek, trying to remove a bit much, eh? (%s)" % (dirname)

        if not os.path.exists(dirname):
            return
        
        files = dircache.listdir(dirname)
        for file in files:
            path = os.path.join (dirname, file)
            if os.path.isdir(path):
                self.recursive_rm(path)
            else:
                retval = os.unlink(path)

        os.rmdir(dirname)

    def create_skeleton(self):
        utils.makedirs(self.project.get_bundle_path("Contents/Resources"))
        utils.makedirs(self.project.get_bundle_path("Contents/MacOS"))

    def create_pkglist(self):
        path = self.project.get_bundle_path("Contents", "PkgInfo")
        path = self.project.evaluate_path(path)
        f = open (path, "w")
        f.write(self.plist.CFBundleSignature)
        f.close()

    def copy_plist(self):
        path = Path(self.project.get_plist_path(),
                    self.project.get_bundle_path("Contents"))
        self.copy_path(path)

    def create_pango_setup(self):
        # Create a temporary pangorc file just for creating the
        # modules file with the right modules.
        modulespath = self.project.get_bundle_path("Contents/Resources/lib/pango/" +
                                                   "${pkg:pango:pango_module_version}/"+
                                                   "modules")

        import tempfile
        fd, tmp_filename = tempfile.mkstemp()
        f = os.fdopen(fd, "w")
        f.write("[Pango]\n")
        f.write("ModulesPath=" + utils.evaluate_pkgconfig_variables (modulespath))
        f.write("\n")
        f.close()

        cmd = "PANGO_RC_FILE=" + tmp_filename + " pango-querymodules"
        f = os.popen(cmd)

        path = self.project.get_bundle_path("Contents/Resources/etc/pango")
        utils.makedirs(path)
        fout = open(os.path.join(path, "pango.modules"), "w")

        prefix = self.project.get_bundle_path("Contents/Resources")

        for line in f:
            line = line.strip()
            if line.startswith("#"):
                continue

            # Replace the hardcoded bundle path with @executable_path...
            if line.startswith(prefix):
                line = line[len(prefix):]
                line = "@executable_path/../Resources" + line

            fout.write(line)
        fout.close()

        os.unlink(tmp_filename)

        # Create the final pangorc file
        path = self.project.get_bundle_path("Contents/Resources/etc/pango")
        utils.makedirs(path)
        f = open(os.path.join(path, "pangorc"), "w")
        f.write("[Pango]\n")
        f.write("ModuleFiles=./pango.modules\n")
        f.close()

    def create_gtk_immodules_setup(self):
        path = self.project.get_bundle_path("Contents/Resources")
        cmd = "GTK_EXE_PREFIX=" + path + " gtk-query-immodules-2.0"
        f = os.popen(cmd)

        path = self.project.get_bundle_path("Contents/Resources/etc/gtk-2.0")
        utils.makedirs(path)
        fout = open(os.path.join(path, "gtk.immodules"), "w")

        prefix = "\"" + self.project.get_bundle_path("Contents/Resources")

        for line in f:
            line = line.strip()
            if line.startswith("#"):
                continue

            # Replace the hardcoded bundle path with @executable_path...
            if line.startswith(prefix):
                line = line[len(prefix):]
                line = "\"@executable_path/../Resources" + line
            fout.write(line)
            fout.write("\n")
        fout.close()

    def create_gdk_pixbuf_loaders_setup(self):
        modulespath = self.project.get_bundle_path("Contents/Resources/lib/gtk-2.0/" +
                                                   "${pkg:gtk+-2.0:gtk_binary_version}/"+
                                                   "loaders")
        cmd = "GDK_PIXBUF_MODULEDIR=" + modulespath + " gdk-pixbuf-query-loaders"
        f = os.popen(cmd)

        path = self.project.get_bundle_path("Contents/Resources/etc/gtk-2.0")
        utils.makedirs(path)
        fout = open(os.path.join(path, "gdk-pixbuf.loaders"), "w")

        prefix = "\"" + self.project.get_bundle_path("Contents/Resources")

        for line in f:
            line = line.strip()
            if line.startswith("#"):
                continue

            # Replace the hardcoded bundle path with @executable_path...
            if line.startswith(prefix):
                line = line[len(prefix):]
                line = "\"@executable_path/../Resources" + line
            fout.write(line)
            fout.write("\n")
        fout.close()

    def copy_binaries(self, binaries):
        for path in binaries:
            dest = self.copy_path(path)

            self.binary_paths.append(dest)

            # Clean up duplicates
            self.binary_paths = list(Set(self.binary_paths))

            # Clean out any libtool (*.la) files and static
            # libraries
            if os.path.isdir(dest):
                for root, dirs, files in os.walk(dest):
                    for name in filter(lambda l: l.endswith(".la") or l.endswith(".a"), files):
                        os.remove(os.path.join(root, name))

    # Copies from Path.source to Path.dest, evaluating any variables
    # in the paths, and returns the real dest.
    def copy_path(self, Path):
        source = self.project.evaluate_path(Path.source)

        if Path.dest:
            dest = self.project.evaluate_path(Path.dest)
        else:
            # Source must begin with a prefix if we don't have a
            # dest. Skip past the source prefix and replace it with
            # the right bundle path instead.
            p = re.compile("^\${prefix(:.*?)?}/")
            m = p.match(Path.source)
            if m:
                relative_dest = self.project.evaluate_path(Path.source[m.end():])
                dest = self.project.get_bundle_path("Contents/Resources", relative_dest)
            else:
                raise "Invalid project file, missing 'dest' property"

        (parent, tail) = os.path.split(dest)
        utils.makedirs(parent)

        for globbed_source in glob.glob(source):
            try:
                if os.path.isdir(globbed_source):
                    #print "dir: %s => %s" % (globbed_source, dest)
                    dir_util.copy_tree (str(globbed_source), str(dest),
                                        preserve_mode=1,
                                        preserve_times=1,
                                        preserve_symlinks=1,
                                        update=1,
                                        verbose=1,
                                        dry_run=0)
                else:
                    #print "file: %s => %s" % (globbed_source, dest)
                    shutil.copy(globbed_source, dest)
            except EnvironmentError, e:
                if e.errno == errno.ENOENT:
                    print "Warning, source file missing: " + globbed_source
                elif e.errno == errno.EEXIST:
                    print "Warning, path already exits: " + dest
                else:
                    raise

        return dest

    # Lists all the binaries copied in so far. Used in the library
    # dependency resolution.
    def list_copied_binaries(self):
        paths = []
        for path in self.binary_paths:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    paths.extend(map(lambda l: os.path.join(root, l), files))
            else:
                paths.append(path)

        # FIXME: Should filter this list so it only contains .so,
        # .dylib, and executable binaries.
        #return filter(lambda l: l.endswith(".so") or l.endswith(".dylib") or os.access(l, os.X_OK), paths)
        return paths

    def resolve_library_dependencies(self):
        # Get the libraries we link to, filter out anything that
        # doesn't come from any of the prefixes we have declared. Then
        # copy in the resulting list, and repeat until the list
        # doesn't change. At that point, all dependencies are
        # resolved.
        n_iterations = 0
        n_paths = 0
        paths = self.list_copied_binaries()
        while n_paths != len(paths):
            cmds = [ "otool -L " ]
            for path in paths:
                cmds.append(path + " ")

            cmd = ''.join(cmds)
            f = os.popen(cmd)

            prefixes = self.project.get_meta().prefixes

            def prefix_filter(line):
                if not "(compatibility" in line:
                    return False
                for prefix in prefixes.values():
                    if prefix in line:
                        return True

                # Warn about any unresolved dependencies that are not
                # part of the system.
                if not line.startswith("/usr/lib") and not line.startswith("/System/Library"):
                    print "Warning, library not available in any prefix:", line.strip().split()[0]

                return False

            lines = filter(prefix_filter, [line.strip() for line in f])

            p = re.compile("(.*.dylib)\s\(compatibility.*$")
            lines = map(lambda line: p.match(line).group(1), lines)

            new_libraries = []
            for library in Set(lines):
                # Replace the real path with the right prefix so we can
                # create a Path object.
                for (key, value) in prefixes.items():
                    if library.startswith(value):
                        path = Path("${prefix:" + key + "}" + library[len(value):])
                        new_libraries.append(path)

            n_paths = len(paths)
            n_iterations += 1
            if n_iterations > 10:
                raise Exception("Too many tries to resolve library dependencies")
            
            self.copy_binaries(new_libraries)
            paths = self.list_copied_binaries()

    def copy_icon_themes(self):
        all_icons = Set()

        themes = self.project.get_icon_themes()

        for theme in themes:
            self.copy_path(Path(os.path.join(theme.source, "index.theme")))

        for theme in themes:
            if theme.icons == IconTheme.ICONS_NONE:
                continue
            
            for root, dirs, files in os.walk(self.project.evaluate_path(theme.source)):
                for f in files:
                    (head, tail) = os.path.splitext(f)
                    if tail in [".png", ".svg"]:
                        all_icons.add(head)

        strings = Set()

        for f in self.list_copied_binaries():
            p = os.popen("strings " + f)
            for string in p:
                string = string.strip()
                strings.add(string)

        used_icons = all_icons.intersection(strings)
        prefix = self.project.get_prefix()

        for theme in themes:
            if theme.icons == IconTheme.ICONS_NONE:
                continue

            for root, dirs, files in os.walk(self.project.evaluate_path(theme.source)):
                for f in files:
                    # Go through every file, if it matches the icon
                    # set, copy it.
                    (head, tail) = os.path.splitext(f)
                    if head in used_icons or theme.icons == IconTheme.ICONS_ALL:
                        path = os.path.join(root, f)

                        # Replace the real paths with the prefix macro
                        # so we can use copy_path.
                        self.copy_path(Path("${prefix}" + path[len(prefix):]))

        # Generate icon caches.
        for theme in themes:
            path = self.project.get_bundle_path("Contents/Resources/share/icons", theme.name)
            cmd = "gtk-update-icon-cache -f " + path + " 2>/dev/null"
            os.popen(cmd)

    # FIXME: Do this in project.py instead.
    def check(self):
        # Check that the executable exists
        # - and is executable
        # - and not a libtool script
        return True

    def run(self):
        # Remove the temp location forcefully.
        self.recursive_rm(self.bundle_path)

        meta = self.project.get_meta()

        final_path = os.path.join(meta.dest, self.project.get_name() + ".app")
        final_path = self.project.evaluate_path(final_path)

        if not meta.overwrite and os.path.exists(final_path):
            print "Bundle already exists: " % (final_path)
            return

        self.create_skeleton()
        self.create_pkglist()
        self.copy_plist()

        # Note: could move this to xml file...
        self.copy_path(Path("${prefix}/lib/charset.alias"))

        # Data
        for path in self.project.get_data():
            self.copy_path(path)

        # Launcher script, if necessary.
        launcher_script = self.project.get_launcher_script()
        if launcher_script:
            self.copy_path(launcher_script)

        # Main binary
        dest = self.copy_path(self.project.get_main_binary())
        self.binary_paths.append(dest)

        # Additional binaries (executables, libraries, modules)
        self.copy_binaries(self.project.get_binaries())
        self.resolve_library_dependencies()

        self.create_pango_setup()
        self.create_gtk_immodules_setup()
        self.create_gdk_pixbuf_loaders_setup()

        self.copy_icon_themes()

        if meta.overwrite:
            self.recursive_rm(final_path)
        shutil.move(self.project.get_bundle_path(), final_path)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "Usage: %s <bundle descriptopn file>" % (sys.argv[0])
        sys.exit(2)

    if not os.path.exists(sys.argv[1]):
        print "File %s does not exist" % (sys.argv[1])
        sys.exit(2)

    project = Project(sys.argv[1])
    bundler = Bundler(project)

    bundler.run()
