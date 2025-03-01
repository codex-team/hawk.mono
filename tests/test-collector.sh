docker-compose -f base.yml up -d
sleep 10
docker-compose -f base.yml -f collector.yml build
docker-compose -f base.yml -f collector.yml run --rm integration-test
docker-compose -f base.yml -f collector.yml down