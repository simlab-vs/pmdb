# swift:6.2.4-noble
FROM swift@sha256:9bea530093ffff8cf6c259991715ee843fe4d0f932e612f7f4b79cca6e00db87

# The tests run the Python recorder, but the image doesn't ship a Python interpreter.
RUN apt-get -q update \
  && DEBIAN_FRONTEND=noninteractive apt-get -q install -y --no-install-recommends python3 \
  && rm -rf /var/lib/apt/lists/*

# The mount point of the container's build directory (see `devcontainer.json`). A new volume copies
# its ownership, letting the `ubuntu` user write to it.
RUN mkdir -p /workspaces/pytrace-recorder/.build \
  && chown ubuntu:ubuntu /workspaces/pytrace-recorder/.build
