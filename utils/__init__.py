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

# 'utils' package
import os
import stat
import sublime
import hashlib

from threading import Condition


environment_file = None


def is_executable(path):
	req = stat.S_IXUSR | stat.S_IRUSR
	try:
		return (os.stat(path).st_mode & req) == req
	except FileNotFoundError:
		return False


def md5_file(path):
	h = hashlib.new('md5')
	with open(path, 'rb') as f:
		h.update(f.read())
	return h.hexdigest()


def extension_path():
	return os.path.split(os.path.split(__file__)[0])[0]


def get_config(name, default=None):
	return sublime.load_settings("dreammaker.sublime-settings").get("dreammaker." + name, default)


def set_config(name, value):
	return sublime.load_settings("dreammaker.sublime-settings").set("dreammaker." + name, value)


class Promise():
	def __init__(self):
		self.cv = Condition()

	def notify(self, *args):
		with self.cv:
			self.result = args
			self.cv.notify()

	def wait(self):
		with self.cv:
			self.cv.wait()
			return self.result
