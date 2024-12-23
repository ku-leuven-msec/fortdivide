#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
#set -o xtrace

# This script can be invoked in the following modes:
# - 'download'      => downloads the dependencies for the MVEE
# - 'build'         => builds the dependencies in a Ubuntu 18.04 docker
# - 'run' (default) => runs the docker, in which you can build and use the MVEE
# - 'dev'           => runs the docker in development mode (all sources are mounted to re-compile)

IMAGE=remon
BUILD_DIR=$PWD/build
DEPS_DIR=$PWD/deps
SHARED_PROJECTS_DIR=$PWD/ext

build_docker() {
    if ! command -v docker &> /dev/null; then
        echo "No docker installed!"
        exit 1
    fi

    docker build . -t $IMAGE
}

download_deps() {
    git submodule update --init --recursive

    # Set the version for the patched libc
    ./scripts/switch_patched_binaries.sh ubuntu20
}

run_docker() {
    if ! command -v x11docker &> /dev/null; then
        echo "No x11docker installed! Download at https://github.com/mviereck/x11docker"
        exit 1
    fi

    # Make these folders here. If docker makes them for us, they will be root-owned...
    mkdir -p $BUILD_DIR
    mkdir -p $SHARED_PROJECTS_DIR

    # This script adds numerous volumes to the container:
    # - the repository, containing all the code
    # - a persistent home folder. This is provided by x11docker, and can contain your config files and bash history (across docker runs!)
    # - a shared 'projects' folder, where you can place applications to build and/or run in the MVEE, as well as their data.
    # - the 'build' data volume. This named volume can be used to incrementally build LLVM (or other applications) in.
    VOLUMES="--mount type=bind,src=$PWD,dst=/opt/repo --mount type=bind,src=$SHARED_PROJECTS_DIR,dst=/projects --mount type=volume,src=build,dst=/build"

    # In development mode, we also mount the source code of the dependencies
    if [ "$#" -eq 1 ]; then
        VOLUMES="$VOLUMES --mount type=bind,src=$DEPS_DIR,dst=/opt/source"
    fi

    # The following command consists of:
    # 1st line: The x11docker invocation and its options (allow for sudo/su, with default password 'x11docker'). Generally, these options aim
    #           to integrate with the host as much as possible, while still allowing us to run and build the MVEE in a dockerized environment.
    #           This reduces container isolation, but as isolation is not the reason we're using x11docker that's not an issue.
    # 2nd line: the docker options (allow ptracing and mount volumes)
    # 3rd line: the actual docker image and the command to run in it
    x11docker --tty --ipc=host --network --interactive --home --sudouser --clipboard --cap-default -- \
        --security-opt seccomp=unconfined -p 8080:8080  --cap-add SYS_PTRACE -ti $VOLUMES -- \
        $IMAGE bash
}

# Check the number of parameters
if [ "$#" -ne 1 ]; then
    echo "No mode specified, trying to just run the docker."
    mode="run"
else
    mode="$1"
fi

case "$mode" in
    build)
        build_docker
        ;;

    download)
        download_deps
        ;;

    run)
        run_docker
        ;;

    dev)
        run_docker 1
        ;;

    *)
        echo "Invalid mode specified!"
        exit 2
        ;;
esac
