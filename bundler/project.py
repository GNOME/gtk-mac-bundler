import errno
import sys
import re
import os
import glob
import shutil
import xml.dom.minidom
from xml.dom.minidom import Node
from plistlib import Plist
from . import utils
from distutils import dir_util, file_util

# Base class for anything that can be copied into a bundle with a
# source and dest.
class Path(object):
    def __init__(self, source, dest=None, recurse=False):
        if source and len(source) == 0:
            source = None
        if dest and len(dest) == 0:
            dest = None

        if source and os.path.isabs(source):
            source = os.path.normpath(source)
        if dest and os.path.isabs(dest):
            dest = os.path.normpath(dest)

        self.source = source
        self.dest = dest
        self.recurse = recurse

    @classmethod
    def from_node(cls, node, validate=True):
        source = utils.node_get_string(node)
        dest = node.getAttribute("dest")
        recurse = node.getAttribute("recurse")
        if len(dest) == 0:
            dest = None
        if recurse == "True":
            recurse = True
        else:
            recurse = False
        if validate:
            Path.validate(source, dest)

        if node.tagName == "framework":
            return Framework(source, recurse)
        if node.tagName == "binary" or node.tagName == "main-binary":
            return Binary(source, dest, recurse)
        if node.tagName == "translations":
            name = node.getAttribute('name')
            if len(name) == 0:
                raise "The tag 'translations' must have a 'name' property."
            return Translation(name, source, dest, recurse)
        if node.tagName == "gir":
            return GirFile(source, dest, recurse)

        return Path(source, dest, recurse)

    @classmethod
    def validate(cls, source, dest):
        if source and len(source) == 0:
            source = None
        if dest and len(dest) == 0:
            dest = None

        if not source or len(source) == 0:
            raise Exception("The source path cannot be empty")

        if source.startswith("${bundle}"):
            raise Exception("The source path cannot use a ${bundle} macro")

        if dest and dest.startswith("${prefix"):
            raise Exception("The destination path cannot use a ${prefix} macro")

        if not os.path.isabs(source):
            if not (source.startswith("${project}") or source.startswith("${env:") or \
                    source.startswith("${pkg:") or source.startswith("${prefix}") or \
                    source.startswith("${prefix:")):
                raise Exception("The source path must be absolute or use one of the "
                                "predefined macros ${project}, ${prefix}, ${prefix:*}, "
                                "${env:*}, or ${pkg:*:*}")

        if not source.startswith("${prefix") and os.path.isabs(source):
            if not dest:
                raise Exception("If the source doesn't use a ${prefix} or ${prefix:*} "
                                "macro, the destination path must be set " + dest)

        if not dest and not source.startswith("${prefix"):
            raise Exception("If the destination path is empty, the source must use "
                            "a ${prefix} or ${prefix:*} macro")

        if dest and len(dest) > 0 and not dest.startswith("${bundle}"):
            raise Exception("The destination path must start with ${bundle}")

        return True

    # Copies from source to dest, evaluating any variables
    # in the paths, and returns the real dest.
    def copy_target(self, project):
        source = project.evaluate_path(self.source)
        if self.dest:
            dest = project.evaluate_path(self.dest)
        else:
            # Source must begin with a prefix if we don't have a
            # dest. Skip past the source prefix and replace it with
            # the right bundle path instead.
            p = re.compile("^\${prefix(:.*?)?}/")
            m = p.match(self.source)
            if m:
                relative_dest = project.evaluate_path(self.source[m.end():])
                dest = project.get_bundle_path("Contents/Resources", relative_dest)
            else:
                print("Invalid bundle file, missing or invalid 'dest' property: " + self.dest)
                sys.exit(1)

        (dest_parent, dest_tail) = os.path.split(dest)
        utils.makedirs(dest_parent)

        # Check that the source only has wildcards in the last component.
        p = re.compile("[\*\?]")
        (source_parent, source_tail) = os.path.split(source)
        if p.search(source_parent):
            print("Can't have wildcards except in the last path component: " + source)
            sys.exit(1)

        if p.search(source_tail):
            source_check = source_parent
        else:
            source_check = source
        if not os.path.exists(source_check):
            print("Cannot find source to copy: " + source)
            sys.exit(1)

        # If the destination has a wildcard as last component (copied
        # from the source in dest-less paths), ignore the tail.
        if p.search(dest_tail):
            dest = dest_parent

        if self.recurse:
            for root, dirs, files in os.walk(source_parent):
                destdir = os.path.join(dest,
                                       os.path.relpath(root, source_parent))
                utils.makedirs(destdir)
                for globbed_source in glob.glob(os.path.join(root,
                                                             source_tail)):
                    try:
