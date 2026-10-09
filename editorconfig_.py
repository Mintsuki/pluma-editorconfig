# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2021-2023 Filip Szymański <fszymanski.pl@gmail.com>
# Copyright (c) 2026 Mintsuki <mintsuki@protonmail.com>

# Follows version 0.17.2 of the EditorConfig specification, bar
# spelling_language, which Pluma gives plugins no way to set, and utf-8-bom,
# whose byte order mark Pluma can't write (a file that has one keeps it).
# max_line_length, outside the spec, sets the right margin

import logging
import os
from contextlib import suppress

import gi

gi.require_version("Pluma", "1.0")
from gi.repository import Gio, GLib, GObject, Pluma

import editorconfig

logger = logging.getLogger("pluma-editorconfig")

# Pluma's names for the spec's charsets
CHARSETS = {
    "latin1": "ISO-8859-1",
    "utf-8": "UTF-8",
    "utf-8-bom": "UTF-8",
    "utf-16be": "UTF-16BE",
    "utf-16le": "UTF-16LE",
}

NEWLINE_TYPES = {
    "lf": Pluma.DocumentNewlineType.LF,
    "cr": Pluma.DocumentNewlineType.CR,
    "crlf": Pluma.DocumentNewlineType.CR_LF,
}

NEWLINES = {
    Pluma.DocumentNewlineType.LF: "\n",
    Pluma.DocumentNewlineType.CR: "\r",
    Pluma.DocumentNewlineType.CR_LF: "\r\n",
}

KNOWN_KEYS = ("indent_style", "indent_size", "tab_width", "end_of_line", "charset",
              "trim_trailing_whitespace", "insert_final_newline", "max_line_length")

# Pluma preferences that EditorConfig settings stand in for
PLUMA_KEYS = ("insert-spaces", "tabs-size", "display-right-margin", "right-margin-position")

# Where Pluma keeps the encoding a file was last opened or saved in on purpose
ENCODING_METADATA = "metadata::pluma-encoding"


# The settings depend on the path alone, so a file not yet saved there gets
# them too; one with no local path (a remote file) gets none
def properties_for(uri):
    if uri is None or (path := Gio.File.new_for_uri(uri).get_path()) is None:
        return {}
    try:
        return editorconfig.get_properties(path)
    except editorconfig.EditorConfigError:
        logger.error("Cannot parse file: '.editorconfig'")
        return {}


def document_properties(doc):
    location = doc.get_location()
    return properties_for(location.get_uri() if location else None)


def whole_number(value):
    with suppress(TypeError, ValueError):
        if (n := int(value)) > 0:
            return n
    return None


def encoding_for(conf):
    charset = CHARSETS.get(conf.get("charset"))
    return Pluma.Encoding.get_from_charset(charset) if charset else None


# Any byte outside ASCII, which all the charsets but UTF-16 read alike
def beyond_ascii(path):
    try:
        with open(path, "rb") as f:
            return any(b == 0 or b > 0x7F for b in f.read())
    except OSError:
        return False


