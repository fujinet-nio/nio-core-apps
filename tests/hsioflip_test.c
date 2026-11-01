#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "fujinet-nio.h"

int hsioflip_run(void);
static uint8_t pbi, initial_index, init_result, get_result, set_result;
static unsigned queries_before, queries_after, sets, get_calls, tables, pauses;
static unsigned fail_after;
static int quit_at;

void clrscr(void) {}
char cgetc(void) { return ++pauses == (unsigned)quit_at ? 'q' : ' '; }
uint8_t experiment_pbi(void) { return pbi; }
void experiment_tables(uint8_t selected, uint8_t *table)
{
  assert(selected == 1);
  ++tables;
  memset(table, 0, 24);
  table[16] = 0x7f;
  table[20] = 1;
}
uint8_t experiment_query(uint8_t *reply, uint16_t *ticks)
{
  assert(get_calls == 1);
  if (sets) ++queries_after;
  else ++queries_before;
  memset(reply, 0, 4);
  reply[0] = 1;
  *ticks = 2;
  if (sets && queries_after <= fail_after) return 0x8a;
  return 1;
}
uint8_t fn_init(void) { return init_result; }
uint8_t fn_fuji_get_hsio(uint8_t *index) { ++get_calls; *index = initial_index; return get_result; }
uint8_t fn_fuji_set_hsio(uint8_t index)
{
  assert(index == FN_FUJI_HSIO_OFF);
  assert(queries_before == 4 && queries_after == 0 && sets == 0);
  ++sets;
  return set_result;
}
static void reset(void)
{
  pbi = 1; initial_index = 0; init_result = get_result = set_result = 0;
  queries_before = queries_after = sets = get_calls = tables = pauses = fail_after = 0;
  quit_at = -1;
}
int main(void)
{
  reset();
  assert(hsioflip_run() == 0);
  assert(queries_before == 4 && sets == 1 && queries_after == 8 && get_calls == 1);
  assert(tables == 17 && pauses == 5);

  reset(); fail_after = 2;
  assert(hsioflip_run() == 0);
  assert(queries_before == 4 && sets == 1 && queries_after == 8 && get_calls == 1);

  /* A failed set may still have taken effect; the follow-up is still useful. */
  reset(); set_result = FN_ERR_IO;
  assert(hsioflip_run() == 0);
  assert(queries_before == 4 && sets == 1 && queries_after == 8 && get_calls == 1);

  reset(); pbi = 0;
  assert(hsioflip_run() == 1);
  assert(queries_before == 0 && sets == 0 && get_calls == 0);
  reset(); initial_index = 9;
  assert(hsioflip_run() == 1);
  assert(queries_before == 0 && sets == 0 && get_calls == 1);
  reset(); init_result = FN_ERR_IO;
  assert(hsioflip_run() == 1);
  assert(queries_before == 0 && sets == 0 && get_calls == 0);
  reset(); get_result = FN_ERR_IO;
  assert(hsioflip_run() == 1);
  assert(queries_before == 0 && sets == 0 && get_calls == 1);
  reset(); quit_at = 2; /* quit after the baseline, before setting OFF */
  assert(hsioflip_run() == 0);
  assert(queries_before == 4 && sets == 0 && queries_after == 0);
  puts("hsioflip sequencing passed");
  return 0;
}
