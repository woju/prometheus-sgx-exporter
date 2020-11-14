import setuptools
from prometheus_sgx_exporter import __version__ as _version

setuptools.setup(
    name='prometheus_sgx_exporter',
    version=_version,
    packages=setuptools.find_packages(),
    ext_modules=[
        setuptools.Extension('prometheus_sgx_exporter._cpuid',
            sources=['prometheus_sgx_exporter/_cpuidmodule.c'],
            extra_compile_args=['-masm=intel', '-Werror'],
        ),
    ],
    data_files=[
        ('lib/systemd/system', ['prometheus-sgx-exporter.service']),
    ],
    entry_points={
        'console_scripts': [
            'prometheus-sgx-exporter = prometheus_sgx_exporter.__main__:main',
        ],
    },
)
