# AI4EU - AI4Industry Pilot

This is a repository containing part of the code of the [AI4Industry Pilot](https://www.ai4europe.eu/node/106) of the [AI4EU project](www.ai4europe.eu).

# Running the full pilot

To run the full pilot, please use "Deploy to local" in the [AI4EU Experiments Platform]() on the [AI4Industry Pilot solution]() and follow the readme in the package or the [YouTube Tutorial (Deploy and Run)](https://www.youtube.com/watch?v=gM-HRMNOi4w).

# Running parts of the pilot in docker

You can run everything manually without docker, but we recommended the helper script `helper.py`.

You can use `conda` and the script `./create-conda-environment.sh` which creates an environment called `ai4eusudoku` that contains all required prerequisites. If you use conda (and generated the environment as indicated above) then, before doing anything mentioned below, you need to run `conda activate ai4eusudoku` in the shell where you run one of the scripts below.

The following commands build three docker images, run them, and then start an orchestrator outside of docker.

```
$ ./helper.py build-protobufs
$ ./helper.py build
$ ./helper.py run detached
$ ./helper.py orchestrate
```

You can see the running containers with the command

```
$ ./helper.py list
```

You should see a list of three containers, all in status "Up" with ports 8000-8003 exported.

In a new browser window open http://localhost:8000/ and you should see the AI4Industry Pilot Webinterface.

You can follow the logs of each docker container using `./helper.py follow <component>`, for example `./helper.py follow gui`.

For more general information, please consult the [AI4EU Experiments Sudoku Tutorial](https://github.com/peschue/ai4eu-sudoku), in particular its [Readme](https://github.com/peschue/ai4eu-sudoku/blob/main/README.md).
