import contextlib
import logging
import aiohttp.web
import aiohttp_cors
import ssl
import os
import asyncio


@contextlib.asynccontextmanager
async def with_application_server(app: aiohttp.web.Application, port: int, use_ssl: bool, **kwargs) -> None:
    """Create a scope in which the application is running on the event loop"""
    # get the ssl context
    ssl_ctx = None
    if use_ssl:
        # certificates are created by a trusted entity
        # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/SSL-on-amazon-linux-2.html
        # or https://certbot.eff.org/instructions?ws=other&os=ubuntufocal
        # step 1: create a private key (.key) and a corresponding certificate signing request (CSR)
        # step 2: submit the CSR to an authorizing entity (e.g. godaddy)
        # step 3: download the resulting certificate (.pem) and the intermediate chain (.crt)
        # step 4: invoke here - note the purpose and cafile in create_default_context are required
        # if this all works, verify with 'curl -X GET https://www.{my-url}.com:3000/ping/compute'
        # noinspection PyTypeChecker
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH, cafile=os.environ.get('SSL_CA_PATH'))
        ssl_ctx.load_cert_chain(os.environ['SSL_CERT_PATH'], os.environ['SSL_PRIVATE_KEY_PATH'])

    # add server to event loop
    runner = aiohttp.web.AppRunner(app, **kwargs)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, '0.0.0.0', port, ssl_context=ssl_ctx)
    await site.start()

    # yield control
    try:
        logging.info(f'Starting server in pid {os.getpid()} binding port {port}')
        yield None
    finally:
        # cleanup the runner and server
        logging.info(f'Shutting down server in pid {os.getpid()} binding port {port}')
        await runner.cleanup()
        await asyncio.sleep(.01)  # ensure port is known to be released


class Server:
    def __init__(self):
        self._step = 2
    
    async def handle_ping(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        """Endpoint loading provided model logits"""
        value = request.headers.get('value')
        logging.info(f'Handling ping with value {value}')
        value = int(value)
        return aiohttp.web.json_response(value + self._step)


def _make_app(server: Server,) -> aiohttp.web.Application:
    # declare app and bind routes
    app = aiohttp.web.Application()

    # add static routes
    routes = [aiohttp.web.static('/page', '/home/ubuntu/theClimberDiary')]
    app.add_routes(routes)

    # support cors from anywhere
    cors_defaults = {'*': aiohttp_cors.ResourceOptions(expose_headers="*", allow_headers="*")}
    cors = aiohttp_cors.setup(app, defaults=cors_defaults)

    # admin endpoints
    ping_resource = cors.add(app.router.add_resource(f'/ping'))
    cors.add(ping_resource.add_route('GET', server.handle_ping))

    return app


async def run():
    """Perpetual function to define and run an app serving the refinement server"""
    # make ready app
    server = Server()
    app = _make_app(server)

    # run server
    event = asyncio.Event()
    async with with_application_server(app, port=443, use_ssl=True):
        await event.wait()  # runs forever



if __name__ == '__main__':
    # set up logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler('log.log')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    
    # do it
    asyncio.run(run())


