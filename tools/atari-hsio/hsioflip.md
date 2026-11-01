# U1MB HSIO transition experiment

`hsioflip` observes what a U1MB does when FujiNet changes its advertised HSIO
index from 0 to off. It sends native device `$7F` SIO `Q` queries through the
OS SIO vector, so an active U1MB PBI speed driver sees them. It does not call
`fn_atari_hsio_enable` or write either U1MB speed table. To inspect the
undocumented tables it temporarily selects the detected PBI and restores the
previous selection; the table values are read only. These memory locations are
observations for this experiment, not an interface applications should assume.

Build a separate boot disk without replacing the normal config disk:

```sh
source ../../scripts/env.sh
make TARGET=atari boot-disk \
  BOOT_DISK_MANIFEST=boot-disk/manifests/atari-hsioflip.yaml \
  BOOT_DISK_STAGE_DIR=build/atari/disk/hsioflip-stage \
  BOOT_DISK_OUTPUT_DIR=build/atari/disk/hsioflip
```

Boot `build/atari/disk/hsioflip/autorun.atr` on the test Atari. Before booting,
enable the U1MB PBI and its HSIO driver, set `sio.hsio 0` on the FujiNet
console, and record `sio.status` including any tuning or fallback settings.
A U1MB PBI must be detected; the test stops if the library cannot read the
FujiNet index as 0. Initialization and the index read themselves send SIO
requests and may establish a cached `$7F` entry.

1. At the first pause, issue `sio.reset` on the console and press a key. The
   program sends four Q queries. Photograph the Atari screen and capture
   `sio.status`. The slots are shown in order 0–3 as `device:value`; a `$7F:01`
   entry is the observed U1MB encoding for divisor 0. If no such entry is
   present, the intended stale-cache condition has not been demonstrated.
2. Press a key to call `fn_fuji_set_hsio(FN_FUJI_HSIO_OFF)`. The program shows
   the returned library status and the table snapshot. Capture `sio.status`
   before resetting counters: it shows whether the FujiNet actually switched.
   A failed return does not prove that it did not switch, so the experiment
   still allows the Q queries to proceed. Issue `sio.reset` after capture.
3. Press a key for Q1–Q4 after the set. Capture the screen and `sio.status`;
   press a key for Q5–Q8 and capture both again. The counters are cumulative
   over the two batches unless you reset them between captures. `Q` at any
   pause exits early. The program does not restore the index; when finished,
   use `sio.hsio 0` on the console if you want to turn it back on.

`S:01` is the OS DCB's success status; other hex values are SIO errors. Four
reply bytes are printed only for success. `T` is elapsed OS clock ticks, not a
wire measurement: PAL is nominally 50 ticks/sec and NTSC 60, and ticks can be
missed while interrupts are masked. The table is sampled immediately after
each query. Neither the cached byte nor a successful Q alone proves the baud
on the wire; compare the Atari results and times with `sio.status`, `sio.trace`
if useful, and UART-break logs. Do not infer a fallback from a single counter.

The host sequencing test can be run with `make test-hsioflip`; it simulates
preconditions and query outcomes. Only a real U1MB can establish what the BIOS
actually does when its cached speed and the FujiNet setting diverge.
