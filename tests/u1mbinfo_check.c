#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "../apps/platform/atari/u1mbinfo_check.h"

int main(void)
{
    uint8_t before[24] = {0}, after[24] = {0};
    /* Hardware example: cleared slot 0; 7f allocated in slot 1. */
    after[17] = 0x7f; after[21] = 5;
    assert(u1mb_new_entry(before, after, 4));
    assert(!u1mb_new_entry(before, after, 3));
    memcpy(before, after, sizeof(before));
    assert(!u1mb_new_entry(before, after, 4));
    /* A cleared existing entry is populated again. */
    before[21] = 0;
    assert(u1mb_new_entry(before, after, 4));
    after[17] = 0x70;
    assert(!u1mb_new_entry(before, after, 4));
    return 0;
}
