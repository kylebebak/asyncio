from typing import cast, List
import httpx
import asyncio


client = httpx.AsyncClient()


async def get(url: str) -> str:
    r = await client.get(url)
    return r.text


async def main() -> None:
    with open("./urls.txt", "r") as file:
        lines = file.readlines()
    results = cast(
        List[str], await asyncio.gather(*(get(line.strip()) for line in lines))
    )
    print(results)


async def main_get() -> None:
    with open("./urls.txt", "r") as file:
        lines = file.readlines()
    results = cast(
        List[httpx.models.AsyncResponse],
        await asyncio.gather(*(client.get(line.strip()) for line in lines)),
    )
    print([r.text for r in results])


async def main_as_completed() -> None:
    with open("./urls.txt", "r") as file:
        lines = file.readlines()
    for future in asyncio.as_completed([get(line.strip()) for line in lines]):
        res = await future
        print(res)


if __name__ == "__main__":
    # asyncio.run(main())
    # asyncio.run(main_get())
    asyncio.run(main_as_completed())
