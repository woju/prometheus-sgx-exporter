# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2020 Wojtek Porczyk <woju@invisiblethingslab.com>

import os
import pathlib
import socket

from cryptography.hazmat.backends import default_backend as _default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

from . import aesm_pb2

fspath = getattr(os, 'fspath', str)  # pylint: disable=invalid-name

ATTRIBUTES = bytes.fromhex('0600000000000000 1f00000000000000') # flags, xfrm
AESMD_SOCKET = pathlib.Path('/var/run/aesmd/aesm.socket')

_backend = _default_backend() # pylint: disable=invalid-name

def get_token():
    mrenclave = os.urandom(32)
    key = rsa.generate_private_key(
        public_exponent=3, key_size=3072, backend=_backend)
    modulus = key.public_key().public_numbers().n.to_bytes(384, 'little')

    req = aesm_pb2.GetTokenReq(req=aesm_pb2.GetTokenReqRaw(
        signature=mrenclave,
        key=modulus,
        attributes=ATTRIBUTES,
        timeout=10000)).SerializeToString()

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(fspath(AESMD_SOCKET))
    sock.send(len(req).to_bytes(4, 'little'))
    sock.send(req)

    ret = aesm_pb2.GetTokenRet()
    ret_len = int.from_bytes(sock.recv(4), 'little')
    ret.ParseFromString(sock.recv(ret_len))

    return ret.ret.error

def coll_aesmd():
    try:
        error = get_token()
        aesmd_serviceable = error == 0
        yield 'aesmd_up 1'
        yield 'aesmd_serviceable {}'.format(int(aesmd_serviceable))
        yield '#aesmd_error {}'.format(error)
    except FileNotFoundError:
        # connect() failed, not running
        yield '# aesmd: file not found'
        yield 'aesmd_up 0'
        yield 'aesmd_serviceable 0'

# vim: tw=80
