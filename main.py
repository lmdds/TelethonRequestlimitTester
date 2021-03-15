import asyncio
from asyncio import sleep

from configobj import ConfigObj
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
    count = 0
    try:
        await client(request)
    except FloodWaitError as e:
        print("Initial wait time of "+request.__class__.__name__+":", e.seconds)
        await sleep(e.seconds + 1)
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
    print("Test of", request.__class__.__name__, "with wait time", wait_time, "finished. Result:", result)
    return result


async def ascertain_wait_time(client, request, wait_time, repetitions, lowering_rate):
    name = request.__class__.__name__
    print("Starting test of", name, "with a wait time of", wait_time,
          "seconds. A successful run would take about", wait_time*repetitions, "seconds.")
    try:
        result = await test_wait_time(client, request, wait_time, repetitions)
    except Exception as e:
        print("Exception occurred at test of "+name+":"+e)
    else:
        if result[0]:
            new_wait_time = int(wait_time * (1 - lowering_rate))
            if new_wait_time == wait_time:
                print(name + ": former wait time = new wait time. Returning.")
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


async def main():
    # Reading configs
    config = ConfigObj("config.ini")
    # Creating client
    client = await TelegramClient(config['Telegram']['username'], int(config['Telegram']['api_id']),
                                  config['Telegram']['api_hash']).start()

    # Execute the testing of all requests asynchronously
    results = await asyncio.gather(*(
        ascertain_wait_time(
            client,
            RequestDict[request](str(config['Requests'][request]['param'])),
            int(config['Requests'][request]['wait_time']),
            int(config['Requests'][request]['repetitions']),
            float(config['Requests'][request]['lowering_rate'])
        )
        for request in config['Requests']
    ))

    # Print the results
    print("\nResults:")
    for r in results:
        print("Request:", r[0], ", Best wait time:", r[1])


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Keyboard interrupted.")
