#include "wb13_node.h"

#include <stdio.h>
#include <string.h>

static int failures;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); failures++; } } while (0)

int main(void)
{
    uint32_t env[WB13_ENVEC_LONGS];
    /* DD OFS as dumped from a real Mount of DO0: (hex, TableSize..DosType). */
    static const uint32_t real_dd[17] = {
        0x12, 0x80, 0, 2, 1, 0xb, 2, 0, 0, 0, 0x4f, 5, 1, 0x7fffffff, 0xfffffffe, 0, 0x444f5300
    };
    uint8_t b[WB13_NAME_MAX + 1];
    unsigned i;

    wb13_fill_envec(env, 0, 0x444f5300u);
    for (i = 0; i < 17; ++i) CHECK(env[i] == real_dd[i]);
    CHECK(env[17] == 0 && env[18] == 0);
    wb13_fill_envec(env, 1, 0x444f5300u);
    CHECK(env[5] == 22);

    CHECK(wb13_make_bstr(b, "DO0:") == 3 && b[0] == 3 && !memcmp(b + 1, "DO0", 3));
    CHECK(wb13_make_bstr(b, "HO1") == 3);
    CHECK(wb13_make_bstr(b, "TOOLONG:") == 0);
    CHECK(wb13_make_bstr(b, ":") == 0);
    CHECK(wb13_make_bstr(b, "DO0:x") == 0);

    wb13_make_bstr(b, "DO0:");
    CHECK(wb13_bstr_matches(b, "DO0:"));
    CHECK(wb13_bstr_matches(b, "do0:"));
    CHECK(wb13_bstr_matches(b, "DO0"));
    CHECK(!wb13_bstr_matches(b, "DO1:"));
    CHECK(!wb13_bstr_matches(b, "DO:"));
    CHECK(!wb13_bstr_matches(b, "DO01:"));

    printf(failures ? "wb13_node_test: %d FAILED\n" : "wb13_node_test: ok\n", failures);
    return failures != 0;
}
