import asyncio
from asyncio import sleep
from configparser import ConfigParser
from time import time

from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest


async def test_wait_time(client, request, wait_time, repetitions):
    request_name = request.__class__.__name__
    print("Starting test of", request_name)
    count = 0
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
        result = False, count, e.seconds
    else:
        result = True,
    print("Test of", request_name, "finished. Result:", result)
    return result


async def ascertain_wait_time(client, request, wait_time, repetitions, lowering_rate):
    result = test_wait_time(client, request, wait_time, repetitions)
    if result[0]:
        return ascertain_wait_time(client, request, repetitions, wait_time * (1 - lowering_rate), lowering_rate)
    else:
        return wait_time


async def main():
    # Reading configs
    config = ConfigParser()
    config.read("config.ini")

    # Creating client
    client = await TelegramClient(config['Telegram']['username'], int(config['Telegram']['api_id']),
                                  config['Telegram']['api_hash']).start()

    # Initialize the request settings (partially hardcoded)

    requests = (
        (CheckChatInviteRequest(config['Requests']['invite_hash']), 100, 20, .1),
        (ResolveUsernameRequest(config['Requests']['username']), 1, 5000, .1),  # 5000: real value unknown
        (ImportChatInviteRequest(config['Requests']['invite_hash']), 90, 5), .1,
    )

    # Execute the testing of all requests asynchronously
    await sleep(800)
    counts = await asyncio.gather(*(
        ascertain_wait_time(client, request[0], request[1], request[2], requests[3])
        for request in requests
    ))

    # Print the results
    print("\nResults:")
    for i in range(len(requests)):
        if counts[i][0]:
            print("SUCCESS: Request:", requests[i][0].__class__.__name__, ", Wait Time:", requests[i][1])
        else:
            print("FAILED: Request:", requests[i][0].__class__.__name__, ", Wait Time:", requests[i][1],
                  ", Count:", counts[i][1], ", Flood Wait Time left:", counts[i][2])


if __name__ == '__main__':
    asyncio.run(main())
