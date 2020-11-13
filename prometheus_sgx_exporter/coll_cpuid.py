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

# pylint: disable=too-few-public-methods,too-many-instance-attributes

import collections
import ctypes
import itertools
import mmap

class CPUIDStruct(ctypes.Structure):
    _fields_ = [
        ('eax', ctypes.c_uint32),
        ('ebx', ctypes.c_uint32),
        ('ecx', ctypes.c_uint32),
        ('edx', ctypes.c_uint32),
    ]

class CPUIDResult(collections.namedtuple('_CPUIDResult', (
    'eax',
    'ebx',
    'ecx',
    'edx',
))):
    @classmethod
    def from_struct(cls, cpuid_struct):
        return cls(
            cpuid_struct.eax,
            cpuid_struct.ebx,
            cpuid_struct.ecx,
            cpuid_struct.edx,
        )

    def __repr__(self):
        return ('{}(eax={:#010x}, ebx={:#010x}, ecx={:#010x}, edx={:#010x})'.format(
            type(self).__name__, self.eax, self.ebx, self.ecx, self.edx))

class CPUID:
    class Bit(collections.namedtuple('_Bit', (
        'leaf',
        'subleaf',
        'reg',
        'bit',
    ))):
        def query(self, cpuid):
            if cpuid.maxleaf < self.leaf:
                return None
            return bool(getattr(cpuid[self.leaf, self.subleaf], self.reg) & (1 << self.bit))

    caps = {
        'is_sgx_supported': Bit(0x7, 0x0, 'ebx', 2),
        'is_flc_supported': Bit(0x7, 0x0, 'ecx', 30),
        'is_sgx1_supported': Bit(0x12, 0x0, 'eax', 0),
        'is_sgx2_supported': Bit(0x12, 0x0, 'eax', 1),
        'is_sgx_virt_supported': Bit(0x12, 0x0, 'eax', 1),
        'is_sgx_mem_concurrency_supported': Bit(0x12, 0, 'eax', 6),
        'is_cet_supported': Bit(0x12, 0x1, 'eax', 6),
        'is_kss_supported': Bit(0x12, 0x1, 'eax', 7),
    }

    def __init__(self):
        self.is_cpuid_supported = None
        self.vendor_id = ''
        self.is_intel_cpu = None
        self.max_enclave_size_32 = 0
        self.max_enclave_size_64 = 0
        self.epc_size = 0

        self.is_cpuid_supported = self._is_cpuid_supported()
        if not self.is_cpuid_supported:
            for cap in self.caps:
                setattr(self, cap, None)
            return

        self._cache = {}

        result = self[0x0, 0x0]
        self.maxleaf = result.eax

        for cap, bit in self.caps.items():
            setattr(self, cap, bit.query(self))

        self.vendor_id = b''.join(reg.to_bytes(4, 'little')
            for reg in (result.ebx, result.edx, result.ecx)).decode()
        self.is_intel_cpu = self.vendor_id == 'GenuineIntel'

        if self.is_sgx_supported and self.maxleaf >= 0x12: # pylint: disable=no-member
            cpuid_12_0_edx = self[0x12, 0x0].edx
            self.max_enclave_size_32 = 1 << (cpuid_12_0_edx & 0xff)
            self.max_enclave_size_64 = 1 << ((cpuid_12_0_edx >> 8) & 0xff)

        for subleaf in itertools.count(0x2):
            result = self[0x12, subleaf]
            typ = result.eax & 0xf
            if not typ:
                break
            if typ == 1:
                self.epc_size += result.ecx & 0xfffff000
                self.epc_size += (result.edx & 0xfffff) << 32


    @staticmethod
    def _is_cpuid_supported():
        buf = mmap.mmap(-1, mmap.PAGESIZE, prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC)
        buf.write(bytes.fromhex(
            '9c'                        # pushf
            '9c'                        # pushf
            '48 81 34 24 00 00 20 00'   # xor QWORD PTR [rsp],0x200000
            '9d'                        # popf
            '9c'                        # pushf
            '58'                        # pop rax
            '48 33 04 24'               # xor rax,QWORD PTR [rsp]
            '9d'                        # popf
            'c3'                        # ret
        ))

        ftype = ctypes.CFUNCTYPE(ctypes.c_int)
        fptr = ctypes.c_void_p.from_buffer(buf)
        func = ftype(ctypes.addressof(fptr))
        ret = func()
        del fptr
        buf.close()
        return bool(ret)

    def __getitem__(self, key):
        if not key in self._cache:
            leaf, subleaf = key # throw TypeError early on invalid signature

            buf = mmap.mmap(-1, mmap.PAGESIZE,
                prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC)
            buf.write(bytes.fromhex(
                '53'        # push rbx
                '89 f0'     # mov eax, esi
                '89 d1'     # mov ecx, edx
                '0f a2'     # cpuid
                '89 07'     # mov [rdi], eax
                '89 5f 04'  # mov [rdi + 0x4], ebx
                '89 4f 08'  # mov [rdi + 0x8], ecx
                '89 57 0c'  # mov [rdi + 0xc], edx
                '5b'        # pop rbx
                'c3'        # ret
            ))

            ftype = ctypes.CFUNCTYPE(None,
                ctypes.POINTER(CPUIDStruct), ctypes.c_uint32, ctypes.c_uint32)
            fptr = ctypes.c_void_p.from_buffer(buf)
            func = ftype(ctypes.addressof(fptr))

            cpuid_struct = CPUIDStruct()
            func(cpuid_struct, leaf, subleaf)
            del fptr
            buf.close()
            self._cache[key] = CPUIDResult.from_struct(cpuid_struct)
        return self._cache[key]


def coll_cpuid():
    cpuid = CPUID()
    yield 'cpuid_is_cpuid_supported {}'.format(
        int(cpuid.is_cpuid_supported))
    yield 'cpuid_is_intel_cpu{{vendor_id="{}"}} {}'.format(
        cpuid.vendor_id, int(cpuid.is_cpuid_supported))
    yield 'cpuid_max_enclave_size_bytes{{arch="x86"}} {:#x}'.format(
        cpuid.max_enclave_size_32)
    yield 'cpuid_max_enclave_size_bytes{{arch="x86_64"}} {:#x}'.format(
        cpuid.max_enclave_size_64)
    yield 'cpuid_epc_size_bytes {:#x}'.format(
        cpuid.epc_size)

    for cap in cpuid.caps:
        yield 'cpuid_{} {}'.format(cap, int(bool(getattr(cpuid, cap))))

# vim: tw=80
