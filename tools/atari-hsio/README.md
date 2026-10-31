# Atari TCP / SIO stress fixture

HSIONET exercises the same public NIO TCP stream and Atari SIOV path used by the game, without contacting a public service. Each round writes one sequence byte, then verifies every byte of a 1, 7, 31, 69, 87, 127, 200 or 255 byte response. The server varies delays deterministically and splits alternate responses. Sequence numbers wrap after 255. The screen reports the round and expected size before each exchange, so an SIO timeout is visible; press any key between rounds to stop.

Build the separate boot disk from `nio-core-apps` after sourcing the workspace environment:

```sh
make TARGET=atari boot-disk BOOT_DISK_MANIFEST=boot-disk/manifests/atari-hsionet.yaml \
  BOOT_DISK_STAGE_DIR=build/atari/disk/hsionet-stage \
  BOOT_DISK_OUTPUT_DIR=build/atari/disk/hsionet
```

The ATR is `build/atari/disk/hsionet/autorun.atr`. Copy it to the Atari's boot media. Run `python3 -u tools/atari-hsio/server.py --host <LAN-IP> --port 6598` on the server machine, allow TCP 6598 on its firewall if needed, and leave it running. The default bind address is loopback; the LAN address must be requested explicitly. This server never contacts a lobby or external service.

On the Atari select `U`, enter the server address as `host:port` (for example `192.168.1.2:6598`), then `R` to run. The initial URL is loopback for emulator testing; loopback on a real FujiNet is the FujiNet itself. An empty entry retains the current URL. `H` toggles the library's own HSIO driver. Leave it off to use SIOV and the U1MB driver, as the game does. The test installs the PROC interrupt and also polls once per 60 Atari ticks, as the game does; FujiNet PROC notifications may be enabled or disabled from the console.

Run `python3 -m unittest discover -s tools/atari-hsio -p 'test_*.py' -v` to verify the server protocol. A completed round verifies the response's size and every byte. This exercises the real stream transport but does not reproduce the game's UI, sound or exact traffic schedule.
