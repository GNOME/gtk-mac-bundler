import sys
import os, errno, glob
import shutil
import re
from plistlib import Plist
from .project import *
from . import utils

class Bundler:
    def __init__(self, project):
        self.project = project

        self.project_dir = project.get_project_dir()

        plist_path = self.project.get_plist_path()
        self.plist = Plist.fromFile(plist_path)

        # List of paths that should be recursively searched for
        # binaries that are used to find library dependencies.
        self.binary_paths = []
        #List of frameworks moved into the bundle which need to be set
        #up for private use.
        self.frameworks = []

        # Create the bundle in a temporary location first and move it
        # to the final destination when done.
        self.meta = project.get_meta()
        self.bundle_path = os.path.join(self.meta.dest, "." + project.get_bundle_name() + ".app")

    def recursive_rm(self, dirname):
        # Extra safety ;)
        if dirname in [ "/", os.getenv("HOME"), os.path.join(os.getenv("HOME"), "Desktop"), self.meta.dest ]:
            print("Eek, trying to remove a bit much, eh? (%s)" % (dirname))
            sys.exit(1)

        if not os.path.exists(dirname):
            return

        files = os.listdir(dirname)
        for file in files:
            path = os.path.join (dirname, file)
            if os.path.isdir(path):
                self.recursive_rm(path)
            else:
                retval = os.unlink(path)
        if (os.path.islink(dirname)):
            os.unlink(dirname)
        else:
            os.rmdir(dirname)

    def create_skeleton(self):
        utils.makedirs(self.project.get_bundle_path("Contents/Resources"))
        utils.makedirs(self.project.get_bundle_path("Contents/MacOS"))

    def create_pkglist(self):
        path = self.project.get_bundle_path("Contents", "PkgInfo")
        path = self.project.evaluate_path(path)
        f = open (path, "w")
        f.write(self.plist.CFBundlePackageType)
        f.write(self.plist.CFBundleSignature)
        f.close()

    def copy_plist(self):
        path = Path(self.project.get_plist_path(),
                    self.project.get_bundle_path("Contents/Info.plist"))
        path.copy_target(self.project)

    def create_pango_setup(self):
        if utils.has_pkgconfig_module("pango") and \
                not utils.has_pkgconfig_variable("pango", "pango_module_version"):
            # Newer pango (>= 1.38) no longer has modules, skip this
            # step in that case.
            return

        # Create a temporary pangorc file just for creating the
        # modules file with the right modules.
        module_version = utils.evaluate_pkgconfig_variables("${pkg:pango:pango_module_version}")
        modulespath = self.project.get_bundle_path("Contents/Resources/lib/pango/" +
                                                   module_version +
                                                   "/modules/")

        from distutils.version import StrictVersion as V
        import tempfile

        fd, tmp_filename = tempfile.mkstemp()
        f = os.fdopen(fd, "w")
        f.write("[Pango]\n")
        f.write("ModulesPath=" + modulespath)
        f.write("\n")
        f.close()

        cmd = "PANGO_RC_FILE=" + tmp_filename + " pango-querymodules"
        f = os.popen(cmd)

        path = self.project.get_bundle_path("Contents/Resources/etc/pango")
        utils.makedirs(path)
        fout = open(os.path.join(path, "pango.modules"), "w")

        if V(module_version) < V('1.8.0'):
            prefix_path  = os.path.join("Contents", "Resources")
        else:
            prefix_path = os.path.join("Contents", "Resources", "lib", "pango",
                                       module_version, "modules/")

        prefix = self.project.get_bundle_path(prefix_path)

        for line in f:
            line = line.strip()
            if line.startswith("# ModulesPath"):
                continue

            # Replace the hardcoded bundle path with @executable_path...
            if line.startswith(prefix):
                line = line[len(prefix):]
#Newer versions of pango have been modified to look in the right place
#for modules (providing the PANGO_LIB_DIR is set to point to the
#bundle_lib folder).
                if V(module_version) < V('1.8.0'):
                    line = "@executable_path/../Resources" + line

            fout.write(line)
            fout.write("\n")
        fout.close()

        os.unlink(tmp_filename)

        # Create the final pangorc file
        path = self.project.get_bundle_path("Contents/Resources/etc/pango")
        utils.makedirs(path)
        f = open(os.path.join(path, "pangorc"), "w")
        f.write("[Pango]\n")
