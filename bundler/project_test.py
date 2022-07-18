import os
import errno
import sys
import unittest
import xml.dom.minidom
from xml.dom.minidom import Node
from plistlib import Plist
from .project import Project
from . import utils

class Mock_Project(Project):

    def __init__(self, testxml, path):
        doc = xml.dom.minidom.parseString(testxml)
        self.root = utils.node_get_element_by_tag_name(doc, "app-bundle")
        assert self.root != None
        dir, tail = os.path.split(path)
        self.project_dir = os.path.join(os.getcwd(), dir)
        self.project_path = os.path.join(self.project_dir, tail)
        try:
            plist_path = os.path.join(self.project_dir, "test.plist")
            plist = Plist.fromFile(plist_path)
        except EnvironmentError as e:
            if e.errno == errno.ENOENT:
                print("Info.plist file not found: " + plist_path)
                sys.exit(1)
            else:
                raise
        self.name = plist.CFBundleExecutable

class Project_Test(unittest.TestCase):

    def setUp(self):
        self.goodproject = Mock_Project(Project_Test.goodxml, 
                                        Project_Test.goodpath)
        self.badproject = Mock_Project(Project_Test.badxml,
                                       Project_Test.badpath)

    def test_a_get_project_path(self):
        path = self.goodproject.get_project_path()
        self.failUnlessEqual(path, Project_Test.goodpath,
                   "Project returned incorrect project path %s wanted %s" % 
                             (path, Project_Test.goodpath) )
        path = self.badproject.get_project_path()
        self.failUnlessEqual(path, Project_Test.badpath,
                   "Project returned incorrect bad project path %s" % path)

    def test_b_get_project_dir(self):
        dir = self.goodproject.get_project_dir()
        good_dir, tail = os.path.split(Project_Test.goodpath)
        self.failUnlessEqual(dir, good_dir,
                   "Project returned incorrect project dir %s" % dir)

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
                                            "Default prefix %s" % pfx))
        try:
            pfx = self.goodproject.get_prefix("alt")
        except KeyError:
            self.fail("Goodproject didn't set the alt prefix")
        self.failUnlessEqual(pfx, "/usr/local/gtk", "Alternate prefix %s" % pfx)

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
                             "Bad Plist Path %s" % path)
        self.failUnlessRaises(Exception, self.badproject.get_plist_path)

    def test_f_get_name(self):
        try:
            plist_path = self.goodproject.get_plist_path()
        except KeyError:
            self.fail("Goodproject didn't set the default prefix")
        try:
            plist = Plist.fromFile(plist_path)
            name = plist.CFBundleExecutable
        except IOError:
            self.fail("Path problem " + plist_path)
        pname = self.goodproject.get_name()
        self.failUnlessEqual(pname, name, "Bad Name %s" % pname)



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
        self.failUnlessEqual(path, os.path.join(name, os.path.join("Contents/MacOS", self.goodproject.name)), "Bundle path evaluation failed %s" % path)
        path = self.goodproject.evaluate_path("${prefix}/bin/foo")
        self.failUnlessEqual(path, 
                             os.path.join(self.goodproject.get_prefix(), 
                                          "bin/foo"), 
                             "Prefix path evaluation failed %s" % path)

    def test_i_get_launcher_script(self):
        launcher_path = self.goodproject.get_launcher_script()
        proj_dir = self.goodproject.get_project_dir();
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
                             "Wrong number of themes %d" % len(themes))
        self.failUnlessEqual(themes[-1].name, "hicolor", 
                             "No hicolor theme %s" % themes[-1].name)

    def test_k_get_environment(self):
        env = self.goodproject.get_environment()
        self.failUnlessEqual(len(env.runtime_variables), 2, 
                         "Wrong number of runtime variables %d" % 
                             len(env.runtime_variables))
        self.failUnlessEqual(len(env.scripts), 2, 
                             "Wrong number of scripts %d" % len(env.scripts))

    def test_l_get_frameworks(self):
        fw = self.goodproject.get_frameworks()
        self.failUnlessEqual(len(fw), 1, 
                             "Wrong number of frameworks %d" % len(fw))

    def test_m_get_main_binary(self):
        bin = self.goodproject.get_main_binary()
        self.failUnlessEqual(bin.source, "${prefix}/bin/foo-source", 
                         "Bad binary source %s" % bin.source)
        self.failUnlessEqual(bin.dest, "${bundle}/Contents/MacOS/${name}-bin", 
                    "Bad binary destination %s" % bin.dest)

    def test_n_get_binaries(self):
        bin = self.goodproject.get_binaries()
        self.failUnlessEqual(len(bin), 2, 
                             "Wrong number of binaries %d" % len(bin))

    def test_o_get_data(self):
        data = self.goodproject.get_data()
        self.failUnlessEqual(len(data), 3, 
                             "Wrong number of data paths %d" % len(data))
        self.failUnlessEqual(data[2].dest, 
                             "${bundle}/Contents/Resources/etc/gtk-2.0/gtkrc", 
                             "Data[2] Destination %s" % data[2].dest)

    def test_p_get_translations(self):
        trans = self.goodproject.get_translations()
        self.failUnlessEqual(len(trans), 1, 
                             "Wrong number of translations %d" % len(trans))
        self.failUnlessEqual(trans[0].name, "foo", 
                             "Bad translation name %s" % trans[0].name)
        self.failUnlessEqual(trans[0].source, "${prefix}/share/locale",
                             "Bad translation source %s" % trans[0].source)


        
