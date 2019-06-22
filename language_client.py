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

from .utils import *


default_name = 'dreammaker'

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


def plugin_loaded():
	print("Extension path:", extension_path())
	Thread(target=prepare_server_thread).start()


def prepare_server_thread():
	cmd = determine_server_command()
	print("Command:", cmd)
	default_config.binary_args[0] = cmd


	# // prepare the status bar
	# status = window.createStatusBarItem(StatusBarAlignment.Left, 10);
	# status.text = "DM: starting";
	# status.command = 'dreammaker.restartLangserver';
	# status.show();

	# ticked_status = window.createStatusBarItem(StatusBarAlignment.Right, 100);
	# ticked_status.command = 'dreammaker.toggleTicked';
	# context.subscriptions.push(window.onDidChangeActiveTextEditor(update_ticked_status));
	# update_ticked_status();


###############################################################################
# LSP Integration

class LspDreammakerPlugin(LanguageHandler):
	def __init__(self):
		print("LSP __init__")
		self._name = default_name
		self._config = default_config

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
		print("on_initialized")
		pass # extra initialization here.


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
		if not is_executable(update_file):
			return
		try:
			shutil.move(update_file, main_file)
			return
		except:
			pass
		# If this fails, it might be because the old process is still
		# running in this window. Wait a bit and try again.
		sleep(0.25)
	# Last chance, and if it really fails, propagate that up
	shutil.move(update_file, main_file)


def lock_and_notify(cv):
	with cv:
		cv.notify()


def prompt_for_server_command(message):
	promise = Promise()
	sublime.active_window().show_quick_panel(
		["The dm-langserver executable must be selected.", message],
		promise.notify,
		sublime.KEEP_OPEN_ON_FOCUS_LOST,
		0,
	)
	index, = promise.wait()
	if index < 0:
		return

	path = None # TODO: file chooser
	if not path:
		return

	set_config('langserverPath', path)
	return path


def is_executable(path):
	req = stat.S_IXUSR | stat.S_IRUSR
	try:
		return (os.stat(path).st_mode & req) == req
	except FileNotFoundError:
		return False


def config_auto_update():
	choice = get_config('autoUpdate')
	if choice is not None:
		return choice

	promise = Promise()
	sublime.active_window().show_quick_panel(
		[
			"Enable dm-langserver auto-updates.",
			"Update dm-langserver just once.",
			"Disable dm-langserver updates.",
		],
		promise.notify,
		sublime.KEEP_OPEN_ON_FOCUS_LOST,
	)
	index, = promise.wait()

	if index == 0:
		set_config('autoUpdate', True)
		return True
	elif index == 1:
		set_config('autoUpdate', False)
		return True
	elif index == 2:
		set_config('autoUpdate', False)
		return False
	else:
		return False


def auto_update(platform, arch, out_file, hash):
	if not config_auto_update():
		return "Auto-update dsiabled."

	url = "https://wombat.platymuus.com/ss13/dm-langserver/update.php?platform={}&arch={}".format(platform, arch)
	if hash:
		url += "&hash={}".format(hash)

	try:
		res = urllib.request.urlopen(url)
	except e:
		return "{}.".format(e)

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

		# TODO: announce update is available
		# if (hash && !update_available) {
		# 	update_available = true;
		# 	status.text += ' - click to update';
		# }
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
