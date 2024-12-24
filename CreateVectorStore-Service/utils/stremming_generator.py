import asyncio


async def generator(chain,args:dict):
    text=''
    try:
        async for chunk in chain.astream(args):
            text+=''+chunk
            yield chunk or ""
            await asyncio.sleep(0.1)
    except Exception as e:
        print (e,"token generation")
