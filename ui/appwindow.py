import gobject
import gtk
from igemacintegration import *
from newassistant import *
from properties import *
from project import *

ui_info = \
'''<ui>
  <menubar name='MenuBar'>
    <menu action='FileMenu'>
      <menuitem action='New'/>
      <menuitem action='Open'/>
      <menuitem action='Save'/>
      <menuitem action='SaveAs'/>
      <menuitem action='Quit'/>

      <!-- Just put those here since it will be moved anyway when using
           the mac menubar
      -->
      <menuitem action='About'/> 
      <menuitem action='Preferences'/>
    </menu>
  </menubar>
</ui>'''


class AppWindow(gtk.Window):
    def __init__(self):
        # Create the toplevel window
        gtk.Window.__init__(self)

        self.set_title("App Creator")
        self.set_default_size(500, 350)

        self.toplevel_box = gtk.VBox(False, 12)
        self.toplevel_box.set_border_width(18)
        self.add(self.toplevel_box)

        self.manager = gtk.UIManager()
        self.manager.insert_action_group(self.create_action_group(), 0)
        self.add_accel_group(self.manager.get_accel_group())

        try:
            mergeid = self.manager.add_ui_from_string(ui_info)
        except gobject.GError, msg:
            print "Failed building menus: %s" % msg

        self.manager.ensure_update()

        # Set up the Mac menu bar
        self.macmenu = MacMenu()

        widget = self.manager.get_widget("/MenuBar")
        self.macmenu.set_menu_bar(widget)

        widget = self.manager.get_widget("/MenuBar/FileMenu/Quit")
        self.macmenu.set_quit_menu_item(widget)

        group = self.macmenu.add_app_menu_group()
        widget = self.manager.get_widget("/MenuBar/FileMenu/About")
        group.add_app_menu_item(widget, None)

        group = self.macmenu.add_app_menu_group()
        widget = self.manager.get_widget("/MenuBar/FileMenu/Preferences")
        group.add_app_menu_item(widget, None)

        # Test a bit...
        project = Project("giggle.bundle")
        self.properties_widget = Properties(project)
        self.toplevel_box.pack_start(self.properties_widget, True, True, 0)

        bbox = gtk.HButtonBox()
        bbox.set_layout(gtk.BUTTONBOX_END)
        self.toplevel_box.pack_start(bbox, False, False, 0)
        
        button = gtk.Button("Create Bundle")
        bbox.pack_start(button, False, False)

        self.show_all()

    def create_action_group(self):
        # GtkActionEntry
        entries = (
          ( "FileMenu", None, "_File" ),               # name, stock id, label
          ( "New", gtk.STOCK_NEW,                      # name, stock id
            "New Bundle...", "<control>N",             # label, accelerator
            "Create a new bundle",                     # tooltip
            self.activate_new ),
          ( "Open", gtk.STOCK_OPEN,
            "Open Bundle","<control>O",
            "Open a bundle",
            self.activate_action ),
          ( "Save", gtk.STOCK_SAVE,
            "Save","<control>S",
            "Save current bundle",
            self.activate_action ),
          ( "SaveAs", gtk.STOCK_SAVE,
            "Save As...", None,
            "Save with a different filename",
            self.activate_action ),
          ( "Quit", gtk.STOCK_QUIT,
            "Quit", "<control>Q",
            "Quit the application",
            self.activate_quit ),
          ( "Preferences", None,
            "Preferences...", "<control>,",
            None,
            self.activate_about ),
          ( "About", None,
            "About App Creator", "<control>A",
            "About",
            self.activate_about ),
        )

        action_group = gtk.ActionGroup("AppWindowActions")
        action_group.add_actions(entries)

        return action_group

    def activate_new(self, action):
        window = NewAssistant(self)
        window.run()        

    def activate_quit(self, action):
        gtk.main_quit()

    def activate_about(self, action):
        dialog = gtk.AboutDialog()
        dialog.set_name("App Creator")
        dialog.set_copyright("\302\251 Copyright 2007 Imendio AB")
        dialog.set_website("http://developer.imendio.com/projects/gtkosx/")
        dialog.connect ("response", lambda d, r: d.destroy())
        dialog.show()

    def activate_action(self, action):
        dialog = gtk.MessageDialog(self, gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE,
            "You activated action: '%s' of type '%s'" % (action.get_name(), type(action)))
        # Close dialog on user response
        dialog.connect ("response", lambda d, r: d.destroy())
        dialog.show()

if __name__ == '__main__':
    window = AppWindow()
    window.connect("destroy", lambda x: gtk.main_quit())
    gtk.main()
