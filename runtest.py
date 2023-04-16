#!/usr/bin/env python3
if __name__ == "__main__" and __package__ is None:
    __package__ = "bundler"

import unittest
import os
from .project_test import ProjectTest

def setProjects( goodpath, badpath):
    if not os.path.isabs(goodpath):
        goodpath = os.path.join(os.getcwd(), goodpath)
    f = open(goodpath)
    ProjectTest.goodxml = f.read()
    f.close()
    ProjectTest.goodpath = goodpath
    if not os.path.isabs(badpath):
        badpath = os.path.join(os.getcwd(), badpath)
    f = open(badpath)
    ProjectTest.badxml = f.read()
    f.close()
    ProjectTest.badpath = badpath
 
setProjects("test/goodproject.bundle", "test/badproject.bundle")
suite = unittest.TestLoader().loadTestsFromTestCase(ProjectTest)
unittest.TextTestRunner(verbosity=2).run(suite)
