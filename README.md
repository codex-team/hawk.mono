
Hawk mono repository for development needs

## How to run

1. Run `git submodule init && git submodule update`.
2. Create `.env` file in those repositories where there is `.env.sample` file.
3. Run `docker-compose up` to run all hawk services or list only the necessary services in the command above.

## Documentation

- [How to send testing events to the local hawk](docs/how-to-get-events.md)
- [How to view Registry queues](docs/how-to-view-registry-queues.md)

## Troubleshooting

If something went wrong, check this items.

### `docker-compose up` failed

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

## Executing Powershell scripts on Windows
To use Powershell scripts, you need to change the script execution policy in the system. Execute next command in Powershell terminal as administrator:

```powershell
Set-ExecutionPolicy RemoteSigned
```

### Pull all submodules
Run `pull-all-submodules.ps1` script:

```powershell
.\pull-all-submodules.ps1
```

### Restore mongo data
Add your dump to `dump\` folder and run `mongorestore.ps1` script with collection name as parameter:

```powershell
# Restore accounts data:
.\mongorestore.ps1 accounts

# Restore events data:
.\mongorestore.ps1 events 
```