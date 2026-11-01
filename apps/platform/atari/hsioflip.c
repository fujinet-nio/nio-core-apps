/* Observe U1MB speed-cache behaviour when FujiNet HSIO changes from 0 to off.
 * The experiment reads the undocumented PBI tables, but never writes them. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "fujinet-nio.h"

#define TABLE_SIZE 24u
#define BATCH 4u

#ifdef HSIOFLIP_TEST
extern void clrscr(void);
extern char cgetc(void);
extern uint8_t experiment_pbi(void);
extern void experiment_tables(uint8_t pbi, uint8_t *table);
extern uint8_t experiment_query(uint8_t *reply, uint16_t *ticks);
#else
#include <atari.h>
#include <conio.h>

#define TABLE_ADDRESS 0xD174u
static uint8_t experiment_pbi(void) { return fn_atari_u1mb_pbi(); }

/* PBI selection is restored immediately. The table itself is only read. */
static void experiment_tables(uint8_t pbi, uint8_t *table)
{
  uint8_t i, saved = *(volatile uint8_t *)0x0248;
  *(volatile uint8_t *)0x0248 = pbi;
  *(volatile uint8_t *)0xD1FF = pbi;
  for (i = 0; i < TABLE_SIZE; ++i) table[i] = *(volatile uint8_t *)(TABLE_ADDRESS + i);
  *(volatile uint8_t *)0x0248 = saved;
  *(volatile uint8_t *)0xD1FF = saved;
}

/* RTCLOK is incremented by the OS; these coarse ticks can undercount while
 * interrupts are masked, so they are not a wire-level timing measurement. */
static uint16_t clock_ticks(void)
{
  uint8_t high, low;
  do {
    high = *(volatile uint8_t *)0x13;
    low = *(volatile uint8_t *)0x14;
  } while (high != *(volatile uint8_t *)0x13);
  return ((uint16_t)high << 8) | low;
}

static uint8_t experiment_query(uint8_t *reply, uint16_t *ticks)
{
  uint16_t start;
  memset(reply, 0, 4);
  OS.dcb.ddevic = 0x7f;
  OS.dcb.dunit = 1;
  OS.dcb.dcomnd = 'Q';
  OS.dcb.dstats = 0x40;
  OS.dcb.dbuf = reply;
  OS.dcb.dtimlo = 3;
  OS.dcb.dunuse = 0;
  OS.dcb.dbyt = 4;
  OS.dcb.daux = 0;
  start = clock_ticks();
  __asm__("jsr $E459");
  *ticks = clock_ticks() - start;
  return OS.dcb.dstats;
}
#endif

static uint8_t table[TABLE_SIZE];
static uint8_t reply[4];

static void show_slots(uint8_t pbi)
{
  uint8_t i;
  experiment_tables(pbi, table);
  printf("  slots:");
  for (i = 0; i < 4; ++i)
    printf(" %02x:%02x", (unsigned)table[16+i], (unsigned)table[20+i]);
  puts("");
}

static void show_disks(void)
{
  uint8_t i;
  printf("disk:");
  for (i = 0; i < 15; ++i)
    if (table[i]) printf(" %u:%02x", (unsigned)(i+1), (unsigned)table[i]);
  puts("");
}

/* SIO status $01 is success. The slot bytes are diagnostic observations of
 * undocumented firmware, not a claim that an entry proves actual wire baud. */
static void batch(uint8_t pbi, uint8_t first, const char *title)
{
  uint8_t i, status;
  uint16_t ticks;
  clrscr();
  puts(title);
  show_slots(pbi);
  show_disks();
  for (i = 0; i < BATCH; ++i) {
    status = experiment_query(reply, &ticks);
    printf("Q%u S:%02x T:%u", (unsigned)(first+i), (unsigned)status, (unsigned)ticks);
    if (status == 1)
      printf(" %02x %02x %02x %02x", (unsigned)reply[0], (unsigned)reply[1],
             (unsigned)reply[2], (unsigned)reply[3]);
    puts("");
    show_slots(pbi);
  }
}

static uint8_t proceed(void)
{
  char key = cgetc();
  return key != 'q' && key != 'Q';
}

int hsioflip_run(void)
{
  uint8_t pbi, status, index;
  clrscr();
  puts("HSIO 0 -> OFF EXPERIMENT");
  puts("U1MB HSIO ON; FujiNet index 0.");
  puts("Reads tables; never clears them.");
  pbi = experiment_pbi();
  if (!pbi) { puts("No compatible PBI. Key to exit."); cgetc(); return 1; }
  printf("PBI $%02x\n", (unsigned)pbi);
  show_slots(pbi);
  show_disks();
  status = fn_init();
  if (status == FN_OK) status = fn_fuji_get_hsio(&index);
  if (status != FN_OK) {
    printf("INIT/GET failed: $%02x\n", (unsigned)status);
    puts("Key to exit."); cgetc(); return 1;
  }
  printf("FujiNet index: $%02x\n", (unsigned)index);
  if (index != 0) { puts("Need index 0. Key to exit."); cgetc(); return 1; }
  puts("Console: sio.reset; then key.");
  puts("Q quits at any pause.");
  if (!proceed()) return 0;

  batch(pbi, 1, "BEFORE: 4 Q, index 0");
  puts("Capture screen and sio.status.");
  puts("Key sets FujiNet OFF; Q quits.");
  if (!proceed()) return 0;

  status = fn_fuji_set_hsio(FN_FUJI_HSIO_OFF);
  clrscr();
  printf("SET OFF result: $%02x\n", (unsigned)status);
  if (status != FN_OK) puts("OFF uncertain: see sio.status.");
  show_slots(pbi);
  show_disks();
  puts("Capture sio.status; sio.reset.");
  puts("Key for 4 Q; Q quits.");
  if (!proceed()) return 0;

  batch(pbi, 1, "AFTER SET: Q1-Q4");
  puts("Capture screen and sio.status.");
  puts("Key for 4 more Q; Q quits.");
  if (!proceed()) return 0;
  batch(pbi, 5, "AFTER SET: Q5-Q8");
  puts("Capture screen and sio.status.");
  puts("FujiNet may be OFF: restore on");
  puts("console with sio.hsio 0. Key exits.");
  cgetc();
  return 0;
}
#ifndef HSIOFLIP_TEST
int main(void) { return hsioflip_run(); }
#endif
