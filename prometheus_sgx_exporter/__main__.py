# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2020 Wojtek Porczyk <woju@invisiblethingslab.com>
# pylint: disable=too-few-public-methods,too-many-instance-attributes

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
@click.option('--listen', default=':9765')
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
