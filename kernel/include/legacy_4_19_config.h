#ifndef __KSU_LEGACY_4_19_CONFIG_H
#define __KSU_LEGACY_4_19_CONFIG_H

/* Override config-dependent header inlines for the late-load module only. */
#undef CONFIG_ARM64_LSE_ATOMICS
#undef CONFIG_HAVE_SYSCALL_TRACEPOINTS
#undef CONFIG_SLUB
#define CONFIG_SLOB 1

/*
 * The stock ruby kernel is built with Clang CFI.  A module that omits
 * CONFIG_CFI_CLANG gets a shorter struct module, so the kernel writes
 * cfi_check and every following field at the wrong offset.  Keep the
 * module's struct module layout identical and provide a permissive
 * __cfi_check in core/init.c so module syscall hooks are accepted by
 * __cfi_slowpath().
 */
#ifndef CONFIG_CFI_CLANG
#define CONFIG_CFI_CLANG 1
#endif

#endif
