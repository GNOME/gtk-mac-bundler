import os
import sys

from .project import Project
from .bundler import Bundler

def main(argv):
    if len(argv) != 1:
        print(f'Usage: {sys.argv[0]} <bundle descriptopn file>')
        sys.exit(2)

    if not os.path.exists(argv[0]):
        print(f'File {argv[0]} does not exist')
        sys.exit(2)

    project = Project(argv[0])
    bundler = Bundler(project)
    #try:
    bundler.run()
    #except Exception as err:
     #   print(f'Bundler encountered an error {str(err)}')
