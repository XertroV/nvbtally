# NVB Tally Module

## Running

### Updater

```
python3 -m nvbtally.updater
```

This populates the DB of nulldatas from api.coinsecrets.org.

Planned: continuous (just need to put args in)

Can be run as cron job

### Filter

```
python3 -m nvbtally.filter_votes
```

This will filter collected nulldatas into a list of votes.

### Tally

```
python3 -m nvbtally.tally [resolution]
```

This will iterate through all votes and 

## Install

**WARNING** Setup isn't stable yet, don't do this

```
python3 setup.py install
```