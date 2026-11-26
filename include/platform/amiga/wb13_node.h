#ifndef FUJINET_WB13_NODE_H
#define FUJINET_WB13_NODE_H

/*
 * Pure (no Amiga headers) helpers for building the DOS device node that
 * FMOUNT creates on Kickstart 1.3 without C:Mount.  The field values were
 * observed from the node a real Mount builds for DO0: (see
 * backlog/amiga-ks13-free-mount.md, Findings); they are not copied code.
 * Kept header-only so the host test can include it.
 */

#include <stdint.h>

#define WB13_ENVEC_LONGS 19u      /* TableSize word + fields through de_Control */
#define WB13_NODE_STACK 4000u
#define WB13_NODE_PRIORITY 5
#define WB13_NAME_MAX 4u          /* "DO0" etc: letters+digit, no colon */

/* Geometry matches the static MountList entries (2 surfaces, 80 cylinders). */
static void wb13_fill_envec(uint32_t env[WB13_ENVEC_LONGS], int high_density,
                            uint32_t dostype)
{
    unsigned i;
    for (i = 0; i < WB13_ENVEC_LONGS; ++i)
        env[i] = 0;
    env[0] = 0x12u;                  /* de_TableSize: through de_DosType */
    env[1] = 128u;                   /* de_SizeBlock (longwords) */
    env[3] = 2u;                     /* de_Surfaces */
    env[4] = 1u;                     /* de_SectorPerBlock */
    env[5] = high_density ? 22u : 11u; /* de_BlocksPerTrack */
    env[6] = 2u;                     /* de_Reserved */
    env[10] = 79u;                   /* de_HighCyl */
    env[11] = 5u;                    /* de_NumBuffers */
    env[12] = 1u;                    /* de_BufMemType: MEMF_PUBLIC */
    env[13] = 0x7fffffffu;           /* de_MaxTransfer */
    env[14] = 0xfffffffeu;           /* de_Mask */
    env[16] = dostype;               /* de_DosType */
}

/* Write a BSTR for label ("DO0:" or "DO0"); returns length or 0 if invalid.
 * dst needs WB13_NAME_MAX + 1 bytes. */
static unsigned wb13_make_bstr(uint8_t *dst, const char *label)
{
    unsigned n = 0;
    while (label[n] && label[n] != ':') {
        if (n >= WB13_NAME_MAX)
            return 0;
        dst[1 + n] = (uint8_t)label[n];
        ++n;
    }
    if (n == 0 || (label[n] == ':' && label[n + 1] != '\0'))
        return 0;
    dst[0] = (uint8_t)n;
    return n;
}

/* Case-insensitive compare of a BSTR against label (colon optional). */
static int wb13_bstr_matches(const uint8_t *bstr, const char *label)
{
    unsigned i, n = bstr[0];
    for (i = 0; i < n; ++i) {
        char a = (char)bstr[1 + i], b = label[i];
        if (a >= 'a' && a <= 'z') a = (char)(a - 32);
        if (b >= 'a' && b <= 'z') b = (char)(b - 32);
        if (b == '\0' || a != b)
            return 0;
    }
    return label[n] == '\0' || (label[n] == ':' && label[n + 1] == '\0');
}

#endif
