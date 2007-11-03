import gobject
import pango
import gtk
from project import Path

class PathList(gtk.HBox):
    def __init__(self):
        gtk.HBox.__init__(self)

        self.set_spacing(6)

        builder = gtk.Builder()
        builder.add_from_file("path-list.ui")
        
        # Get the scrolled window
        widget = builder.get_object("scrolledwindow")
        self.pack_start(widget, True, True)

        self.treeview = builder.get_object("treeview")

        model = gtk.ListStore(gobject.TYPE_PYOBJECT)
        self.treeview.set_model(model)

        cell = builder.get_object("source_renderer")
        column = builder.get_object("source_column")
        column.set_cell_data_func(cell, self.source_cell_data_func)

        cell = builder.get_object("dest_renderer")
        column = builder.get_object("dest_column")
        column.set_cell_data_func(cell, self.dest_cell_data_func)

        cell = builder.get_object("type_renderer")
        column = builder.get_object("type_column")
        column.set_cell_data_func(cell, self.type_cell_data_func)

        selection = self.treeview.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.connect("changed", self.selection_changed_cb)

        bbox = gtk.VBox()
        bbox.set_spacing(6)
        self.pack_start(bbox, False, False)
        
        self.add_button = gtk.Button()
        self.add_button.add(gtk.image_new_from_stock("gtk-add", gtk.ICON_SIZE_MENU))
        self.add_button.connect("clicked", self.add_clicked_cb)
        bbox.pack_start(self.add_button, False, False)

        self.remove_button = gtk.Button()
        self.remove_button.add(gtk.image_new_from_stock("gtk-remove", gtk.ICON_SIZE_MENU))
        self.remove_button.connect("clicked", self.remove_clicked_cb)
        bbox.pack_start(self.remove_button, False, False)

        self.edit_button = gtk.Button()
        self.edit_button.add(gtk.image_new_from_stock("gtk-properties", gtk.ICON_SIZE_MENU))
        self.edit_button.connect("clicked", self.edit_clicked_cb)
        bbox.pack_start(self.edit_button, False, False)

        self.treeview.grab_focus()

        # Force update of selection state
        self.selection_changed_cb(selection)

    def source_cell_data_func(self, column, cell, model, iter):
        (path,) = model.get(iter, 0)
        cell.set_property("text", path.source)

    def dest_cell_data_func(self, column, cell, model, iter):
        (path,) = model.get(iter, 0)
        cell.set_property("text", path.dest)

    def type_cell_data_func(self, column, cell, model, iter):
        (path,) = model.get(iter, 0)
        if path.path_type == Path.FILE:
            text = "File"
        else:
            text = "Directory"
        cell.set_property("text", text)

    def selection_changed_cb(self, selection):
        (model, rows) = selection.get_selected_rows()

        self.remove_button.set_sensitive(len(rows) > 0)
        self.edit_button.set_sensitive(len(rows) == 1)

    def add_clicked_cb(self, button):
        dialog = PathDialog(self.get_toplevel())
        dialog.run()
        dialog.destroy()
    
    def edit_clicked_cb(self, button):
        selection = self.treeview.get_selection()
        (model, rows) = selection.get_selected_rows()

        i = model.get_iter(rows[0])
        (path,) = model.get(i, 0)
        
        dialog = PathDialog(self.get_toplevel(), path)
        if dialog.run() == gtk.RESPONSE_OK:
            model.row_changed(rows[0], i)
            
        dialog.destroy()

    def remove_clicked_cb(self, button):
        selection = self.treeview.get_selection()
        (model, rows) = selection.get_selected_rows()

        iters = map(lambda path: model.get_iter(path), rows)

        # Iters are persistant with GtkListStore so this is OK
        for iter in iters:
            model.remove(iter)

        # Re-select the first one available after removing
        if model.iter_is_valid(iter):
            selection.select_iter(iter)
    
    def set_path_list(self, paths):
        model = self.treeview.get_model()
        model.clear()

        for path in paths:
            model.append((path,))

    def get_path_list(self):
        return []


