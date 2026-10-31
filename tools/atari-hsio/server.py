#!/usr/bin/env python3
"""Deterministic, private request/response fixture for the HSIONET Atari test."""
import argparse
import asyncio

LENGTHS = (1, 7, 31, 69, 87, 127, 200, 255)


def response(sequence):
    return bytes((sequence + i) & 255 for i in range(LENGTHS[sequence & 7]))


async def handle(reader, writer):
    peer = writer.get_extra_info('peername')
    print(f'connected {peer}', flush=True)
    try:
        while request := await reader.read(1):
            seq = request[0]
            data = response(seq)
            await asyncio.sleep(0.03 * (seq * 17 % 9))
            # Some responses arrive in two chunks, exercising partial stream reads.
            split = len(data) // 2 if seq & 1 else len(data)
            writer.write(data[:split])
            await writer.drain()
            if split < len(data):
                await asyncio.sleep(0.04)
                writer.write(data[split:])
                await writer.drain()
            print(f'{peer} seq={seq} bytes={len(data)}', flush=True)
    except (ConnectionError, OSError):
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass
        print(f'disconnected {peer}', flush=True)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=6598)
    args = parser.parse_args()
    server = await asyncio.start_server(handle, args.host, args.port)
    print(f'listening on {server.sockets[0].getsockname()}', flush=True)
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