#Pango 2.32 (corresponding to module_version 1.8.0) and later don't
#interpret "./" to mean the same directory that the rc file is in, so
#this doesn't work any more. However, pango does know to look in the
#bundle directory (when given the right environment variable), so we
#don't need this, either.
        if V(module_version) < V('1.8.0'):
            f.write("ModuleFiles=./pango.modules\n")
        f.close()

    def create_gtk_immodules_setup(self):
        path = self.project.get_bundle_path("Contents/Resources")
        cmd = "GTK_EXE_PREFIX=" + path + " gtk-query-immodules-" + self.project.get_gtk_version()
        f = os.popen(cmd)

        path = self.project.get_bundle_path("Contents/Resources/etc/",
                                            self.project.get_gtk_dir())
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
        modulespath = ""
        cachepath = ""
        if os.path.exists(os.path.join(self.project.get_prefix(), "lib",
                                       "gdk-pixbuf-2.0")):

            modulespath = self.project.get_bundle_path("Contents/Resources/lib/",
                                                     "gdk-pixbuf-2.0",
                                                     "${pkg:gdk-pixbuf-2.0:gdk_pixbuf_binary_version}",
                                                     "loaders")
            cachepath = self.project.get_bundle_path("Contents/Resources/lib/",
                                                     "gdk-pixbuf-2.0",
                                                     "${pkg:gdk-pixbuf-2.0:gdk_pixbuf_binary_version}",
                                                     "loaders.cache")
        elif os.path.exists(os.path.join(self.project.get_prefix(), "lib",
                                       "gdk-pixbuf-3.0")):
            modulespath = self.project.get_bundle_path("Contents/Resources/lib/",
                                                     "gdk-pixbuf-3.0",
                                                     "${pkg:gdk-pixbuf-3.0:gdk_pixbuf_binary_version}",
                                                     "loaders")
            cachepath = self.project.get_bundle_path("Contents/Resources/lib/",
                                                     "gdk-pixbuf-3.0",
                                                     "${pkg:gdk-pixbuf-3.0:gdk_pixbuf_binary_version}",
                                                     "loaders.cache")
        else:
            modulespath = self.project.get_bundle_path("Contents/Resources/lib/",
                                                       self.project.get_gtk_dir(),
                                                       "${pkg:" + self.meta.gtk + ":gtk_binary_version}",
                                                       "loaders")
            cachepath = self.project.get_bundle_path("Contents/Resources/etc/",
                                                     self.project.get_gtk_dir(),
                                                     "gdk-pixbuf.loaders")

        modulespath = utils.evaluate_pkgconfig_variables (modulespath)
        cachepath = utils.evaluate_pkgconfig_variables (cachepath)

        cmd = "GDK_PIXBUF_MODULEDIR=" + modulespath + " gdk-pixbuf-query-loaders"
        f = os.popen(cmd)

        utils.makedirs(os.path.dirname(cachepath))
        fout = open(cachepath, "w")

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
            if os.path.islink(path.source):
                continue
            dest = path.copy_target(self.project)

            self.binary_paths.append(dest)

            # Clean up duplicates
            self.binary_paths = list(set(self.binary_paths))

            # Clean out any libtool (*.la) files and static libraries
            if os.path.isdir(dest):
                for root, dirs, files in os.walk(dest):
                    for name in [l for l in files if l.endswith(".la") or l.endswith(".a")]:
                        os.remove(os.path.join(root, name))

    # Lists all the binaries copied in so far. Used in the library
    # dependency resolution and icon theme lookup.
    def list_copied_binaries(self):
        def filter_path(path):
            if os.path.islink(path):
                return False
            if path.endswith(".so") or path.endswith(".dylib") or os.access(path, os.X_OK):
                return True
            return False
        paths = []
        for path in self.binary_paths:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    paths.extend([os.path.join(root, l) for l in files])
            else:
                paths.append(path)

        paths = list(filter(filter_path, paths))
        return list(set(paths))

    def resolve_library_dependencies(self):
        # Get the libraries we link to, filter out anything that
        # doesn't come from any of the prefixes we have declared. Then
        # copy in the resulting list, and repeat until the list
        # doesn't change. At that point, all dependencies are
        # resolved.
        n_iterations = 0
        n_paths = 0
        paths = self.list_copied_binaries()

        def relative_path_map(line):
            if not os.path.isabs(line):
                for prefix in list(prefixes.values()):
                    path = os.path.join(prefix, "lib", line)
                    if os.path.exists(path):
                        return path
                print("Cannot find a matching prefix for %s" % (line))
            return line

        def prefix_filter(line):
            if not "(compatibility" in line:
                # print "Removed %s" % line
                return False

            if line.startswith("/usr/X11"):
                print("Warning, found X11 library dependency, you most likely don't want that:", line.strip().split()[0])

            if os.path.isabs(line):
                for prefix in list(prefixes.values()):
                    if prefix in line:
                        return True

                if not line.startswith("/usr/lib") and not line.startswith("/System/Library"):
                    print("Warning, library not available in any prefix:",
                          line.strip().split()[0])

                return False

            return True

        while n_paths != len(paths):
            cmds = [ "otool -L " ]
            for path in paths:
                cmds.append(path + " ")

            cmd = ''.join(cmds)
            f = os.popen(cmd)

            prefixes = self.meta.prefixes
            lines = list(filter(prefix_filter, [line.strip() for line in f]))
            p = re.compile("(.*\.dylib\.?.*)\s\(compatibility.*$")
            lines = utils.filterlines(p, lines)
            lines = list(map(relative_path_map, lines))
            new_libraries = []
            for library in set(lines):
                # Replace the real path with the right prefix so we can
                # create a Path object.
                for (key, value) in list(prefixes.items()):
                    if library.startswith(value):
                        path = Path("${prefix:" + key + "}" + library[len(value):])
                        new_libraries.append(path)

            n_paths = len(paths)
            n_iterations += 1
            if n_iterations > 10:
                print("Too many tries to resolve library dependencies")
                sys.exit(1)

            self.copy_binaries(new_libraries)
            paths = self.list_copied_binaries()

    def run_install_name_tool(self):
        print("Running install name tool")

        paths = self.list_copied_binaries()
        prefixes = self.meta.prefixes

        # First change all references in libraries.
        for prefix in prefixes:
            prefix_path = self.project.get_prefix(prefix)
            print("Going through prefix: " + prefix_path)
            for path in paths:
                cmd = os.path.join(os.path.dirname(__file__), "run-install-name-tool-change.sh") + " " + path + " " + prefix_path + " Resources" + " change"
                f = os.popen(cmd)
                for line in f:
                    print(line)

        # Then change the id of all libraries. Skipping this part for now
        #for path in paths:
        #    cmd = os.path.join(os.path.dirname(__file__), "run-install-name-tool-id.sh") + " " + path
        #    print cmd
        #    f = os.popen(cmd)
        #    for line in f:
        #        print line

        for framework in self.frameworks:
            fw_name, ext = os.path.splitext(os.path.basename(framework))
            fwl = os.path.join(framework, fw_name)
            print("Importing Framework: " + fwl)
