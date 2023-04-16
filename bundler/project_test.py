import os
import errno
import sys
import unittest
import xml.dom.minidom
from plistlib import load as plist_load

from .project import Project
from . import utils

class MockProject(Project):

    def __init__(self, testxml, path):
        super().__init__(path)
        doc = xml.dom.minidom.parseString(testxml)
        self.root = utils.node_get_element_by_tag_name(doc, "app-bundle")
        assert self.root is not None
        project_dir, tail = os.path.split(path)
        self.project_dir = os.path.join(os.getcwd(), project_dir)
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

class ProjectTest(unittest.TestCase):

    def setUp(self):
        self.goodproject = MockProject(ProjectTest.goodxml,
                                        ProjectTest.goodpath)
        self.badproject = MockProject(ProjectTest.badxml,
                                       ProjectTest.badpath)

    def test_a_get_project_path(self):
        path = self.goodproject.get_project_path()
        self.assertEqual(path, ProjectTest.goodpath,
                             f'Project returned incorrect project path {path} wanted {ProjectTest.goodpath}')
        path = self.badproject.get_project_path()
        self.assertEqual(path, ProjectTest.badpath,
                             f'Project returned incorrect bad project path {path}')

    def test_b_get_project_dir(self):
        project_dir = self.goodproject.get_project_dir()
        good_dir, dummy_tail = os.path.split(ProjectTest.goodpath)
        self.assertEqual(project_dir, good_dir,
                             f'Project returned incorrect project dir {project_dir}')

    def test_c_get_meta(self):
        node = self.goodproject.get_meta()
        self.assertNotEqual(node, None, "Didn't find meta node in goodproject")
        self.assertRaises(Exception, self.badproject.get_meta())

    def test_d_get_prefix(self):
        try:
            pfx = self.goodproject.get_prefix()
        except KeyError:
            self.fail("Goodproject didn't set the default prefix")
        self.assertEqual(pfx, os.getenv("JHBUILD_PREFIX",
                                            f'Default prefix {pfx}'))
        try:
            pfx = self.goodproject.get_prefix("alt")
        except KeyError:
            self.fail("Goodproject didn't set the alt prefix")
        self.assertEqual(pfx, "/usr/local/gtk", f'Alternate prefix {pfx}')

    def test_e_get_plist_path(self):
        try:
            path = self.goodproject.get_plist_path()
        except KeyError:
            self.fail("Goodproject didn't set the default prefix")
        except ValueError:
            self.fail("Goodproject didn't set the plist tag")
        project_dir, dummy_tail = os.path.split(ProjectTest.goodpath)
        self.assertEqual(path,
                             os.path.join(project_dir, "test.plist"),
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
        self.assertEqual(pname, name, f'Bad Name {pname}')



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
        self.assertEqual(path, os.path.join(name, os.path.join("Contents/MacOS", self.goodproject.name)), f'Bundle path evaluation failed {path}')
        path = self.goodproject.evaluate_path("${prefix}/bin/foo")
        self.assertEqual(path,
                             os.path.join(self.goodproject.get_prefix(),
                                          "bin/foo"),
                             f'Prefix path evaluation failed {path}')

    def test_i_get_launcher_script(self):
        launcher_path = self.goodproject.get_launcher_script()
        proj_dir = self.goodproject.get_project_dir()
        path = self.goodproject.evaluate_path(launcher_path.source)
        self.assertEqual(path,
                             os.path.join(proj_dir, "launcher.sh"),
                             "Bad launcher source")
        self.assertEqual(launcher_path.dest,
                             "${bundle}/Contents/MacOS/${name}",
                             "Bad launcher destination")

    def test_j_get_icon_themes(self):
        themes = self.goodproject.get_icon_themes()
        self.assertEqual(len(themes), 2,
                             f'Wrong number of themes {len(themes)}')
        self.assertEqual(themes[-1].name, "hicolor",
                             f'No hicolor theme {themes[-1].name}')

    def test_k_get_frameworks(self):
        fw = self.goodproject.get_frameworks()
        self.assertEqual(len(fw), 1,
                             f'Wrong number of frameworks {len(fw)}')

    def test_l_get_main_binary(self):
        main_bin = self.goodproject.get_main_binary()
        self.assertEqual(main_bin.source, "${prefix}/bin/foo-source",
                         f'Bad binary source {main_bin.source}')
        self.assertEqual(main_bin.dest, "${bundle}/Contents/MacOS/${name}-bin",
                             f'Bad binary destination {main_bin.dest}')

    def test_m_get_binaries(self):
        bins = self.goodproject.get_binaries()
        self.assertEqual(len(bins), 2,
                             f'Wrong number of binaries {len(bins)}')

    def test_n_get_data(self):
        data = self.goodproject.get_data()
        self.assertEqual(len(data), 3,
                             f'Wrong number of data paths {len(data)}')
        self.assertEqual(data[2].dest,
                             "${bundle}/Contents/Resources/etc/gtk-2.0/gtkrc",
                             f'Data[2] Destination {data[2].dest}')

    def test_o_get_translations(self):
        trans = self.goodproject.get_translations()
        self.assertEqual(len(trans), 1,
                             f'Wrong number of translations {len(trans)}')
        self.assertEqual(trans[0].name, "foo",
                             f'Bad translation name {trans[0].name}')
        self.assertEqual(trans[0].source, "${prefix}/share/locale",
                             f'Bad translation source {trans[0].source}')
