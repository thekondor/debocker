# logging (using click)

import click

NONE, LOW = 0, 1
VERBOSITY = NONE

def fail(msg, *params):
    raise click.ClickException(msg.format(*params))

def log(msg, v = 0):
    if VERBOSITY == NONE:
        if v == 0:
            click.secho('LOG {}'.format(msg), fg = 'green')
    else:
        if v <= VERBOSITY:
            click.secho('LOG[{}] {}'.format(v, msg), fg = 'green')
