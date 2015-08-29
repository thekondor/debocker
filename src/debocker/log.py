# logging (using click)

import click

NONE, LOW = 0, 1
VERBOSITY = NONE

def fail(msg, *params):
    raise click.ClickException(msg.format(*params))

def set_verbosity(value):
    global VERBOSITY
    VERBOSITY = value

def is_verbose():
    # return True is there is positive verbosity set
    return (VERBOSITY > NONE)

def log(msg, v = 0):
    if VERBOSITY == NONE:
        if v == 0:
            click.secho('LOG {}'.format(msg), fg = 'green')
    else:
        if v <= VERBOSITY:
            click.secho('LOG[{}] {}'.format(v, msg), fg = 'green')
