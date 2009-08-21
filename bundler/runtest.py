#!/usr/bin/python
import unittest
import os
from project_test import Project_Test

def setProjects( goodpath, badpath):
    if not os.path.isabs(goodpath):
        goodpath = os.path.join(os.getcwd(), goodpath)
    f = open(goodpath)
    Project_Test.goodxml = f.read()
    f.close()
    Project_Test.goodpath = goodpath
    if not os.path.isabs(badpath):
        badpath = os.path.join(os.getcwd(), badpath)
    f = open(badpath)
    Project_Test.badxml = f.read()
    f.close()
    Project_Test.badpath = badpath
 
setProjects("test/goodproject.bundle", "test/badproject.bundle")
suite = unittest.TestLoader().loadTestsFromTestCase(Project_Test)
unittest.TextTestRunner(verbosity=2).run(suite)
