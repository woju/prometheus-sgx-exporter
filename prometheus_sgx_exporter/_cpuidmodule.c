/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Copyright (c) 2020 Wojtek Porczyk <woju@invisiblethingslab.com>
 * Copyright (c) 2018-2020 Invisible Things Lab
 *                         Michal Kowalczyk <mkow@invisiblethingslab.com>
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>


static uint32_t maxleaf;
struct cpuidr {
    uint32_t eax, ebx, ecx, edx;
};

static int is_cpuid_supported(void)
{
    // Checks whether (R/E)FLAGS.ID is writable (bit 21).
    uint64_t write_diff;
    __asm__ (
        "pushf\n"

        "pushf\n"
        "xor qword ptr [rsp], (1 << 21)\n"
        "popf\n"
        "pushf\n"
        "pop %0\n"
        "xor %0, [rsp]\n"

        "popf\n"
        : "=r" (write_diff)
    );
    return write_diff == (1 << 21);
}

static void cpuid(struct cpuidr *res, uint32_t leaf, uint32_t subleaf)
{
    if (!res) {
        return;
    }
    __asm__ ("cpuid\n"
        :
            "=a" (res->eax),
            "=b" (res->ebx),
            "=d" (res->edx),
            "=c" (res->ecx)
        :
            "a" (leaf),
            "c" (subleaf));
}


PyDoc_STRVAR(CPUIDNotSupportedError_doc,
"Raised when CPUID is not supported.");
static PyObject *CPUIDNotSupportedError;

PyDoc_STRVAR(CPUIDLeafNotSupportedError_doc,
"Raised when CPUID leaf is greater than maxleaf.");
static PyObject *CPUIDLeafNotSupportedError;

PyDoc_STRVAR(cpuid_result_doc, 
"cpuid_result: Result from cpuid().\n\
\n\
This object may be accessed either as tuple of (eax, ebc, edx, ecx),\n\
or via the attributes eax, ebc, edx, ecx. Note the order.\n\
\n\
See cpuid for more information.");
static PyStructSequence_Field cpuid_result_fields[] = {
    {"eax", "EAX register value"},
    {"ebx", "EBX register value"},
    {"edx", "EDX register value"},
    {"ecx", "ECX register value"},
    {NULL, NULL}
};
static PyStructSequence_Desc cpuid_result_desc __attribute__((__unused__)) = {
    .name = "cpuid_result",
    .doc = cpuid_result_doc,
    .fields = cpuid_result_fields,
    .n_in_sequence = 4,
};

static PyTypeObject cpuid_result;

PyDoc_STRVAR(cpuid_cpuid_doc, 
"cpuid(leaf, subleaf, /) -> cpuid_result\n\
\n\
Execute CPUID.\n\
\n\
Raise CPUIDNotSupportedError if CPUID instruction is not supported.\n\
Raise CPUIDLeafNotSupportedError if a particular CPUID leaf is not supported.");
static PyObject *cpuid_cpuid(PyObject *self, PyObject *args)
{
    uint32_t leaf, subleaf;
    if (!PyArg_ParseTuple(args, "II", &leaf, &subleaf))
        return NULL;

    if (leaf > maxleaf) {
        PyErr_Format(CPUIDLeafNotSupportedError,
            "leaf is greater than CPUID_MAXLEAF (%d)", maxleaf);
        return NULL;
    }

    struct cpuidr result;
    cpuid(&result, leaf, subleaf);

    PyObject *ret = PyStructSequence_New(&cpuid_result);
    if (ret == NULL)
        return NULL;

#define CPUID_RESULT_SET_ITEM(pos, reg) \
    do { \
        PyObject *v = PyLong_FromUnsignedLong(reg); \
        if (v == NULL) { \
            Py_DECREF(ret); \
            return NULL; \
        } \
        PyStructSequence_SetItem(ret, (pos), v); \
    } while (0)

    CPUID_RESULT_SET_ITEM(0, result.eax);
    CPUID_RESULT_SET_ITEM(1, result.ebx);
    CPUID_RESULT_SET_ITEM(2, result.edx);
    CPUID_RESULT_SET_ITEM(3, result.ecx);

    return ret;
}

static PyObject *cpuid_dummy(PyObject *self, PyObject *args)
{
    if (!PyArg_ParseTuple(args, "II", NULL, NULL)) {
        return NULL;
    }

    PyErr_SetString(CPUIDNotSupportedError, "CPUID not supported");
    return NULL;
}

static PyMethodDef cpuid_methods[] = {
    {"cpuid", cpuid_cpuid, METH_VARARGS, cpuid_cpuid_doc},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef cpuidmodule = {
    PyModuleDef_HEAD_INIT,
    .m_name = "_cpuid",
    .m_doc = NULL, /* TODO */
    .m_size = -1,
    .m_methods = cpuid_methods,
};

PyMODINIT_FUNC PyInit__cpuid(void)
{
    if (!is_cpuid_supported()) {
        cpuid_methods[0].ml_meth = &cpuid_dummy;
    }

    PyObject *m = PyModule_Create(&cpuidmodule);
    if (m == NULL)
        goto err_return;

    CPUIDNotSupportedError = PyErr_NewExceptionWithDoc(
        "cpuid.CPUIDNotSupportedError", CPUIDNotSupportedError_doc, NULL, NULL);
    if (CPUIDNotSupportedError == NULL)
        goto err_decref_m;

    Py_XINCREF(CPUIDNotSupportedError);
    if (PyModule_AddObject(m,
            "CPUIDNotSupportedError", CPUIDNotSupportedError) < 0)
        goto err_decref_cnse;

    PyObject *bases = Py_BuildValue("O", PyExc_ValueError);
    if (bases == NULL)
        goto err_decref_cnse;

    CPUIDLeafNotSupportedError = PyErr_NewExceptionWithDoc(
        "cpuid.CPUIDUnsupportedLeafError", CPUIDLeafNotSupportedError_doc,
        bases, NULL);
    Py_DECREF(bases);
    if (CPUIDLeafNotSupportedError == NULL)
        goto err_decref_cnse;

    Py_XINCREF(CPUIDNotSupportedError);
    if (PyModule_AddObject(m,
            "CPUIDLeafNotSupportedError", CPUIDLeafNotSupportedError) < 0)
        goto err_decref_clnse;

    if (PyStructSequence_InitType2(&cpuid_result, &cpuid_result_desc) < 0)
        goto err_decref_clnse;
    if (PyModule_AddObject(m, "cpuid_result", (PyObject *)&cpuid_result) < 0)
        goto err_decref_clnse;

    struct cpuidr result;
    cpuid(&result, 0x0, 0x0);
    maxleaf = result.eax;
    if (PyModule_AddIntConstant(m, "CPUID_MAXLEAF", maxleaf) < 0)
        goto err_decref_clnse;

    return m;

err_decref_clnse:
    Py_XDECREF(CPUIDLeafNotSupportedError);
    Py_CLEAR(CPUIDLeafNotSupportedError);
err_decref_cnse:
    Py_XDECREF(CPUIDNotSupportedError);
    Py_CLEAR(CPUIDNotSupportedError);
err_decref_m:
    Py_DECREF(m);
err_return:
    return NULL;
}

/* vim: set tw=80 : */
