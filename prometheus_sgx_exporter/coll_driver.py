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
