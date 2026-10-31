import asyncio
import unittest

import server


class FixtureTest(unittest.IsolatedAsyncioTestCase):
    async def test_variable_responses_and_sequence_wrap(self):
        listener = await asyncio.start_server(server.handle, '127.0.0.1', 0)
        port = listener.sockets[0].getsockname()[1]
        reader, writer = await asyncio.open_connection('127.0.0.1', port)
        try:
            for seq, length in ((0, 1), (1, 7), (2, 31), (3, 69), (4, 87),
                                (5, 127), (6, 200), (7, 255), (255, 255)):
                writer.write(bytes([seq])); await writer.drain()
                data = await asyncio.wait_for(reader.readexactly(length), 2)
                self.assertEqual(data, bytes((seq + i) & 255 for i in range(length)))
        finally:
            writer.close()
            await writer.wait_closed()
            listener.close()
            await listener.wait_closed()
            await asyncio.sleep(0)