#                        print "Copying %s to %s" % (globbed_source, destdir)
                        shutil.copy(globbed_source, destdir)
                    except EnvironmentError as e:
                        if e.errno == errno.ENOENT:
                            print("Warning, source file missing: " + globbed_source)
                        elif e.errno == errno.EEXIST:
                            print("Warning, path already exits: " + dest)
                        else:
                            print("Error %s when copying file: %s" % ( str(e), globbed_source ))
                            sys.exit(1)

        else:
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
                        file_util.copy_file (str(globbed_source), str(dest),
                                            preserve_mode=1,
                                            preserve_times=1,
                                            update=1,
                                            link=None,
                                            verbose=1,
                                            dry_run=0)
                except EnvironmentError as e:
                    if e.errno == errno.ENOENT:
                        print("Warning, source file missing: " + globbed_source)
                    elif e.errno == errno.EEXIST:
                        print("Warning, path already exits: " + dest)
                    else:
                        print("Error %s when copying file: %s" %( str(e), globbed_source ))
                        sys.exit(1)
        return dest

# Used for anything that has a name and value.
class Variable:
    def __init__(self, node):
        self.name = node.getAttribute("name")
        self.value = utils.node_get_string(node)

class Environment:
    def __init__(self, node):
        self.runtime_variables = []
        self.scripts = []

        variables = utils.node_get_elements_by_tag_name(node, "runtime-variable")
        for child in variables:
            self.runtime_variables.append(Variable(child))

        scripts = utils.node_get_elements_by_tag_name(node, "script")
        for child in scripts:
            script = Path(utils.node_get_string(child), "${bundle}/Resources/Scripts")
            self.scripts.append(script)

class Meta:
    def __init__(self, node):
        self.prefixes = {}

        prefixes = utils.node_get_elements_by_tag_name(node, "prefix")
        for child in prefixes:
            name = child.getAttribute("name")
            if len(name) == 0:
                name = "default"
            value = utils.evaluate_environment_variables(utils.node_get_string(child))
            self.prefixes[name] = value

        child = utils.node_get_element_by_tag_name(node, "image")
        if child:
            pass # FIXME: implement

        child = utils.node_get_element_by_tag_name(node, "run-install-name-tool")
        if child:
            self.run_install_name_tool = True
        else:
            self.run_install_name_tool = False

        child = utils.node_get_element_by_tag_name(node, "destination")
        self.overwrite = utils.node_get_property_boolean(child, "overwrite", False)
        self.dest = utils.node_get_string(child, "${project}")

        child = utils.node_get_element_by_tag_name(node, "gtk")
        if child:
            self.gtk = utils.node_get_string(child)
        else:
            self.gtk = "gtk+-2.0"

class Framework(Path):
    def __init__(self, source, recurse):
        (head, tail) = os.path.split(source)
        dest = "${bundle}/Contents/Frameworks/" + tail
        super(Framework, self).__init__(source, dest, recurse);

class Binary(Path):
    def __init__(self, source, dest, recurse):
        super(Binary, self).__init__(source, dest, recurse)

class Translation(Path):
    def __init__(self, name, sourcepath, destpath, recurse):
        super(Translation, self).__init__(sourcepath, destpath, recurse)
        self.name = name

class GirFile(Path):
    def __init__(self, sourcepath, destpath, recurse):
        super(GirFile, self).__init__(sourcepath, destpath, recurse)

class Data(Path):
    pass

