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

# language_client.py - LSP provider with DMLS updates and extensions.

import os
import stat
import gzip
import shutil
import urllib
import sublime, sublime_plugin

from threading import Thread
from LSP.plugin.core.handlers import LanguageHandler
from LSP.plugin.core.settings import ClientConfig, LanguageConfig

from time import sleep

from . import utils
from .utils import *


default_name = 'dm-langserver'

default_config = ClientConfig(
	name=default_name,
	binary_args=[None],
	tcp_port=None,
	enabled=True,
	init_options=dict(),
	settings=dict(),
	env=dict(),
	languages=[
		LanguageConfig(
			'dreammaker',
			['source.dm'],
			["Packages/DreamMaker Language Client/dreammaker.tmLanguage"]
		),
	]
)

update_available = False
status_text = 'DM: Starting...'


def plugin_loaded():
	sublime.active_window().status_message(status_text)
	Thread(target=prepare_server_thread).start()


def prepare_server_thread():
	default_config.binary_args[0] = determine_server_command()


###############################################################################
# LSP Integration

class LspDreammakerPlugin(LanguageHandler):
	client = None

	def __init__(self):
		self._name = default_name
		self._config = default_config
		self.environment = "DM"

	@property
	def name(self) -> str:
		return self._name

	@property
	def config(self) -> ClientConfig:
		return self._config

	def on_start(self, window) -> bool:
		# Still waiting on prepare_server_thread to finish.
		if not default_config.binary_args[0]:
			# When we return False, it seems that LSP will call us again later,
			# so we have an opportunity to continue configuring.
			return False

		return True

	def on_initialized(self, client) -> None:
		LspDreammakerPlugin.client = client

		# Add handlers for the extension methods.
		client.on_notification('$window/status', self.on_window_status)

		try:
			from . import object_tree
		except ImportError:
			pass
		else:
			object_tree.on_initialized(client)

	def on_window_status(self, message):
		global status_text
		if message['environment']:
			self.environment = message['environment']
			utils.environment_file = "{}.dme".format(self.environment)
			try:
				from . import toggle_ticked
			except ImportError:
				pass
			else:
				window = sublime.active_window()
				view = window and window.active_view()
				view and toggle_ticked.update_ticked_status(view)

		tasks = message['tasks'] or []
		if not tasks:
			status_text = "{}: ready".format(self.environment)
		elif len(tasks) == 1:
			element = tasks[0]
			status_text = "{}: {}".format(self.environment, element)

			# // Special handling for the "no .dme file" error message.
			# if (element == "no .dme file") {
			# 	status.tooltip = "Open Folder the directory containing your .dme file";
			# 	status.command = 'vscode.openFolder';
			# 	await lc.stop();
			# 	let result = await window.showInformationMessage("The DreamMaker language server requires access to your project's `.dme` file. Please use the \"Open Folder\" command to open the folder which contains it.", "Open Folder");
			# 	if (result === "Open Folder") {
			# 		await commands.executeCommand('vscode.openFolder');
			# 	}
			# }
		else:
			status_text = "{} ({}): {}".format(environment, len(tasks), "; ".join(tasks))

		if update_available:
			status_text += ' - update ready'

		sublime.active_window().status_message(status_text)


###############################################################################
# Server command lookup and autoupdater


def determine_server_command():
	# If the config override is set, use that, and don't autoupdate.
	server_command = get_config('langserverPath')
	if server_command:
		# ".update" files are still supported here to allow easy updating of
		# local builds.
		update_copy(server_command, "{}.update".format(server_command))
		if is_executable(server_command):
			return server_command
		else:
			return prompt_for_server_command("Configured executable is missing or invalid.")

	# Nothing is set in the config.
	arch = sublime.arch()
	platform = {"windows": "win32", "osx": "darwin", "linux": "linux"}[sublime.platform()]
	extension = ".exe" if platform == "win32" else ""
	auto_file = "{}/bin/dm-langserver-{}-{}{}".format(extension_path(), arch, platform, extension)
	update_file = "{}.update".format(auto_file)
	update_copy(auto_file, update_file)

	if is_executable(auto_file):
		# If the executable is already valid, run it now, and update later.
		Thread(target=lambda: auto_update(platform, arch, update_file, md5_file(auto_file))).start()
	else:
		# Otherwise, update now.
		os.makedirs("{}/bin".format(extension_path()), exist_ok=True)
		failure = auto_update(platform, arch, auto_file, None)
		if failure:
			return prompt_for_server_command(failure)

		# Debounce to handle the file being busy if accessed by antivirus or
		# similar immediately after download.
		sleep(0.5)

	return auto_file


