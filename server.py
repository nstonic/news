import anyio
from aiohttp import web

from jaundice_rater import JaundiceRater


async def handle(request):
    params = request.rel_url.query
    urls = params.get('urls')
    if urls:
        url_list = urls.split(',')
        if len(url_list) > 10:
            return web.json_response({
                'error': 'Too many urls in request, should be 10 or less'
            },
                status=400
            )
        rater = JaundiceRater('charged_dict')
        async with anyio.create_task_group() as tg:
            tg.start_soon(rater.rate, url_list)
        return web.json_response(rater.results)
    else:
        return web.json_response({
            'error': 'URL list is empty'
        })


app = web.Application()
app.add_routes([web.get('/', handle)])


if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1')
