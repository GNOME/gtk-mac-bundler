import sys, os

from project import *
from bundler import *

def main(argv):
    if len(argv) != 1:
        print "Usage: %s <bundle descriptopn file>" % (sys.argv[0])
        sys.exit(2)

    if not os.path.exists(argv[0]):
        print "File %s does not exist" % (argv[0])
        sys.exit(2)

    project = Project(argv[0])
    bundler = Bundler(project)

    bundler.run()