# Fix the framework IDs
            cmd = os.path.join(os.path.dirname(__file__), "run-install-name-tool-change.sh") + " " + fwl + " " + fw_name + " Frameworks" + " id"
            f = os.popen(cmd)
            for line in f:
                print(line)
# Fix the dependencies in other libraries
            for path in paths:
                cmd = os.path.join(os.path.dirname(__file__), "run-install-name-tool-change.sh") + " " + path + " " + fw_name + " Frameworks/" + fw_name + " change"
                f = os.popen(cmd)
                for line in f:
                    print(line)
#fix the dependencies in frameworks
            for ufw in self.frameworks:
                ufw_name, ext = os.path.splitext(os.path.basename(ufw))
                if ufw_name == fw_name:
                    continue
                ufwl = os.path.join(ufw, ufw_name)
                cmd = os.path.join(os.path.dirname(__file__), "run-install-name-tool-change.sh") + " " + ufwl + " " + fw_name + " Frameworks/" + fw_name + " change"
                f = os.popen(cmd)
                for line in f:
                    print(line)


    def strip_debugging(self):
        paths = self.list_copied_binaries()
        for path in paths:
            if path.endswith(".dylib") or path.endswith(".so"):
                os.chmod(path, 0o644)
                os.system("strip -x " + path + " 2>/dev/null")
                os.chmod(path, 0o444)
            else:
                os.chmod(path, 0o755)
                os.system("strip -ur " + path + " 2>/dev/null")
                os.chmod(path, 0o555)

