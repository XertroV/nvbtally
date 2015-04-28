# NVB Tally Module

## Running

### Updater

```
python3 -m nvbtally.updater [--watch]
```

This populates the DB of nulldatas from api.coinsecrets.org.

Planned: watching mode; will wait for new blocks and add them as the come in.

Can be run as cron job (without `--watch`)

### Filter

```
python3 -m nvbtally.filter_votes
```

This will filter collected nulldatas into a list of votes.
Additionally traces transactions back to their origin, finding the metadata.
Caches results.

### Tally

```
python3 -m nvbtally.tally [--hex] NETWORK_NAME RESOLUTION
```

This will iterate through all votes and give a response to the outcome of `RESOLUTION` for `NETWORK_NAME`.

## Install

**WARNING** Setup isn't stable yet, don't do this

```
python3 setup.py install
```