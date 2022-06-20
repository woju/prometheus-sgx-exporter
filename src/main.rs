use std::arch::asm;

fn is_cpuid_supported() -> bool {
    let flagdiff: u64;
    unsafe {
        asm!("
            pushf
            pushf
            xor qword ptr [rsp], (1 << 21)
            popf
            pushf
            pop {}
            xor {}, [rsp]
            popf
        ",
            lateout(reg) => flagdiff,
            options(nomem, preserves_flags),
        );
    }
    flagdiff == (1 << 21)
}

fn main() {
    dbg!(is_cpuid_supported());
}
