import logging
from conftest import *
from test_utils import find_resource
from click.testing import CliRunner

"""
python diana-cli.py -s "{redis: {ctype: Redis}}" check
"""

app = __import__('diana-cli')

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(app.cli, ["--help"])
    print(result.output)

    assert("Check status of service ENDPOINTS" in result.output)


def test_cli_svc_check(setup_orthanc, setup_redis):
    runner = CliRunner()
    services_file = find_resource("resources/test_services.yml")
    result = runner.invoke(app.cli, [
        "-s", "{redis_bad2: {ctype: Redis, port: 9999}}",
        "-S", services_file, "check"])
    print(result.output)

    assert( "orthanc: Ready" in result.output )
    assert( "orthanc_bad: Not Ready" in result.output )
    assert( "redis: Ready" in result.output )
    assert( "redis_bad: Not Ready" in result.output )
    assert( "redis_bad2: Not Ready" in result.output )


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.debug("Testing")

    test_cli_help()
    for (i, j) in zip( setup_orthanc(), setup_redis() ):
        test_cli_svc_check(None, None)

        # i.stop_service()
        # j.stop_service()
