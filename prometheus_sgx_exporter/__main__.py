# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2020 Wojtek Porczyk <woju@invisiblethingslab.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

#
# NOTE: this file has to be compatible with python-3.5 (xenial)
# pylint: disable=too-few-public-methods,too-many-instance-attributes
#

import http.server
import itertools

import click

from .coll_cpuid import coll_cpuid
from .coll_driver import coll_driver
from .coll_aesmd import coll_aesmd

def render():
    return '\n'.join(itertools.chain(
        coll_cpuid(),
        coll_driver(),
        coll_aesmd(),
    ))

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self): # pylint: disable=invalid-name
        resp = (render() + '\n').encode('ascii')
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.send_header('Content-length', len(resp))
        self.end_headers()
        self.wfile.write(resp)

@click.group(invoke_without_command=True)
@click.option('--listen', default=':9086')
@click.pass_context
def main(ctx, listen):
    if ctx.invoked_subcommand is not None:
        return
    host, port = listen.split(':')
    port = int(port)
    http.server.HTTPServer((host, port), Handler).serve_forever()

@main.command('test')
def main_test():
    print(render())

if __name__ == '__main__':
    main() # pylint: disable=no-value-for-parameter

# vim: tw=80
