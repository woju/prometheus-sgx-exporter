# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2020 Wojtek Porczyk <woju@invisiblethingslab.com>
# pylint: disable=too-few-public-methods,too-many-instance-attributes

import collections
import ctypes
import itertools
import mmap

from . import _cpuid

class CPUID:
    class Bit(collections.namedtuple('_Bit', (
        'leaf',
        'subleaf',
        'reg',
        'bit',
    ))):
        def query(self, cpuid):
            try:
                return bool(
                    getattr(_cpuid.cpuid(self.leaf, self.subleaf), self.reg)
                        & (1 << self.bit))
            except _cpuid.CPUIDLeafNotSupportedError:
                return None

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

        try:
            cpuid_0_0 = _cpuid.cpuid(0x0, 0x0)

        except _cpuid.CPUIDNotSupportedError:
            self.is_cpuid_supported = False
            if not self.is_cpuid_supported:
                for cap in self.caps:
                    setattr(self, cap, None)
                return

        self.is_cpuid_supported = True
        self.vendor_id = b''.join(reg.to_bytes(4, 'little')
            for reg in cpuid_0_0[1:]).decode()
        self.is_intel_cpu = self.vendor_id == 'GenuineIntel'
        del cpuid_0_0

        for cap, bit in self.caps.items():
            setattr(self, cap, bit.query(self))

        if _cpuid.CPUID_MAXLEAF >= 0x12:
            cpuid_12_0_edx = _cpuid.cpuid(0x12, 0x0).edx
            self.max_enclave_size_32 = 1 << (cpuid_12_0_edx & 0xff)
            self.max_enclave_size_64 = 1 << ((cpuid_12_0_edx >> 8) & 0xff)

            for subleaf in itertools.count(0x2):
                result = _cpuid.cpuid(0x12, subleaf)
                typ = result.eax & 0xf
                if not typ:
                    break
                if typ == 1:
                    self.epc_size += result.ecx & 0xfffff000
                    self.epc_size += (result.edx & 0xfffff) << 32

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
