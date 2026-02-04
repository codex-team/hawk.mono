# Hawk

Error tracking service

![Right col](https://github.com/user-attachments/assets/2d97cbdc-d828-43de-85fc-c830726c60bf)

This repo contains all subrepos of Hawk modules except Client SDKs (Catchers). It is used for developmnet purposes but also can be used to self-host Hawk.

## Documentation

- [How to use hawk.mono to run local Hawk](docs/how-to-run-local-hawk.md)
- [How to send testing events to the local hawk](docs/how-to-get-events.md)
- [How to view Registry queues](docs/how-to-view-registry-queues.md)

## How to run

1. Run `git submodule init && git submodule update`.
2. Create `.env` file in those repositories where there is `.env.sample` file.
3. Run `docker-compose up` to run all hawk services or list only the necessary services in the command above.

## Logging (Loki + Grafana)

Grafana runs in Docker Compose and ships with a provisioned Logs dashboard that opens by default.

### Local Loki (default)

1. Copy `.env.sample` to `.env` (or update your existing `.env`) and keep the local values:

```
LOKI_ENDPOINT=http://loki:3100/loki/api/v1/push
LOKI_AUTH_HEADER=
GRAFANA_CLOUD_LOKI_USER=
GRAFANA_CLOUD_LOKI_API_KEY=
```

2. Start services: `docker-compose up`
3. Open Grafana: `http://localhost:3001`  
   User: `admin`  Password: `admin`

### Grafana Cloud Loki

1. In `.env`, comment the local `LOKI_ENDPOINT` and set the cloud values:

```
# LOKI_ENDPOINT=http://loki:3100/loki/api/v1/push
LOKI_ENDPOINT=https://<your-cloud-host>/loki/api/v1/push
GRAFANA_CLOUD_LOKI_USER=<your_cloud_loki_user_id>
GRAFANA_CLOUD_LOKI_API_KEY=<your_api_key>
```

2. Start services: `docker-compose up`
3. Open Grafana: `http://localhost:3001`  
   User: `admin`  Password: `admin`

## Troubleshooting

If something went wrong, check this items.

### /api dir is empty after using ./pull-all-submodules.sh

```
git submodule update --remote --merge
```

### `docker-compose up` failed

There can be a problems if docker has an outdated image or volume. You can try rebuild it.

#### Removing and image

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

#### Removing a volume

1. List all volumes: 

```bash
docker volume ls
```

2. Find a volume you want to remove. For example, `hawkmono_api-deps` 

3. Remove volume

```
docker volume rm hawkmono_api-deps
```

4. Build

```bash
docker-compose build api
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
