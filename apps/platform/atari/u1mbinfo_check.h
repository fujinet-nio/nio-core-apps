#ifndef U1MBINFO_CHECK_H
#define U1MBINFO_CHECK_H

#include <stdint.h>

/* A probe may allocate a different slot. Require a changed entry, so an
 * already-cached match elsewhere cannot be mistaken for a new discovery. */
static uint8_t u1mb_new_entry(const uint8_t *before, const uint8_t *after, uint8_t speed)
{
  uint8_t i;
  for (i = 0; i < 4; ++i) {
    if (after[16 + i] == 0x7f && after[20 + i] == speed + 1 &&
        (before[16 + i] != after[16 + i] || before[20 + i] != after[20 + i])) return 1;
  }
  return 0;
}
#endif
