import logging
import click
from diana.utils.gateways import supress_urllib_debug
from diana_cli import __version__
from diana import __version__ as diana_version

from diana_cli.cli import cmds as cli_cmds

from .ssde import ssde
from .classify import classify
# from diana_cli.check import check
# from diana_cli.collect import collect
# from diana_cli.dcm2im import dcm2im
# from diana_cli.file_index import findex, fiup
# from diana_cli.guid import guid
# from diana_cli.mock import mock
# from diana_cli.ofind import ofind
# from diana_cli.verify import verify
# from diana_cli.watch import watch


@click.group(name="diana-plus")
@click.option('--verbose/--no-verbose', default=False)
@click.version_option(version=(__version__, diana_version),
                      prog_name=("diana-plus", "python-diana"))
def cli(verbose):
    """Run diana and diana-plus packages using a command-line interface."""

    if verbose:
        logging.basicConfig(level=logging.DEBUG)
        supress_urllib_debug()
        click.echo('Verbose mode is %s' % ('on' if verbose else 'off'))
    else:
        logging.basicConfig(level=logging.WARNING)
        supress_urllib_debug()


cmds = [
    ssde,
    classify,
]

# cli_cmds =[
#     check,
#     collect,
#     dcm2im,
#     findex,
#     fiup,
#     guid,
#     mock,
#     ofind,
#     verify,
#     watch,
# ]

for c in cmds + cli_cmds:
    cli.add_command(c)


# Indirection to set envar prefix from setuptools entry pt
def main():
    cli(auto_envvar_prefix='DIANA', obj={})


if __name__ == "__main__":
    main()
