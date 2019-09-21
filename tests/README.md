## Prepare environment
```
docker-compose -f .\base.yml -f .\collector.yml up -d rabbitmq
docker-compose -f .\base.yml -f .\collector.yml up -d collector
```

## Run tests
```
docker-compose -f .\base.yml -f .\collector.yml run --rm integration-test
```
