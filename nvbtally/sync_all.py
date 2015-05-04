__author__ = 'XertroV'

from time import sleep

from .updater import Updater
from .filter_votes import Filterer
from .tally import Tallier

to_sleep = 30

if __name__ == "__main__":
    objects = [Updater(), Filterer(), Tallier()]

    while True:
        for o in objects:
            o.run()
        print('Sleeping %d' % to_sleep)
        sleep(to_sleep)
        print('About to do stuff... Do not kill')
        sleep(1)
