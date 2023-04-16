import os
import errno
import sys
import unittest
import xml.dom.minidom
from plistlib import load as plist_load

from .project import Project
from . import utils

class Mock_Project(Project):

    def __init__(self, testxml, path):
        super().__init__(path)
        doc = xml.dom.minidom.parseString(testxml)
        self.root = utils.node_get_element_by_tag_name(doc, "app-bundle")
        assert self.root != None
        dir, tail = os.path.split(path)
        self.project_dir = os.path.join(os.getcwd(), dir)
        self.project_path = os.path.join(self.project_dir, tail)
        plist_path = os.path.join(self.project_dir, "test.plist")
        try:
            with open( plist_path, mode="rb") as fp:
                plist = plist_load(fp)
            self.name = plist['CFBundleExecutable']
        except EnvironmentError as e:
            if e.errno == errno.ENOENT:
                print("Info.plist file not found: " + plist_path)
                sys.exit(1)
            else:
                raise

class Project_Test(unittest.TestCase):

    def setUp(self):
        self.goodproject = Mock_Project(Project_Test.goodxml,
                                        Project_Test.goodpath)
        self.badproject = Mock_Project(Project_Test.badxml,
                                       Project_Test.badpath)

    def test_a_get_project_path(self):
        path = self.goodproject.get_project_path()
        self.failUnlessEqual(path, Project_Test.goodpath,
                             f'Project returned incorrect project path {path} wanted {Project_Test.goodpath}')
        path = self.badproject.get_project_path()
        self.failUnlessEqual(path, Project_Test.badpath,
                             f'Project returned incorrect bad project path {path}')

    def test_b_get_project_dir(self):
        dir = self.goodproject.get_project_dir()
        good_dir, tail = os.path.split(Project_Test.goodpath)
        self.failUnlessEqual(dir, good_dir,
                             f'Project returned incorrect project dir {dir}')

    def test_c_get_meta(self):
        node = self.goodproject.get_meta()
        self.failIfEqual(node, None, "Didn't find meta node in goodproject")
        self.assertRaises(Exception, self.badproject.get_meta())

    def test_d_get_prefix(self):
        try:
            pfx = self.goodproject.get_prefix()
        except KeyError:
            self.fail("Goodproject didn't set the default prefix")
        self.failUnlessEqual(pfx, os.getenv("JHBUILD_PREFIX",
                                            f'Default prefix {pfx}'))
        try:
            pfx = self.goodproject.get_prefix("alt")
        except KeyError:
            self.fail("Goodproject didn't set the alt prefix")
        self.failUnlessEqual(pfx, "/usr/local/gtk", f'Alternate prefix {pfx}')

    def test_e_get_plist_path(self):
        try:
            path = self.goodproject.get_plist_path()
        except KeyError:
            self.fail("Goodproject didn't set the default prefix")
        except Exception:
            self.fail("Goodproject didn't set the plist tag")
        dir, tail = os.path.split(Project_Test.goodpath)
        self.failUnlessEqual(path,
                             os.path.join(dir, "test.plist"),
                             f'Bad Plist Path {path}')

    def test_f_get_name(self):
        try:
            plist_path = self.goodproject.get_plist_path()
        except KeyError:
            self.fail("Goodproject didn't set the default prefix")
        try:
            with open(plist_path, "rb") as f:
                plist = plist_load(f)
            name = plist['CFBundleExecutable']
        except IOError:
            self.fail("Path problem " + plist_path)
        pname = self.goodproject.get_name()
        self.failUnlessEqual(pname, name, f'Bad Name {pname}')



#If get_name works, this will too.
    def test_g_get_bundle_path(self):
        pass

    def test_h_evaluate_path(self):
        try:
            path = self.goodproject.evaluate_path("${bundle}/Contents/MacOS/${name}")
        except KeyError:
            self.fail("Goodproject didn't set the default prefix")
        try:
            name = self.goodproject.get_bundle_path()
        except AttributeError:
            self.fail("Project didn't set the name attribute")
        self.failUnlessEqual(path, os.path.join(name, os.path.join("Contents/MacOS", self.goodproject.name)), f'Bundle path evaluation failed {path}')
        path = self.goodproject.evaluate_path("${prefix}/bin/foo")
        self.failUnlessEqual(path,
                             os.path.join(self.goodproject.get_prefix(),
                                          "bin/foo"),
                             f'Prefix path evaluation failed {path}')

    def test_i_get_launcher_script(self):
        launcher_path = self.goodproject.get_launcher_script()
        proj_dir = self.goodproject.get_project_dir()
        path = self.goodproject.evaluate_path(launcher_path.source)
        self.failUnlessEqual(path,
                             os.path.join(proj_dir, "launcher.sh"),
                             "Bad launcher source")
        self.failUnlessEqual(launcher_path.dest,
                             "${bundle}/Contents/MacOS/${name}",
                             "Bad launcher destination")

    def test_j_get_icon_themes(self):
        themes = self.goodproject.get_icon_themes()
        self.failUnlessEqual(len(themes), 2,
                             f'Wrong number of themes {len(themes)}')
        self.failUnlessEqual(themes[-1].name, "hicolor",
                             f'No hicolor theme {themes[-1].name}')

    def test_k_get_frameworks(self):
        fw = self.goodproject.get_frameworks()
        self.failUnlessEqual(len(fw), 1,
                             f'Wrong number of frameworks {len(fw)}')

    def test_l_get_main_binary(self):
        bin = self.goodproject.get_main_binary()
        self.failUnlessEqual(bin.source, "${prefix}/bin/foo-source",
                         f'Bad binary source {bin.source}')
        self.failUnlessEqual(bin.dest, "${bundle}/Contents/MacOS/${name}-bin",
                             f'Bad binary destination {bin.dest}')

    def test_m_get_binaries(self):
        bin = self.goodproject.get_binaries()
        self.failUnlessEqual(len(bin), 2,
                             f'Wrong number of binaries {len(bin)}')

    def test_n_get_data(self):
        data = self.goodproject.get_data()
        self.failUnlessEqual(len(data), 3,
                             f'Wrong number of data paths {len(data)}')
        self.failUnlessEqual(data[2].dest,
                             "${bundle}/Contents/Resources/etc/gtk-2.0/gtkrc",
                             f'Data[2] Destination {data[2].dest}')

    def test_o_get_translations(self):
        trans = self.goodproject.get_translations()
        self.failUnlessEqual(len(trans), 1,
                             f'Wrong number of translations {len(trans)}')
        self.failUnlessEqual(trans[0].name, "foo",
                             f'Bad translation name {trans[0].name}')
        self.failUnlessEqual(trans[0].source, "${prefix}/share/locale",
                             f'Bad translation source {trans[0].source}')