class EditorConfigWindowPlugin(GObject.Object, Pluma.WindowActivatable):
    """Loading and saving, for every document in the window. A document's view
    gets its plugin only once its tab is first shown, which a document saved
    from a tab never shown (Save All) never is"""
    __gtype_name__ = "EditorConfigWindowPlugin"

    window = GObject.Property(type=Pluma.Window)

    def __init__(self):
        super().__init__()

    def do_activate(self):
        self.reopened = set()
        self.window_handler_ids = [
            self.window.connect("tab-added", lambda w, tab: self.watch(tab.get_document())),
            self.window.connect("tab-removed", lambda w, tab: self.unwatch(tab.get_document())),
        ]
        for doc in self.window.get_documents():
            self.watch(doc)

    def do_deactivate(self):
        for doc in self.window.get_documents():
            self.unwatch(doc)
        for handler_id in self.window_handler_ids:
            self.window.disconnect(handler_id)

    def do_update_state(self):
        pass

    def watch(self, doc):
        if not hasattr(doc, "editorconfig_document_handler_ids"):
            doc.editorconfig_document_handler_ids = [
                doc.connect("loaded", self.on_loaded),
                doc.connect("save", self.on_save),
                doc.connect("saved", self.on_saved),
            ]

    def unwatch(self, doc):
        for handler_id in getattr(doc, "editorconfig_document_handler_ids", ()):
            doc.disconnect(handler_id)
        with suppress(AttributeError):
            del doc.editorconfig_document_handler_ids

    def on_loaded(self, doc, error):
        conf = document_properties(doc)

        if (newline_type := NEWLINE_TYPES.get(conf.get("end_of_line"))) is not None:
            doc.set_property("newline-type", newline_type)

        # Plugins only see a document once its loading has begun, so a file's
        # first opening goes by Pluma's guess at its encoding, which can fail
        # or misread it. Then it's opened again in its charset, which Pluma
        # remembers for the next time; one opened in an encoding chosen on
        # purpose, now or before, is left so
        enc, loaded = encoding_for(conf), doc.get_encoding().get_charset()
        location = doc.get_location()
        if (enc is not None and enc.get_charset() != loaded and location is not None
                and doc.get_metadata(ENCODING_METADATA) != loaded
                and location.get_uri() not in self.reopened
                and (error or beyond_ascii(location.get_path()))):
            self.reopened.add(location.get_uri())
            GLib.idle_add(self.reopen, doc, enc)

    # In place of its tab, which closing an unchanged document allows
    def reopen(self, doc, enc):
        if (tab := Pluma.Tab.get_from_document(doc)) is None or doc.get_modified():
            return False
        notebook = tab.get_parent()
        position = notebook.page_num(tab)
        active = self.window.get_active_tab() == tab
        cursor = doc.get_iter_at_mark(doc.get_insert())
        new = self.window.create_tab_from_uri(doc.get_location().get_uri(), enc,
                                              cursor.get_line() + 1, False, active)
        notebook.reorder_child(new, position)
        self.window.close_tab(tab)
        if active:
            self.window.set_active_tab(new)
        return False

    def on_save(self, doc, uri, encoding, flags):
        conf = properties_for(uri)

        # In the file's charset, whatever it was opened or Saved As with
        enc = encoding_for(conf)
        if enc is not None and (encoding is None or enc.get_charset() != encoding.get_charset()):
            GObject.signal_stop_emission_by_name(doc, "save")
            doc.emit("save", uri, enc, flags)
            return

        if (newline_type := NEWLINE_TYPES.get(conf.get("end_of_line"))) is not None:
            doc.set_property("newline-type", newline_type)

        # Pluma's Save Without Trailing Spaces plugin trims every file, and no
        # other plugin can stop it, so false only takes effect with it off
        if conf.get("trim_trailing_whitespace") == "true":
            trim_trailing_whitespace(doc)

        doc.editorconfig_strip_final_newline = conf.get("insert_final_newline") == "false"
        if doc.editorconfig_strip_final_newline:
            strip_final_newlines(doc)

    def on_saved(self, doc, error):
        if not error and getattr(doc, "editorconfig_strip_final_newline", False):
            strip_final_newline_on_disk(doc)
        doc.editorconfig_strip_final_newline = False