def update_copy(main_file, update_file):
	for _ in range(8):
		if not os.path.exists(update_file):
			return
		try:
			os.replace(update_file, main_file)
			return
		except:
			pass
		# If this fails, it might be because the old process is still
		# running in this window. Wait a bit and try again.
		sleep(0.25)
	# Last chance, and if it really fails, propagate that up
	os.replace(update_file, main_file)


def lock_and_notify(cv):
	with cv:
		cv.notify()


def prompt_for_server_command(message):
	message = "The dm-langserver executable must be specified.\n\n{}".format(message)

	opened = False
	current = utils.get_config('langserverPath')
	while not current or not is_executable(current):
		if not sublime.ok_cancel_dialog(message, "Edit"):
			return

		if not opened:
			utils.open_config()
			opened = True

		while utils.get_config('langserverPath') == current:
			sleep(1)

		current = utils.get_config('langserverPath')
		message = "The specified path is not a valid executable."

	return current


def config_auto_update(hash):
	choice = get_config('autoUpdate')
	if choice is not None:
		return choice

	if hash:
		choices = [
			"Enable dm-langserver updates (recommended).",
			"Disable dm-langserver updates.",
		]
		choice_actions = ['yes', 'no']
	else:
		choices = [
			"Install dm-langserver now and enable updates (recommended).",
			"Install dm-langserver now, but disable updates.",
			"Manually select dm-langserver executable.",
		]
		choice_actions = ['yes', 'once', 'no']

	promise = Promise()
	sublime.active_window().show_quick_panel(
		choices,
		promise.notify,
		sublime.KEEP_OPEN_ON_FOCUS_LOST,
	)
	index, = promise.wait()

	if index < 0:
		# cancel = do nothing, but ask again later
		return False

	act = choice_actions[index]
	if act == 'yes':
		set_config('autoUpdate', True)
		return True
	elif act == 'once':
		set_config('autoUpdate', False)
		return True
	elif act == 'no':
		set_config('autoUpdate', False)
		return False


def auto_update(platform, arch, out_file, hash):
	global status_text, update_available

	if not config_auto_update(hash):
		return "Auto-update disabled."

	url = "https://wombat.platymuus.com/ss13/dm-langserver/update.php?platform={}&arch={}".format(platform, arch)
	if hash:
		url += "&hash={}".format(hash)

	try:
		res = urllib.request.urlopen(url)
	except Exception as e:
		return "{}.".format(e)

	print('dm-langserver updater:', res.status, res.reason)
	if res.status == 200:  # New version
		with open(out_file, "wb") as stream:
			encoding = res.headers.get('Content-encoding')
			if encoding == 'gzip':
				with gzip.open(res) as gz:
					stream.write(gz.read())
			elif encoding is None:
				with res:
					stream.write(res.read())
			else:
				return "Unknown Content-encoding: {}".format(encoding)

		# mark the file as executable
		mode = os.stat(out_file).st_mode
		mode |= stat.S_IXUSR
		os.chmod(out_file, mode)

		if hash:
			if not update_available:
				update_available = True
				status_text += " - update ready"
			sublime.active_window().status_message(status_text)
		return

	elif res.status in (204, 304):  # Unmodified
		if hash:
			return
		return "Binaries are not available for {}-{}.".format(arch, platform)

	elif res.status == 404:  # Not found
		return "Binaries are not available for {}-{}.".format(arch, platform)

	elif res.status == 410:  # Endpoint removed
		set_config('autoUpdate', False)
		return "Update endpoint removed, try updating the extension."

	else:  # Error
		return "Server returned {} {}.".format(res.status, res.reason)
