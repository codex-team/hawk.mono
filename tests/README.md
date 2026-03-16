## Prepare environment
```
docker-compose -f base.yml up -d 
```

## Run integration tests
```
docker-compose -f base.yml -f collector.yml run --rm integration-test
```

## Clear after run
```
docker-compose -f collector.yml down
```