class PathDialog(gtk.Dialog):
    def __init__(self, parent=None, path=None):
        gtk.Dialog.__init__(self, "Edit Path", parent,
                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                            ("Cancel", gtk.RESPONSE_CANCEL,
                             "OK", gtk.RESPONSE_OK))
        self.set_has_separator(False)
        self.set_default_size(400, -1)

        vbox = gtk.VBox(False, 12)
        vbox.set_border_width(12)
        self.vbox.add(vbox)

        group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        hbox = gtk.HBox(False, 6)
        vbox.pack_start(hbox, False, False, 0)
        label = gtk.Label("Type:")
        label.set_alignment(1, 0.5)
        group.add_widget(label)
        hbox.pack_start(label, False, False, 0)
        self.type_file_button = gtk.RadioButton(None, "File")
        hbox.pack_start(self.type_file_button, False, False, 0)
        self.type_directory_button = gtk.RadioButton(self.type_file_button, "Directory")
        hbox.pack_start(self.type_directory_button, False, False, 0)

        if path and path.path_type == "directory":
            self.type_directory_button.set_active(True)
                
        self.type_file_button.connect("toggled", self.type_toggled_cb)

        hbox = gtk.HBox(False, 6)
        vbox.pack_start(hbox, False, False, 0)
        label = gtk.Label("Source:")
        label.set_alignment(1, 0.5)
        group.add_widget(label)
        hbox.pack_start(label, False, False, 0)
        self.source_entry = gtk.Entry()
        hbox.pack_start(self.source_entry, True, True, 0)
        if path:
            self.source_entry.set_text(path.source)

        button = gtk.FileChooserButton("Choose Source")
        if path and path.path_type == "directory":
            button.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
        else:
            button.set_action(gtk.FILE_CHOOSER_ACTION_OPEN)
        self.source_button = button
        hbox.pack_start(button, True, True, 0)

        hbox = gtk.HBox(False, 6)
        vbox.pack_start(hbox, False, False, 0)
        label = gtk.Label("Destination:")
        label.set_alignment(1, 0.5)
        group.add_widget(label)
        hbox.pack_start(label, False, False, 0)
        self.dest_entry = gtk.Entry()
        hbox.pack_start(self.dest_entry, True, True, 0)
        if path:
            self.dest_entry.set_text(path.dest)

        button = gtk.FileChooserButton("Choose Destination")
        if path and path.path_type == "directory":
            button.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
        else:
            button.set_action(gtk.FILE_CHOOSER_ACTION_OPEN)
        self.dest_button = button
        hbox.pack_start(button, True, True, 0)

        self.help_label = gtk.Label()
        self.help_label.set_line_wrap_mode(pango.WRAP_WORD_CHAR)
        self.help_label.set_line_wrap(True)
        self.help_label.set_alignment(0, 0.5)
        # Force the label to 3 lines so the window doesn't resize later.
        self.help_label.set_markup("<span size='small' style='italic'>\n\n\n</span>")
        vbox.pack_start(self.help_label, False, False, 0)
        
        self.source_entry.connect("changed", self.entries_changed_cb)
        self.dest_entry.connect("changed", self.entries_changed_cb)

        self.connect("response", self.response_cb)

        if path:
            # Force sensitivity update
            self.entries_changed_cb(self.source_entry)
        else:
            self.set_response_sensitive(gtk.RESPONSE_OK, False)

            # Hack to allow creating an empty node, just for the UI.
            path = Path("/foo", "/bar")
            path.source = None
            path.dest = None
        self.path = path

        vbox.show_all()

    def entries_changed_cb(self, entry):
        try:
            Path.validate(self.source_entry.get_text(), self.dest_entry.get_text())
            self.help_label.set_text("")
            self.set_response_sensitive(gtk.RESPONSE_OK, True)
        except Exception, e:
            self.help_label.set_markup("<span size='small' style='italic'>" +
                                       str(e) + "</span>")
            self.set_response_sensitive(gtk.RESPONSE_OK, False)
        
    def type_toggled_cb(self, button):
        # Update the filechooser buttons according to the source/dest type
        if button.get_active() and button == self.type_file_button:
            self.source_button.set_action(gtk.FILE_CHOOSER_ACTION_OPEN)
            self.dest_button.set_action(gtk.FILE_CHOOSER_ACTION_OPEN)
        else:
            self.source_button.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
            self.dest_button.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)

    # NOTE: Why does this callback have a dialog parameter? "self"
    # should be enough, looks like a bug in the bindning?
    def response_cb(self, dialog, response):
        if response == gtk.RESPONSE_OK:
            self.path.source = self.source_entry.get_text()
            self.path.dest = self.dest_entry.get_text()

            if self.type_file_button.get_active():
                self.path.path_type = "file"
            else:
                self.path.path_type = "directory"
