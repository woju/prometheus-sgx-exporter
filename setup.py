import setuptools
setuptools.setup(
    ext_modules=[
        setuptools.Extension('prometheus_sgx_exporter._cpuid',
            sources=['prometheus_sgx_exporter/_cpuidmodule.c'],
            extra_compile_args=['-masm=intel', '-Werror'],
        ),
    ],
)
