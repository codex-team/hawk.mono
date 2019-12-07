Hawk mono repository for development needs

# Init modules

1. Run `git submodule init && git submodule update`.
2. Create `.env` file in those repositories where there is `.env.sample` file.
3. Run `docker-compose up` to run all hawk services or list only the necessary services in the command above.


# Troubleshooting

If something went wrong, check this items.

## `docker-compose up` failed

Try this commands:

```bash
docker-compose build --no-cache <service>
```

service are  `garage` or `api` etc (see [docker-compose.yml](/docker-compose.yml) -> services)

If it does not help, remove docker image and build again:

1. List all images:

```bash
docker ps | grep hawk
```

2. Copy image name

3. Remove an image

```bash
docker image rm <name>
```

4. Rebuild

```bash
docker-compose up <service>
```
