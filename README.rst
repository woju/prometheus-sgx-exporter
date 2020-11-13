prometheus-sgx-exporter
=======================

Supported: Python >= 3.5, Ubuntu >= 16.04 (only LTS), Debian >= 10.

Installation
------------

.. code-block:: sh

   sudo python3 -m pip install --prefix /usr .
   sudo systemctl start prometheus-sgx-exporter
   sudo systemctl enable prometheus-sgx-exporter

Testing
-------

For one-off test, to see how the response gets rendered:

.. code-block:: sh

   prometheus-sgx-exporter test
   # or without installing
   python3 -m prometheus_sgx_exporter test

Copyright
---------

| Copyright © 2020 Wojtek Porczyk <woju invisiblethingslab com>.
| Licenced under AGPLv3 or later.
