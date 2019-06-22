# DreamMaker Language Client - Sublime package for DreamMaker Language Server
# Copyright (C) 2019  Tad Hardesty
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Utilities for dealing with the `.dme` file in relation to the workspace.

import os
import sublime, sublime_plugin
import threading, time

from . import utils


STATUS_KEY = "dreammaker_ticked"
TICKABLE_GLOB = "**/*.{dm,dmm,dmf,dms}"


class DreammakerToggleTickedCommand(sublime_plugin.TextCommand):
	def is_visible(self):
		return bool(is_tickable(self.view.file_name()))

	def run(self, edit):
		if env_toggle_ticked(self.view.window(), self.view.file_name()):
			update_ticked_status(self.view)
		else:
			sublime.error_message("There does not appear to be a .dme file.")

	def description(self):
		return 'description'


class DmInternalToggleTickedCommand(sublime_plugin.TextCommand):
	def run(self, edit, include, state=None):
		toggle_ticked(edit, self.view, include, state)

	def description(self, include, state=None):
		act = {None: 'Toggle', True: 'Tick', False: 'Untick'}[state]
		return '{} {}'.format(act, include)


class TickStatusEventListener(sublime_plugin.EventListener):
	def on_activated(self, view):
		update_ticked_status(view)


def update_ticked_status(view):
	fname = view.file_name()
	if not fname:
		view.erase_status(STATUS_KEY)
		return

	discovered = environment_path(view.window(), fname)
	if not discovered:
		view.erase_status(STATUS_KEY)
		return

	uri, relative = discovered
	if not is_tickable(relative):
		view.erase_status(STATUS_KEY)
		return

	ticked = relative in EnvironmentFile.from_window_and_uri(view.window(), uri).includes
	view.set_status(STATUS_KEY, "Ticked" if ticked else "Unticked")


def env_toggle_ticked(window, file_uri):
	if not file_uri:
		return

	discovered = environment_path(window, file_uri)
	if not discovered:
		return

	uri, relative = discovered
	if not is_tickable(relative):
		return

	view = window.open_file(uri)
	state = not (relative in EnvironmentFile.from_view(view).includes)

	def when_ready():
		view.run_command("dm_internal_toggle_ticked", {"include": relative, "state": state})

	if view.is_loading():
		def wait_until_loaded():
			while view.is_loading():
				time.sleep(0.25)
			when_ready()

		threading.Thread(target=wait_until_loaded).start()
		return True
	else:
		when_ready()
		return True


def environment_path(window, of):
	folders = window.folders()
	if not folders or not utils.environment_file:
		return

	root = folders[0]
	relative = os.path.relpath(of, root)

	dme = os.path.join(root, utils.environment_file)
	return dme, relative.replace("/", "\\")


def is_tickable(include):
	return include and (include.endswith(".dm") or include.endswith(".dmm") or include.endswith(".dmf") or include.endswith(".dms"))


def toggle_ticked(edit, view, include, state):
	env = EnvironmentFile.from_view(view)
	include = include.replace("/", "\\")

	# generate the workspace edit: either insert or delete the given line
	line = len(env.header)
	for file in env.includes:
		if file == include:
			if state == True:  # keep the file even if it's already ticked
				return None
			view.erase(edit, sublime.Region(view.text_point(line, 0), view.text_point(line + 1, 0)))
			view.show_at_center(view.text_point(line, 0))
			return edit
		elif sort_less(include, file):
			break
		line += 1

	if state == False:  # don't add the file if it's already not there
		return None
	view.insert(edit, view.text_point(line, 0), "{}{}{}\n".format(EnvironmentFile.PREFIX, include, EnvironmentFile.SUFFIX))
	view.show_at_center(sublime.Region(view.text_point(line, 0), view.text_point(line + 1, 0)))
	return edit


def sort_less(a, b):
	parts_a, parts_b = a.split("\\"), b.split("\\")
	i = 0
	while True:
		part_a, part_b = parts_a[i].lower(), parts_b[i].lower()
		if i == len(parts_a) - 1 and i == len(parts_b) - 1:
			# files in the same directory sort by their extension first
			bits_a, bits_b = part_a.split("."), part_b.split(".")
			ext_a, ext_b = bits_a[-1], bits_b[-1]
			if ext_a != ext_b:
				return ext_a < ext_b
			# and then by their filename
			return part_a < part_b
		elif i == len(parts_a) - 1:
			# files sort before directories
			return True
		elif i == len(parts_b) - 1:
			# directories sort after files
			return False
		elif part_a != part_b:
			# directories sort by their name
			return part_a < part_b
		i += 1


class EnvironmentFile:
	BEGIN = "// BEGIN_INCLUDE"
	END = "// END_INCLUDE"
	PREFIX = "#include \""
	SUFFIX = "\""

	def __init__(self):
		self.header = []
		self.includes = []
		self.footer = []

	@staticmethod
	def from_view(view):
		contents = view.substr(sublime.Region(0, view.size()))
		return EnvironmentFile.from_stream(contents.splitlines())

	@staticmethod
	def from_window_and_uri(window, uri):
		# find the environment file either in the open documents or on the filesystem
		view = window.find_open_file(uri)
		if view:
			return EnvironmentFile.from_view(view)

		with open(os.path.join(window.folders()[0], uri)) as stream:
			return EnvironmentFile.from_stream(stream)

	@staticmethod
	def from_stream(input):
		input = (x.rstrip('\r\n') for x in input)
		env = EnvironmentFile()

		for line in input:
			env.header.append(line)
			if line == EnvironmentFile.BEGIN:
				break
		for line in input:
			if line == EnvironmentFile.END:
				env.footer.append(line)
				break
			elif line.startswith(EnvironmentFile.PREFIX) and line.endswith(EnvironmentFile.SUFFIX):
				env.includes.append(line[len(EnvironmentFile.PREFIX) : -len(EnvironmentFile.SUFFIX)])
			# junk lines in the INCLUDE section are discarded
		for line in input:
			env.footer.push(line)
		return env
