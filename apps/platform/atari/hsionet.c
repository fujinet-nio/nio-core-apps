/* Interactive, deterministic TCP stress test for native Atari SIO. */
#include <atari.h>
#include <conio.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "fujinet-nio.h"

static uint8_t buf[256];
static char url[100] = "tcp://127.0.0.1:6598";
static char entry[100];
static const uint8_t lengths[] = {1, 7, 31, 69, 87, 127, 200, 255};

static void run_test(void)
{
    fn_handle_t handle;
    uint32_t roff = 0, woff = 0;
    uint16_t n, written, received, total, i;
    uint8_t flags, status, seq, last, pending;
    unsigned rounds = 0;
    clrscr();
    cprintf("HSIONET connecting...\r\n");
    status = fn_open(&handle, 0, url, FN_OPEN_KEEP);
    if (status) { cprintf("open error $%02x\r\n", status); return; }
    fn_atari_proc_enable();
    for (;;) {
        seq = (uint8_t)rounds;
        n = lengths[seq & 7];
        cprintf("\r%5u size %3u ", rounds, n);
        do {
            status = fn_write(handle, woff, &seq, 1, &written);
        } while (status == FN_ERR_NOT_READY || status == FN_ERR_BUSY);
        if (status || written != 1) {
            cprintf("write $%02x n%u sio $%02x\r\n", status, written, fn_atari_last_sio_status());
            break;
        }
        ++woff;
        total = 0; pending = 1; last = OS.rtclok[2];
        while (total < n) {
            if (fn_atari_proc_pending()) pending = 1;
            if (!pending && (uint8_t)(OS.rtclok[2] - last) < 60) continue;
            pending = 0; last = OS.rtclok[2];
            status = fn_read(handle, roff, buf, n - total, &received, &flags);
            if (status == FN_ERR_NOT_READY || status == FN_ERR_BUSY) continue;
            if (status || (!received && (flags & FN_READ_EOF))) {
                cprintf("read $%02x flags $%02x sio $%02x\r\n", status, flags,
                        fn_atari_last_sio_status());
                goto done;
            }
            for (i = 0; i < received; ++i) {
                if (buf[i] != (uint8_t)(seq + total + i)) {
                    cprintf("bad data at %u\r\n", total + i); goto done;
                }
            }
            total += received; roff += received;
            if ((flags & FN_READ_AVAILABLE) && fn_read_available()) pending = 1;
            if (received && total < n) pending = 1;
        }
        ++rounds;
        if (kbhit()) { (void)cgetc(); break; }
    }
done:
    fn_atari_proc_disable();
    status = fn_close(handle);
    cprintf("\r\n%u rounds; close $%02x\r\n", rounds, status);
}

int main(void)
{
    uint8_t status;
    char key;
    status = fn_init();
    if (status) { cprintf("init error $%02x\r\n", status); return 1; }
    clrscr();
    cprintf("HSIONET TCP stress\r\n%s\r\n", url);
    cprintf("U URL  R run  H HSIO  Q quit\r\n");
    for (;;) {
        key = cgetc();
        if (key == 'q' || key == 'Q') return 0;
        if (key == 'u' || key == 'U') {
            cprintf("\r\nhost:port (empty keeps current):\r\n");
            cgets(entry, sizeof(entry));
            if (entry[0] && strlen(entry) <= sizeof(url) - 7) {
                strcpy(url, "tcp://");
                strcat(url, entry);
            }
            cprintf("%s\r\n", url);
        }
        if (key == 'h' || key == 'H') {
            if (fn_atari_hsio_index() != 0xff) { fn_atari_hsio_disable(); cprintf("library HSIO off\r\n"); }
            else { status = fn_atari_hsio_enable(); cprintf("library HSIO $%02x index %u\r\n", status, fn_atari_hsio_index()); }
        }
        if (key == 'r' || key == 'R') {
            run_test();
            cprintf("U URL  R run  H HSIO  Q quit\r\n");
        }
    }
}
