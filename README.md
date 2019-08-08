Hawk monorepository for development needs

# Init modules
1. Run `git submodule init && git submodule update`.
2. Create `.env` file in those repositories where there is `.env.sample` file.
3. Run `docker-compose up` to run all hawk services or list only the necessary services in the command above.
