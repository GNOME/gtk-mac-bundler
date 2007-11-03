import os
import re
import gtk
from plistlib import Plist
from pathlist import *

class Properties(gtk.Notebook):
    def __init__(self, project=None):
        gtk.Notebook.__init__(self)

        self.project = project

        self.setup_general_page()
        self.setup_data_page()
        self.setup_frameworks_page()
        self.setup_binaries_page()
        self.setup_advanced_page()

        self.data_path_list.set_path_list(project.get_data())
        self.binaries_path_list.set_path_list(project.get_binaries())

        self.application_name_entry.grab_focus()

    def setup_general_page(self):
        page = gtk.VBox(False, 12)
        page.set_border_width(18)

        plist_path = self.project.get_plist_path()

        # FIXME: Should probably make it possible to do this in
        # project directly.
        project_dir, tail = os.path.split(self.project.get_project_path())
        print project_dir, plist_path
        p = re.compile("^\${project}")
        plist_path = p.sub(project_dir, plist_path)

        p = re.compile("^\${project}")
        plist_path = p.sub(project_dir, plist_path)

        print "a%sb" % (plist_path)

        plist = Plist.fromFile(plist_path)

        group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        hbox = gtk.HBox(False, 6)
        label = gtk.Label("Application Name:")
        label.set_alignment(1, 0.5)
        group.add_widget(label)
        hbox.pack_start(label, False, False, 0)
        entry = gtk.Entry()
        entry.set_text(plist.CFBundleExecutable)
        self.application_name_entry = entry
        hbox.pack_start(entry, True, True, 0)
        page.pack_start(hbox, False, False, 0);

        hbox = gtk.HBox(False, 6)
        label = gtk.Label("Prefix:")
        label.set_alignment(1, 0.5)
        group.add_widget(label)
        hbox.pack_start(label, False, False, 0)
        entry = gtk.Entry()
        entry.set_text(self.project.get_prefix())
        self.prefix_entry = entry
        hbox.pack_start(entry, True, True, 0)
        button = gtk.FileChooserButton("Choose Prefix")
        button.set_mode =gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER
        self.prefix_button = button
        hbox.pack_start(button, True, True, 0)
        page.pack_start(hbox, False, False, 0);

        hbox = gtk.HBox(False, 6)
        label = gtk.Label("Executable:")
        label.set_alignment(1, 0.5)
        group.add_widget(label)
        hbox.pack_start(label, False, False, 0)
        entry = gtk.Entry()
        entry.set_text(self.project.get_main_binary().source)
        self.executable_entry = entry
        hbox.pack_start(entry, True, True, 0)
        button = gtk.FileChooserButton("Choose Executable")
        self.executable_button = button
        hbox.pack_start(button, True, True, 0)
        page.pack_start(hbox, False, False, 0);

        self.general_page = page
        self.append_page(page, gtk.Label("General"))

    def setup_data_page(self):
        page = gtk.VBox(False, 12)
        page.set_border_width(18)

        list = PathList()
        page.pack_start(list, True, True)

        self.data_path_list = list
        self.data_page = page
        self.append_page(page, gtk.Label("Data"))

    def setup_frameworks_page(self):
        page = gtk.VBox()
        page.add(gtk.Label("Not implemented"))

        self.binaries_page = page
        self.append_page(page, gtk.Label("Frameworks"))

    def setup_binaries_page(self):
        page = gtk.VBox(False, 12)
        page.set_border_width(18)

        list = PathList()
        page.pack_start(list, True, True)

        self.binaries_path_list = list
        self.data_page = page
        self.append_page(page, gtk.Label("Binaries"))

    def setup_advanced_page(self):
        # Additional executables
        # Additionla prefixes
        # Translations (languages, modules) list or auto
        # Theme engines, gtkrc, plist
        # Input methods (all or list)
        # Pango modules (all or list)
        # PyGTK+

        page = gtk.VBox()
        page.add(gtk.Label("Advanced"))

        self.binaries_page = page
        self.append_page(page, gtk.Label("Advanced"))


if __name__ == '__main__':
    properties = Properties()

    window = gtk.Window()
    window.set_default_size(400, 300)
    window.add(properties)
    window.connect("destroy", gtk.main_quit)
    window.show_all()

    gtk.main()

