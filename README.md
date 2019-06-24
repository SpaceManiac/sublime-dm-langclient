# DreamMaker Language Client

This [Sublime Text 3][st3] package acts as a client to the
[DreamMaker language server][ls], a component of [SpacemanDMM]. It provides
language-related services for DreamMaker, the scripting language of the [BYOND]
engine.

The extension has an optional auto-update feature for the language server, with
binaries available for Windows and Linux. On other platforms, the path to the
`dm-langserver` binary may be specified manually.

[st3]: https://www.sublimetext.com/
[ls]: https://github.com/SpaceManiac/SpacemanDMM/tree/master/src/langserver#dreammaker-language-server
[SpacemanDMM]: https://github.com/Spacemaniac/SpacemanDMM/
[BYOND]: https://secure.byond.com/

## Features

* Diagnostics, Go To Definition, Find All References and more provided by the
  [language server][ls].
* Syntax highlighting for the DreamMaker language.
* Build task (Ctrl+B) support for invoking DreamMaker. Supports Windows native,
  Linux native, and Wine.
* Status bar indicator and command to toggle a file's tickmark in the `.dme`
  ("DreamMaker: Toggle Tick").
* Built-in DM Reference browser ("DreamMaker: Open DM Reference").
* DM object tree browser ("DreamMaker: Open Object Tree").

## Installation

1. Install [Package Control].
2. Use "Package Control: Install Package" to install "[LSP]".
3. Use "Package Control: Install Package" to install
   "[DreamMaker Language Client][dmlc]".

To use unreleased versions:

1. Use [Package Control] or otherwise install [LSP].
2. Navigate to the directory revealed by "Preferences > Browse Packages...".
3. Run `git clone https://github.com/SpaceManiac/sublime-dm-langclient "DreamMaker Language Client"`

[Package Control]: https://packagecontrol.io/installation
[LSP]: https://packagecontrol.io/packages/LSP
[dmlc]: https://packagecontrol.io/packages/DreamMaker%20Language%20Client

## License

DreamMaker Language Client is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

DreamMaker Language Client is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with DreamMaker Language Client.  If not, see <http://www.gnu.org/licenses/>.
