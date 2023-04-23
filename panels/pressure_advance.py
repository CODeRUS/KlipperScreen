import logging
import re

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango

from ks_includes.screen_panel import ScreenPanel


def create_panel(*args):
    return PressureAdvancePanel(*args)


class PressureAdvancePanel(ScreenPanel):

    def __init__(self, screen, title):
        super().__init__(screen, title)
        self.options = []
        self.grid = Gtk.Grid()
        self.values = {}
        self.list = {}
        self.extruders = self._printer.get_tools()

        for extruder in self.extruders:
            self.options += [
                {"name": _(f"{extruder} pressure advance"),
                 "units": _("s"),
                 "option": f"{extruder} advance",
                 "value": self._printer.get_dev_stat(extruder, "pressure_advance"),
                 "digits": 3,
                 "minval": 0,
                 "maxval": 0.2}]
            self.options += [
                {"name": _(f"{extruder} smooth time"),
                 "units": _("s"),
                 "option": f"{extruder} smooth_time",
                 "value": self._printer.get_dev_stat(extruder, "smooth_time"),
                 "digits": 2,
                 "minval": 0,
                 "maxval": 0.1}]

        for opt in self.options:
            self.add_option(**opt)

        scroll = self._gtk.ScrolledWindow()
        scroll.add(self.grid)

        self.content.add(scroll)
        self.content.show_all()

    def activate(self):
        pass

    def process_update(self, action, data):
        if action == "notify_status_update":
            print(data)
            for entity in data:
                if entity in self.extruders:
                    for param in data[entity]:
                        self.update_option(f'{entity} {param}', data[entity][param])

    def update_option(self, option, value):
        if option not in self.list:
            return

        if self.list[option]['scale'].has_grab():
            return

        self.values[option] = float(value)
        self.list[option]['scale'].disconnect_by_func(self.set_opt_value)
        self.list[option]['scale'].set_value(self.values[option])
        self.list[option]['scale'].connect("button-release-event", self.set_opt_value, option)
        # Infinite scale
        for opt in self.options:
            if opt['option'] == option:
                if self.values[option] > opt["maxval"] * .75:
                    self.list[option]['adjustment'].set_upper(self.values[option] * 1.5)
                else:
                    self.list[option]['adjustment'].set_upper(opt["maxval"])
                break

    def add_option(self, option, name, units, value, digits, minval, maxval):
        logging.info(f"Adding option: {option}")
        if value is None:
            value = 0

        name = Gtk.Label()
        name.set_markup(f"<big><b>{name}</b></big> ({units})")
        name.set_hexpand(True)
        name.set_vexpand(True)
        name.set_halign(Gtk.Align.START)
        name.set_valign(Gtk.Align.CENTER)
        name.set_line_wrap(True)
        name.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.values[option] = value
        # adj (value, lower, upper, step_increment, page_increment, page_size)
        adj = Gtk.Adjustment(value, minval, maxval, 1, 5, 0)
        scale = Gtk.Scale.new(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.set_digits(digits)
        scale.set_hexpand(True)
        scale.set_has_origin(True)
        scale.get_style_context().add_class("option_slider")
        scale.connect("button-release-event", self.set_opt_value, option)

        reset = self._gtk.Button("refresh", style="color1")
        reset.connect("clicked", self.reset_value, option)
        reset.set_hexpand(False)

        item = Gtk.Grid()
        item.attach(name, 0, 0, 2, 1)
        item.attach(scale, 0, 1, 1, 1)
        item.attach(reset, 1, 1, 1, 1)

        self.list[option] = {
            "row": item,
            "scale": scale,
            "adjustment": adj,
        }

        pos = sorted(self.list).index(option)
        self.grid.attach(self.list[option]['row'], 0, pos, 1, 1)
        self.grid.show_all()

    def reset_value(self, widget, option):
        for x in self.options:
            if x["option"] == option:
                self.update_option(option, x["value"])
        self.set_opt_value(None, None, option)

    def set_opt_value(self, widget, event, opt):
        value = self.list[opt]['scale'].get_value()
        self._screen._ws.klippy.gcode_script(f"SET_PRESSURE_ADVANCE EXTRUDER={opt}={value}")
