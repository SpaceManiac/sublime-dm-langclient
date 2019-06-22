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

import os
import threading
import subprocess

import sublime, sublime_plugin

from . import utils


PANEL_ID = "DreamMaker Build"


# Based on https://www.sublimetext.com/docs/3/build_systems.html
class DreammakerBuildCommand(sublime_plugin.WindowCommand):
	encoding = 'utf-8'
	killed = False
	proc = None
	panel = None
	panel_lock = threading.Lock()

	def is_enabled(self, kill=False):
		# Kill option only available when running.
		if kill:
			return self.proc is not None and self.proc.poll() is None
		return True

	def run(self, kill=False):
		if kill:
			if self.proc:
				self.killed = True
				self.proc.terminate()
			return

		vars = self.window.extract_variables()
		working_dir = vars['folder']

		exe = utils.find_executable(["dm.exe", "DreamMaker"])
		if exe is None:
			sublime.error_message('You must configure "dreammaker.byondPath" to point to a valid BYOND installation.')
			return

		dme = "byond.dme"
		if dme is None:
			sublime.error_message('No DME file')
			return

		with self.panel_lock:
			self.panel = self.window.create_output_panel(PANEL_ID)

			settings = self.panel.settings()
			settings.set(
				'result_file_regex',
				"^([^:]+):(\\d+):([^:]+): (.*)$"
			)
			settings.set('result_base_dir', working_dir)

			self.window.run_command('show_panel', {'panel': 'output.{}'.format(PANEL_ID)})

		if self.proc is not None:
			try:
				self.proc.terminate()
			except ProcessLookupError:
				pass
			self.proc = None

		args = [exe, dme]
		env = {}
		if sublime.platform() != 'windows':
			env['LD_LIBRARY_PATH'] = os.path.split(exe)[0]

		self.do_write('-- {}\n'.format(' '.join(args)))
		self.proc = subprocess.Popen(
			args,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			cwd=working_dir,
			env=env,
		)
		self.killed = False

		threading.Thread(
			target=self.read_handle,
			args=(self.proc.stdout,)
		).start()

	def read_handle(self, handle):
		chunk_size = 2 ** 13
		out = b''
		while True:
			try:
				data = os.read(handle.fileno(), chunk_size)
				# If exactly the requested number of bytes was
				# read, there may be more data, and the current
				# data may contain part of a multibyte char
				out += data
				if len(data) == chunk_size:
					continue
				if data == b'' and out == b'':
					raise IOError('EOF')
				# We pass out to a function to ensure the
				# timeout gets the value of out right now,
				# rather than a future (mutated) version
				self.queue_write(out.decode(self.encoding))
				if data == b'':
					raise IOError('EOF')
				out = b''
			except (UnicodeDecodeError) as e:
				msg = 'Error decoding output using %s - %s'
				self.queue_write(msg  % (self.encoding, str(e)))
				break
			except (IOError):
				if self.killed:
					msg = 'Cancelled'
				else:
					msg = 'Finished'
				self.queue_write('-- %s' % msg)
				break

	def queue_write(self, text):
		sublime.set_timeout(lambda: self.do_write(text), 1)

	def do_write(self, text):
		text = text.replace('\r', '')  # for Wine
		with self.panel_lock:
			self.panel.run_command('append', {'characters': text})
