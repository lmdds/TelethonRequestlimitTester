import asyncio
from asyncio import sleep
from configparser import ConfigParser
from time import time

from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions import account
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest


async def test_wait_time(client, request, wait_time, repetitions):
    request_name = request.__class__.__name__
    print("Starting test of", request_name)
    count = 0
    execution_time = 0
    try:
        for i in range(repetitions):
            start_time = time()
            try:
                await client(request)
                raise RPCError(request, "Success.")
            except FloodWaitError:
                raise
            except RPCError:
                count += 1
                await sleep(wait_time)

    except FloodWaitError as e:
        result = False, count, e.seconds + (time() - start_time)
    else:
        result = True,
    print("Test of", request_name, "finished. Result:", result)
    return result


async def main():
    # Reading configs
    config = ConfigParser()
    config.read("config.ini")

    # Creating client
    client = await TelegramClient(config['Telegram']['username'], int(config['Telegram']['api_id']),
                                  config['Telegram']['api_hash']).start()

    requests = (
        (CheckChatInviteRequest(config['Requests']['invite_hash']), 80, 20),
        (ResolveUsernameRequest(config['Requests']['username']), 1, 5000),  # 5000: real value unknown
        (ImportChatInviteRequest(config['Requests']['invite_hash']), 100, 5),
    )

    counts = await asyncio.gather(*(
        test_wait_time(client, request[0], request[1], request[2])
        for request in requests
    ))

    print("\nResults:")
    for i in range(len(requests)):
        if counts[i][0]:
            print("SUCCESS: Request:", requests[i][0].__class__.__name__, ", Wait Time:", requests[i][1])
        else:
            print("FAILED: Request:", requests[i][0].__class__.__name__, ", Wait Time:", requests[i][1],
                  ", Count:", counts[i][1], ", Flood Wait Time:", counts[i][2])


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Keyboard interrupted.")
