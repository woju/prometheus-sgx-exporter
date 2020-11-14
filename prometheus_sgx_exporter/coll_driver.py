# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2020 Wojtek Porczyk <woju@invisiblethingslab.com>

import pathlib

SGX_DRIVER_PATHS = {
    'inkernel': pathlib.Path('/dev/sgx_enclave'),
    'dcap': pathlib.Path('/dev/sgx/enclave'),
    'oot': pathlib.Path('/dev/isgx'),
}

def coll_driver():
    for driver, path in SGX_DRIVER_PATHS.items():
        state = path.is_char_device() and not path.is_symlink()
        yield 'sgx_driver{{type="{}"}} {}'.format(driver, int(state))

# vim: tw=80
