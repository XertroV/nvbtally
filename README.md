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
python3 -m nvbtally.filter_votes [--watch]
```

This will filter collected nulldatas into a list of votes.
Additionally traces transactions back to their origin, finding the metadata.
Caches results.

### Tally

```
python3 -m nvbtally.tally [--watch] [--hex] [--res RES_ID] NETWORK_NAME
```

This will iterate through all votes and give a response to the outcome of `RES_ID` for `NETWORK_NAME`. 
If `--hex` is specified all strings are presumed to be hex encoded.

## Install

**WARNING** Incomplete

```
python3 setup.py install
```