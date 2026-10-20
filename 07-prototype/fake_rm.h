/* Synthetic payload generator, not an RM emulator or device backend. */
#ifndef FAKE_RM_H
#define FAKE_RM_H
#include <stddef.h>
#include <stdint.h>
int fake_rm_payload(uint32_t command, unsigned char *out, size_t capacity);
#endif