class EditorConfigPlugin(GObject.Object, Pluma.ViewActivatable):
    """The editing settings, for a document's view"""
    __gtype_name__ = "EditorConfigPlugin"

    view = GObject.Property(type=Pluma.View)

    def __init__(self):
        super().__init__()

    # The settings are applied now too: a view can be activated after its
    # document has loaded, and then "loaded" never comes
    def do_activate(self):
        doc = self.view.get_buffer()
        self.handler_ids = [
            doc.connect("loaded", lambda d, _: self.apply_editorconfig(d)),
            # Save As may have moved it under other settings
            doc.connect("saved", lambda d, _: self.apply_editorconfig(d)),
        ]
        # What this plugin set, and to what: see apply_editorconfig
        self.applied = {}
        self.active = True
        self.pluma_settings = Gio.Settings.new("org.mate.pluma")
        self.pluma_settings_id = self.pluma_settings.connect("changed", self.on_pluma_setting_changed)
        self.apply_editorconfig(doc)

    def do_deactivate(self):
        doc = self.view.get_buffer()
        for handler_id in self.handler_ids:
            doc.disconnect(handler_id)
        self.pluma_settings.disconnect(self.pluma_settings_id)
        self.active = False

    def do_update_state(self):
        pass

    # Pluma applies a changed preference to every view; the file's settings
    # go back once it has
    def on_pluma_setting_changed(self, settings, key):
        if key in PLUMA_KEYS:
            GLib.idle_add(self.reapply)

    def reapply(self):
        if self.active:
            self.apply_editorconfig(self.view.get_buffer())
        return False

    # Each pair the file's EditorConfig sets is applied. One it stops setting
    # (Save As, or "unset") goes back to Pluma's own setting, if this plugin
    # set it and nothing has changed it since, so another plugin's change
    # stays
    def apply_editorconfig(self, doc):
        conf = document_properties(doc)
        view, prefs = self.view, self.pluma_settings

        if (style := conf.get("indent_style")) in ("tab", "space"):
            view.set_insert_spaces_instead_of_tabs(style == "space")
            self.applied["indent_style"] = view.get_insert_spaces_instead_of_tabs()
        elif self.unapply("indent_style", view.get_insert_spaces_instead_of_tabs()):
            view.set_insert_spaces_instead_of_tabs(prefs.get_boolean("insert-spaces"))

        # Defaults to indent_size, which the core sees to
        if (width := whole_number(conf.get("tab_width"))) is not None:
            view.set_tab_width(width)
            self.applied["tab_width"] = view.get_tab_width()
        elif self.unapply("tab_width", view.get_tab_width()):
            view.set_tab_width(prefs.get_uint("tabs-size"))

        # Columns per indentation level, which a tab's width needn't match;
        # -1, as for "tab", makes it the tab width
        size = conf.get("indent_size")
        if (indent := -1 if size == "tab" else whole_number(size)) is not None:
            view.set_indent_width(indent)
            self.applied["indent_size"] = view.get_indent_width()
        elif self.unapply("indent_size", view.get_indent_width()):
            view.set_indent_width(-1)

        length = conf.get("max_line_length")
        if (margin := 0 if length == "off" else whole_number(length)) is not None:
            view.set_show_right_margin(margin > 0)
            if margin > 0:
                view.set_right_margin_position(margin)
            self.applied["max_line_length"] = self.margin()
        elif self.unapply("max_line_length", self.margin()):
            view.set_right_margin_position(prefs.get_uint("right-margin-position"))
            view.set_show_right_margin(prefs.get_boolean("display-right-margin"))

        # The spec has plugins ignore keys they don't know
        for name, val in conf.items():
            if name not in KNOWN_KEYS:
                logger.debug(f"Property not supported: '{name}={val}'")

    def margin(self):
        return self.view.get_show_right_margin(), self.view.get_right_margin_position()

    # Whether to put a setting back: only if this plugin set it, to the value
    # it still has
    def unapply(self, name, current):
        return name in self.applied and self.applied.pop(name) == current


# Every whitespace character before a line end, as the spec has it
def trim_trailing_whitespace(doc):
    doc.begin_user_action()
    for linenr in range(0, doc.get_line_count()):
        start = doc.get_iter_at_line(linenr)

        end = start.copy()
        if not end.ends_line():
            end.forward_to_line_end()

        line = doc.get_text(start, end, False)
        start.forward_chars(len(line.rstrip()))

        if not start.equal(end):
            doc.delete(start, end)
    doc.end_user_action()


# Line ends at the very end of the text, all of which insert_final_newline =
# false rules out
def strip_final_newlines(doc):
    start = doc.get_end_iter()
    while not start.is_start():
        before = start.copy()
        before.backward_char()
        if before.get_char() not in "\n\r  ":
            break
        start = before
    if not start.is_end():
        doc.delete(start, doc.get_end_iter())


# Pluma ends every non-empty file with a newline as it writes it, so with
# insert_final_newline = false it comes off the file afterwards. The
# modification time goes back to the one Pluma recorded, or Pluma would take
# the file for changed by another program
def strip_final_newline_on_disk(doc):
    location = doc.get_location()
    if location is None or (path := location.get_path()) is None:
        return
    try:
        charset = doc.get_encoding().get_charset()
        with open(path, "rb") as f:
            head = f.read(2)
        # UTF-16 with a byte order mark, in the order that names
        if charset == "UTF-16":
            charset = "UTF-16LE" if head == b"\xff\xfe" else "UTF-16BE"
        newline = NEWLINES[doc.get_newline_type()].encode(charset)
        st = os.stat(path)
        if st.st_size < len(newline):
            return
        with open(path, "r+b") as f:
            f.seek(-len(newline), os.SEEK_END)
            if f.read() != newline:
                return
            f.truncate(st.st_size - len(newline))
        os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))
    except (OSError, LookupError, UnicodeError) as e:
        logger.error(f"Cannot remove the final newline: {e}")
