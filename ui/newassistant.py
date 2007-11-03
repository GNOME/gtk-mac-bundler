import os
import gobject
import gtk

class NewAssistant(gtk.Assistant):
    def __init__(self, parent=None):
        gtk.Assistant.__init__(self)

        if parent:
            self.set_transient_for(parent)

        self.set_title('Assistant')
        self.set_default_size(500, 300)
        self.set_border_width(12)

        self.add_select_type_page()
        self.add_select_name_page()

        self.directory_edited = False

        self.connect("prepare", self.prepare_cb)
        self.connect("cancel", self.cancel_cb)
        self.connect("close", self.close_cb)
        self.connect("destroy", lambda d: gtk.main_quit())

    def prepare_cb(self, unknown, page):
        if page == self.select_type_page:
            self.type_treeview.grab_focus()
        elif page == self.select_name_page:
            self.name_entry.grab_focus()

    def cancel_cb(self, unknown):
        self.destroy()

    def close_cb(self, unknown):
        self.destroy()

    def run(self):
        self.connect ("destroy", lambda d: gtk.main_quit())
        self.show_all()

        # The grab in prepare doesn't work the first time we show the
        # first page for some reason
        self.type_treeview.grab_focus()
        try:
            gtk.main()
        except KeyboardInterrupt:
            import sys
            sys.exit(0)

    def update_select_name_page_completeness(self):
        complete = len(self.name_entry.get_text()) > 0 and \
                   len(self.directory_entry.get_text()) > 0
        self.set_page_complete(self.select_name_page, complete)

    def type_changed_cb(self, selection):
        (model, iter) = selection.get_selected()
        self.set_page_title(self.select_name_page, "New %s" % (model.get(iter, 0)))

    def add_select_type_page(self):
        page = gtk.VBox(False, 0)
        page.set_border_width(12)

        label = gtk.Label("Select the type of application to create:")
        label.set_alignment(0, 0.5)
        page.pack_start(label, False, False, 6)

        builder = gtk.Builder()
        builder.add_from_file("app-type-treeview.ui")
        
        # Get the scrolled window
        widget = builder.get_object("scrolledwindow")
        page.pack_start(widget)

        widget = builder.get_object("treeview")
        selection = widget.get_selection()
        selection.set_mode(gtk.SELECTION_BROWSE)
        selection.connect("changed", self.type_changed_cb)
        self.type_treeview = widget

        self.append_page(page)
        self.set_page_title(page, "New Application Bundle")
        self.set_page_type(page, gtk.ASSISTANT_PAGE_INTRO)
        self.set_page_complete(page, True)

        self.select_type_page = page

    def name_changed_cb(self, entry):
        if not self.directory_edited:
            self.directory_entry.handler_block(self.directory_changed_handler_id)
            self.directory_entry.set_text("~/%s" % (entry.get_text()))
            self.directory_entry.handler_unblock(self.directory_changed_handler_id)

        self.update_select_name_page_completeness()

    def directory_changed_cb(self, entry):
        if len(entry.get_text()) > 0:
            self.directory_edited = True
        else:
            self.directory_edited = False
            
        self.update_select_name_page_completeness()

    def add_select_name_page(self):
        page = gtk.VBox(False, 12)
        page.set_border_width(12)

        group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        hbox = gtk.HBox(False, 6)
        page.pack_start(hbox, False, False, 0)
        label = gtk.Label("Application Name:")
        label.set_alignment(1, 0.5)
        group.add_widget(label)
        hbox.pack_start(label, False, False, 0)
        self.name_entry = gtk.Entry()
        hbox.pack_start(self.name_entry, True, True, 0)

        hbox = gtk.HBox(False, 6)
        page.pack_start(hbox, False, False, 0)
        label = gtk.Label("Project Directory:")
        label.set_alignment(1, 0.5)
        group.add_widget(label)
        hbox.pack_start(label, False, False, 0)
        self.directory_entry = gtk.Entry()
        self.directory_entry.set_text("~/")
        hbox.pack_start(self.directory_entry, True, True, 0)
        button = gtk.FileChooserButton("Choose Directory")
        button.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
        button.set_current_folder(os.getenv("HOME"))
        self.directory_button = button
        hbox.pack_start(button, True, True, 0)
        
        self.name_entry.connect("changed", self.name_changed_cb)
        self.directory_changed_handler_id = self.directory_entry.connect("changed", self.directory_changed_cb)

        self.append_page(page)
        self.set_page_title(page, "New ...")
        self.set_page_type(page, gtk.ASSISTANT_PAGE_CONFIRM)
        self.set_page_complete(page, False)

        self.select_name_page = page
        
