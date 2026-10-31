/* U1MBINFO: examine and clear U1MB HSIO device cache entries.
 *
 * Sets the FujiNet HSIO index, clears selected U1MB entries, then
 * sends one raw SIO command at a time through the OS (so through the U1MB's handler) and shows the
 * tables again after each, so the command that first creates an entry for a device is visible.
 * Run `sio.status` on the FujiNet afterwards for what reached it.
 *
 * The tables are the U1MB's own (undocumented): the PBI ROM selected by writing its ID bit to $D1FF
 * shows "S3", "IC" or "XU" at $D800 and the standard PBI identification bytes;
 * $D174+n is disk n+1's entry (0 = never polled, else the divisor
 * plus 1) and $D184..$D187 / $D188..$D18B are up to four non-disk device IDs and their entries.
 */

#include <atari.h>
#include <conio.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "fujinet-nio.h"
#include "u1mbinfo_check.h"

#define TABLE_ADDRESS 0xD174u
#define DISKS         15u
#define DEVICES       4u

typedef struct {
  uint8_t device;
  uint8_t command;
  uint8_t stats;      /* DSTATS: $40 reads from the device, $80 writes to it, 0 neither */
  uint8_t bytes;
  const char *what;
} step_t;

/* With a U1MB BIOS that polls every device ($3F first, then the other detection commands), $7F is
 * the one the FujiNet answers: a Q (our query), a status, a repeat of the Q (now at whatever speed was
 * agreed), and $70 for comparison (nothing answers it, so the whole detection sequence times out).
 * sio.status on the FujiNet shows "3F asked: ... 0x7f n" and the first frames for other devices. */
static const step_t steps[] = {
  { 0x7f, 'Q', 0x40, 4, "7F Q query" },
  { 0x7f, 'Q', 0x40, 4, "7F Q again" },
  { 0x7f, 'S', 0x40, 4, "7F S status" },
  { 0x70, 'S', 0x40, 4, "70 S status" }
};

static uint8_t buffer[8];
static uint8_t table[DISKS + 1 + DEVICES * 2];
static uint8_t before_probe[DISKS + 1 + DEVICES * 2];

static void pair(uint8_t a, uint8_t b)
{
  printf(" %02x:%02x", (unsigned) a, (unsigned) b);
}

static uint8_t dump_tables(void)
{
  uint8_t i, sel = fn_atari_u1mb_pbi();
  uint8_t original = *(volatile uint8_t *)0x0248;
  if (!sel) {
    puts("No supported PBI BIOS active.");
    return 0;
  }
  *(volatile uint8_t *)0x0248 = sel;
  *(volatile uint8_t *)0xD1FF = sel;
  for (i = 0; i < sizeof(table); ++i) table[i] = *(volatile uint8_t *)(TABLE_ADDRESS + i);
  *(volatile uint8_t *)0x0248 = original;
  *(volatile uint8_t *)0xD1FF = original;
  printf("PBI $%02x disk:", (unsigned) sel);
  for (i = 0; i < DISKS; ++i)
    if (table[i])
      pair(i + 1, table[i]);
  printf("\n dev:");
  for (i = 0; i < DEVICES; ++i)
    printf(" %u:%02x:%02x", (unsigned)i, (unsigned)table[16 + i], (unsigned)table[20 + i]);
  puts("");
  return 1;
}

static void send(const step_t *s)
{
  buffer[0] = buffer[1] = buffer[2] = buffer[3] = 0;
  OS.dcb.ddevic = s->device;
  OS.dcb.dunit = 1;
  OS.dcb.dcomnd = s->command;
  OS.dcb.dstats = s->stats;
  OS.dcb.dbuf = buffer;
  OS.dcb.dtimlo = 3;
  OS.dcb.dunuse = 0;
  OS.dcb.dbyt = s->bytes;
  OS.dcb.daux = 0;
  __asm__("jsr $E459");
}

int main(void)
{
  uint8_t i, key, selected, speed, status, observed;

  clrscr();
  puts("U1MBINFO");
  puts("start:");
  if (!dump_tables()) { puts("Press a key to exit."); cgetc(); return 1; }
  puts("Clear device slot 0-3, A=all, Q=quit");
  do { key = cgetc(); } while ((key < '0' || key > '3') && key != 'a' && key != 'A' && key != 'q' && key != 'Q');
  if (key == 'q' || key == 'Q') return 0;
  selected = (key == 'a' || key == 'A') ? DEVICES : key - '0';
  puts("Set HSIO index 0-9, O=off:");
  do { key = cgetc(); } while ((key < '0' || key > '9') && key != 'o' && key != 'O');
  speed = (key == 'o' || key == 'O') ? 0xff : key - '0';
  status = fn_init();
  if (status == FN_OK) status = fn_fuji_set_hsio(speed);
  if (status == FN_OK) status = fn_fuji_get_hsio(&observed);
  if (status != FN_OK) { printf("Set HSIO failed: %u\nPress a key.\n", (unsigned)status); cgetc(); return 1; }
  printf("FujiNet index: $%02x\n", (unsigned)observed);
  status = fn_atari_u1mb_clear_devices(selected == DEVICES ? 15 : (1u << selected));
  if (status == FN_OK) status = fn_atari_u1mb_clear_device(0x7f);
  if (status != FN_OK) {
    printf("Clear failed: %u\n", (unsigned)status);
    dump_tables();
    puts("Press a key to exit."); cgetc();
    return 1;
  }
  puts("Clear readback OK");
  dump_tables();
  if (!dump_tables()) { puts("Press a key to exit."); cgetc(); return 1; }
  memcpy(before_probe, table, sizeof(table));
  puts("Send 7F Q; then check device table.");
  send(&steps[0]);
  printf("SIO status $%02x\n", (unsigned)OS.dcb.dstats);
  dump_tables();
  if (speed == 0xff) puts("Off: inspect 7F entry and sio.status.");
  else if (OS.dcb.dstats == 1 && u1mb_new_entry(before_probe, table, speed)) puts("New 7F entry matches speed.");
  else puts("7F entry not verified; see table.");
  puts("Key for original SIO diagnostics.");
  cgetc();
  for (i = 0; i < sizeof(steps) / sizeof(steps[0]); ++i) {
    printf("key: send %s\n", steps[i].what);
    cgetc();
    send(&steps[i]);
    printf("-> $%02x reply", (unsigned) OS.dcb.dstats);
    pair(buffer[0], buffer[1]);
    pair(buffer[2], buffer[3]);
    puts("");
    dump_tables();
  }
  puts("done (key to exit); sio.status on the FujiNet");
  cgetc();
  return 0;
}
