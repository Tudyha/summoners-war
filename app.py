"""AScript app facade for the Summoners War reroll runner."""

from .runner import Runner


def run():
    Runner().run_forever()