#
# If you want to sign your application, set $APPLICATION_CERT with the
# appropriate certificate name in your default Keychain. This function
# will sign every binary in the bundle with the certificate and the
# bundle's id string.
#
    def sign_binaries(self):
        if "APPLICATION_CERT" not in os.environ:
            return
        cert = os.getenv("APPLICATION_CERT")
        paths = self.list_copied_binaries()
        ident = self.project.get_bundle_id()
        paths.sort(reverse=True)
        for path in paths:
            cmdargs = ['codesign', '-s', cert, '-i', ident, path]
            result = os.spawnvp(os.P_WAIT, 'codesign', cmdargs)

            if result:
                raise OSError('"' + " ".join(cmdargs) + '" failed %d' % result)

    def copy_icon_themes(self):
        all_icons = set()

        themes = self.project.get_icon_themes()

        for theme in themes:
            theme.copy_target
            all_icons |= theme.enumerate_icons(self.project)

        strings = set()

        # Get strings from binaries.
        for f in self.list_copied_binaries():
            p = os.popen("strings " + f)
            for string in p:
                string = string.strip()
                strings.add(string)

        # FIXME: Also get strings from glade files.

        used_icons = all_icons.intersection(strings)
        for theme in themes:
            theme.copy_icons(self.project, used_icons)

    def copy_translations(self):
        translations = self.project.get_translations()
        prefix = self.project.get_prefix()


        def name_filter(filename):
            path, fname = os.path.split(filename)
            name, ext = os.path.splitext(fname)
            if name != program.name:
                return False
            elif ext not in (".mo", ".po"):
                return False
            else:
                return True

        for program in translations:
            if program.name == "" or program.name == None:
                raise "No program name to tranlate!"

            source = self.project.evaluate_path(program.source)
            if source == None:
                raise "Failed to parse translation source!"
            for root, trees, files in os.walk(source):
                for file in filter(name_filter, files):
                    path = os.path.join(root, file)
                    Path("${prefix}" + path[len(prefix):], program.dest).copy_target(self.project)


    def install_gir(self):
        gir_files = self.project.get_gir()
        bundle_gir_dir = self.project.get_bundle_path('Contents', 'Resources',
                                                      'share', 'gir-1.0')
        bundle_typelib_dir = self.project.get_bundle_path('Contents', 'Resources',
                                                          'lib', 'girepository-1.0')
        old_lib_path = os.path.join(self.project.get_prefix(), 'lib')
        os.makedirs(bundle_gir_dir)
        os.makedirs(bundle_typelib_dir)
        import subprocess

        def transform_file(filename):
            path, fname = os.path.split(filename)
            name, ext = os.path.splitext(fname)

            with open (filename, "r") as source:
                lines = source.readlines()
            newpath = os.path.join(bundle_gir_dir, fname)
            typelib = os.path.join(bundle_typelib_dir, name + '.typelib')
            with open (newpath, "w") as target:
                for line in lines:
                    target.write(re.sub(old_lib_path,
                                        '@executable_path/../Resources/lib',
                                        line))
            subprocess.call(['g-ir-compiler', '--output=' + typelib, newpath])
            self.binary_paths.append(typelib)

        for gir in gir_files:
            filename = self.project.evaluate_path(gir.source)
            for globbed_source in glob.glob(filename):
                try:
                    transform_file(globbed_source)
                except Exception as err:
                    print('Error in transformation of %s: %s' % (globbed_source, err))

    def run(self):
        # Remove the temp location forcefully.
        path = self.project.evaluate_path(self.bundle_path)
        self.recursive_rm(path)

        final_path = os.path.join(self.meta.dest, self.project.get_bundle_name() + ".app")
        final_path = self.project.evaluate_path(final_path)

        if not self.meta.overwrite and os.path.exists(final_path):
            print("Bundle already exists: " + final_path)
            sys.exit(1)

        self.create_skeleton()
        self.create_pkglist()
        self.copy_plist()

        # Note: could move this to xml file...
        Path("${prefix}/lib/charset.alias").copy_target(self.project)

        # Main binary
        path = self.project.get_main_binary()
        source = self.project.evaluate_path(path.source)
        if not os.path.exists(source):
            print("Cannot find main binary: " + source)
            sys.exit(1)

        dest = path.copy_target(self.project)
        self.binary_paths.append(dest)

        # Additional binaries (executables, libraries, modules)
        self.copy_binaries(self.project.get_binaries())
        self.resolve_library_dependencies()

        # Gir and Typelibs
        self.install_gir()

        # Data
        for path in self.project.get_data():
            path.copy_target(self.project)

        # Translations
        self.copy_translations()

        # Frameworks
        frameworks = self.project.get_frameworks()
        for path in frameworks:
            dest = path.copy_target(self.project)
            self.frameworks.append(dest)

        self.copy_icon_themes()

        self.create_pango_setup()
        self.create_gtk_immodules_setup()
        self.create_gdk_pixbuf_loaders_setup()

        if self.meta.run_install_name_tool:
            self.run_install_name_tool()

        #self.strip_debugging()

        self.sign_binaries()

        # Launcher script, if necessary.
        launcher_script = self.project.get_launcher_script()
        if launcher_script:
            path = launcher_script.copy_target(self.project)
            if "APPLICATION_CERT" in os.environ:
                cert = os.environ["APPLICATION_CERT"]
                ident = self.project.get_bundle_id()
                cmdargs = ['codesign', '-s', cert, '-i', ident, "-f", path]
                result = os.spawnvp(os.P_WAIT, 'codesign', cmdargs)
                if result:
                    raise OSError('"'+ " ".join(cmdargs) + '" failed %d' % result)
        if self.meta.overwrite:
            self.recursive_rm(final_path)
        shutil.move(self.project.get_bundle_path(), final_path)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: %s <bundle descriptopn file>" % (sys.argv[0]))
        sys.exit(2)

    if not os.path.exists(sys.argv[1]):
        print("File %s does not exist" % (sys.argv[1]))
        sys.exit(2)

    project = Project(sys.argv[1])
    bundler = Bundler(project)

    bundler.run()