class IconTheme:
    ICONS_NONE, ICONS_ALL, ICONS_AUTO = list(range(3))

    def __init__(self, name, icons=ICONS_AUTO):
        self.name = name
        self.source = "${prefix}/share/icons/" + name

        self.icons = icons

    @classmethod
    def from_node(cls, node):
        name = utils.node_get_string(node)
        if not name:
            raise Exception("Icon theme must have a 'name' property")

        string = node.getAttribute("icons")
        if string == "all":
            icons = IconTheme.ICONS_ALL
        elif string == "none":
            icons = IconTheme.ICONS_NONE
        elif string == "auto" or len(string) == 0:
            icons = IconTheme.ICONS_AUTO

        return IconTheme(name, icons)

class Project:
    def __init__(self, project_path=None):
        if not os.path.isabs(project_path):
            project_path = os.path.join(os.getcwd(), project_path)
        self.project_path = project_path
        self.root = None

        if project_path and os.path.exists(project_path):
            try:
                doc = xml.dom.minidom.parse(project_path)
                # Get the first app-bundle tag and ignore any others.
                self.root = utils.node_get_element_by_tag_name(doc, "app-bundle")
            except:
                print("Could not load project %s:" % (project_path))
                raise

        # The directory the project file is in (as opposed to
        # project_path which is the path including the filename).
        self.project_dir, tail = os.path.split(project_path)
        self.meta = self.get_meta()

        plist_path = self.get_plist_path()
        try:
            plist = Plist.fromFile(plist_path)
        except EnvironmentError as e:
            if e.errno == errno.ENOENT:
                print("Info.plist file not found: " + plist_path)
                sys.exit(1)
            else:
                raise
        self.name = plist.CFBundleExecutable
        if "CFBundleName" in plist:
            self.bundle_name = plist.CFBundleName
        else:
            self.bundle_name = plist.CFBundleExecutable

        self.bundle_id = plist.CFBundleIdentifier

    """
     Replace ${env:?}, ${prefix}, ${prefix:?}, ${project}, ${gtk}, ${gtkdir},
     ${gtkversion}, ${pkg:?:?}, ${bundle}, and ${name} variables.
    """
    def evaluate_path(self, path, include_bundle=True):
        p = re.compile("^\${prefix}")
        path = p.sub(self.get_prefix(), path)

        p = re.compile("^\${prefix:(.*?)}")
        m = p.match(path)
        if m:
            path = p.sub(self.get_prefix(m.group(1)), path)

        p = re.compile("^\${project}")
        path = p.sub(self.project_dir, path)

        p = re.compile("\${gtk}")
        path = p.sub(self.meta.gtk, path)

        p = re.compile("\${gtkdir}")
        path = p.sub(self.get_gtk_dir(), path)

        p = re.compile("\${gtkversion}")
        path = p.sub(self.get_gtk_version(), path)

        try:
            p = re.compile("\${name}")
            path = p.sub(self.name, path)
        except AttributeError:
            pass # can be used before name path is set

        if include_bundle:
            try:
                p = re.compile("^\${bundle}")
                path = p.sub(self.get_bundle_path(), path)
            except AttributeError:
                pass # can be used before bundle path is set

        path = utils.evaluate_environment_variables(path)
        path = utils.evaluate_pkgconfig_variables(path)

        return os.path.normpath(path)

    def get_name(self):
        return self.name

    def get_bundle_name(self):
        return self.bundle_name

    def get_bundle_id(self):
        return self.bundle_id

    def get_prefix(self, name="default"):
        meta = self.get_meta()
        return meta.prefixes[name]

    def get_project_path(self):
        return self.project_path

    def get_project_dir(self):
        return self.project_dir

    def get_bundle_path(self, *args):
        dest = self.get_meta().dest
        bundle_path = os.path.join(dest, "." + self.get_name() + ".app")
        bundle_path = self.evaluate_path(bundle_path, False)
        return os.path.join(bundle_path, *args)

    def get_plist_path(self):
        plist = utils.node_get_element_by_tag_name(self.root, "plist")
        if not plist:
            raise Exception("The 'plist' tag is required")
        return  self.evaluate_path(utils.node_get_string(plist))

    def get_launcher_script(self):
        node = utils.node_get_element_by_tag_name(self.root, "launcher-script")
        if node:
            path = Path.from_node(node, False)
            if not path.source:
                # Use the default launcher.
                launcher = os.path.join(os.path.dirname(__file__),
                                        "launcher.sh")
                path = Path(launcher, "${bundle}/Contents/MacOS/${name}")
            else:
                path.dest = "${bundle}/Contents/MacOS/${name}"
            return path

        return None

    def get_icon_themes(self):
        themes = []

        nodes = utils.node_get_elements_by_tag_name(self.root, "icon-theme")
        for node in nodes:
            themes.append(IconTheme.from_node(node))

        # The hicolor theme is mandatory.
        if not [l for l in themes if l.name == "hicolor"]:
            themes.append(IconTheme("hicolor"))

        return themes

    def get_meta(self):
        node = utils.node_get_element_by_tag_name(self.root, "meta")
        return Meta(node)

    def get_gtk_version(self):
        if self.meta.gtk == "gtk+-3.0":
            return "3.0"
        else:
            return "2.0"

    def get_gtk_dir(self):
        if self.meta.gtk == "gtk+-3.0":
            return "gtk-3.0"
        else:
            return "gtk-2.0"

    def get_environment(self):
        node = utils.node_get_element_by_tag_name(self.root, "environment")
        return Environment(node)

    def get_frameworks(self):
        frameworks = []
        nodes = utils.node_get_elements_by_tag_name(self.root, "framework")
        for node in nodes:
            frameworks.append(Path.from_node(node))
        return frameworks

    def get_translations(self):
        translations = []
        nodes = utils.node_get_elements_by_tag_name(self.root, "translations")
        for node in nodes:
            translations.append(Path.from_node(node))
        return translations

    def get_gir(self):
        gir_files = []
        nodes = utils.node_get_elements_by_tag_name(self.root, "gir")
        for node in nodes:
            gir_files.append(Path.from_node(node))
        return gir_files

    def get_main_binary(self):
        node = utils.node_get_element_by_tag_name(self.root, "main-binary")
        if not node:
            raise Exception("The file has no <main-binary> tag")

        binary = Path.from_node(node)

        launcher = self.get_launcher_script()
        if launcher:
            suffix = "-bin"
        else:
            suffix = ""
        binary.dest = "${bundle}/Contents/MacOS/${name}" + suffix

        return binary

    def get_binaries(self):
        binaries = []
        nodes = utils.node_get_elements_by_tag_name(self.root, "binary")
        for node in nodes:
            binaries.append(Path.from_node(node))
        return binaries

    def get_data(self):
        data = []
        nodes = utils.node_get_elements_by_tag_name(self.root, "data")
        for node in nodes:
            data.append(Path.from_node(node))
        return data

if __name__ == '__main__':
    project = Project(os.path.join(os.getcwd(), 'giggle.bundle'))

    print("General:")
    print("  Project path: %s" % (project.get_project_path()))
    print("  Plist path: %s" % (project.get_plist_path()))
    print("  App name: %s" % (project.name))
    print("  Destination: %s" % (project.get_meta().dest))
    print("  Overwrite: %s" % (str(project.get_meta().overwrite)))

    environment = project.get_environment()
    print("Environment:")
    for variable in environment.runtime_variables:
        print("  %s=%s" % (variable.name, variable.value))
    for script in environment.scripts:
        print("  %s => %s" % (script.source, script.dest))

    print("Frameworks:")
    for framework in project.get_frameworks():
        print(" ", framework)

    print("Main binary:")
    binary = project.get_main_binary()
    print("  %s => %s" % (binary.source, binary.dest))

    print("Launcher:")
    launcher_script = project.get_launcher_script()
    print("  %s => %s" % (launcher_script.source, launcher_script.dest))

    print("Binaries:")
    for binary in project.get_binaries():
        print("  %s => %s" % (binary.source, binary.dest))
