import asyncio
import logging.config
from asyncio import sleep

import yaml

from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.contacts import ResolveUsernameRequest
from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest

RequestDict = {
    'ResolveUsernameRequest': ResolveUsernameRequest,
    'ImportChatInviteRequest': ImportChatInviteRequest,
    'CheckChatInviteRequest': CheckChatInviteRequest
}


async def test_wait_time(client, request, wait_time, repetitions):
    name = request.__class__.__name__
    count = 0
    try:
        await client(request)
    except FloodWaitError as e:
        logging.getLogger(name).info(f"Initial wait time: {e.seconds} ({round(e.seconds / 3600, 1)} hours ).")
        await sleep(e.seconds + 1)
        logging.getLogger(name).info(f"Starting now.")
        count = -1
    except RPCError:
        pass

    try:
        for i in range(repetitions):
            try:
                count += 1
                await sleep(wait_time)
                await client(request)
            except FloodWaitError:
                raise
            except RPCError:
                pass
    except FloodWaitError as e:
        result = False, count, e.seconds
    else:
        result = True,
    logging.getLogger(name).info(f"Test with wait time {wait_time} finished. Result: {result}")
    return result


async def ascertain_wait_time(client, request, wait_time, repetitions, lowering_rate):
    name = request.__class__.__name__
    logging.getLogger(name).info(f"Starting test with a wait time of {wait_time} seconds. "
                                 f"A successful run would take about {round(wait_time * repetitions / 3600, 1)} hours.")

    result = await test_wait_time(client, request, wait_time, repetitions)

    if result[0]:
        new_wait_time = int(wait_time * (1 - lowering_rate))
        if new_wait_time == wait_time:
            logging.getLogger(name).info(f"Former wait time = new wait time. Returning.")
            return name, wait_time
        else:
            result_rec = await ascertain_wait_time(client, request, new_wait_time,
                                                   repetitions, lowering_rate)
        if result_rec[1]:
            return result_rec
        else:
            return name, wait_time
    else:
        return name, False


async def start_ascertain_wait_time(client, request, wait_time, repetitions, lowering_rate):
    name = request.__class__.__name__
    try:
        result = await ascertain_wait_time(client, request, wait_time, repetitions, lowering_rate)
    except Exception as e:
        logging.getLogger(name).info(f"Exception occurred: {e.__str__()}")
        return name, False

    else:
        if result[1]:
            return result
        else:
            logging.getLogger(name).info(f"Restarting with twice the wait time.")
            return await start_ascertain_wait_time(client, request, wait_time * 2, repetitions, lowering_rate)


async def main():
    # Reading configs
    config = yaml.load(open("config.yml", "r"), Loader=yaml.SafeLoader)

    logging.config.dictConfig(config['logging'])
    # Creating client
    client = await TelegramClient("Telegram", int(config['client']['api_id']),
                                  config['client']['api_hash']).start()

    # Execute the testing of all requests asynchronously
    results = await asyncio.gather(
        *(
            start_ascertain_wait_time(
                client,
                RequestDict[request](str(config['requests'][request]['param'])),
                int(config['requests'][request]['wait_time']),
                int(config['requests'][request]['repetitions']),
                float(config['requests'][request]['lowering_rate'])
            )
            for request in config['requests']
        )
    )

    # Print the results
    logging.info("\nResults:")
    for r in results:
        logging.info(f"Request: {r[0]}, Best wait time: {r[1]}")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Keyboard interrupted.")
