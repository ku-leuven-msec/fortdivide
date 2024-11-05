# README

**NOTE:** We are continually testing these benchmarks and fixing issues. If, at any point, you run into issues somewhere our best advice is to start from a clean clone again in a few days.

## Running

```bash
cd /wherevever/you/put/the/main/repo/
cd eurosp2025/
./bootstrap.sh
# This will download, compile, and install the kernel as a debian package, requiring a password a few times.
# Since youn are not booted into the correct kernel, it will ask you to reboot to the correct kernel.
sudo reboot

# Just run bootstrap again
cd /wherevever/you/put/the/main/repo/
cd eurosp2025/
./bootstrap.sh

# Run benchmarks, specifically those in the paper.
# This, again, requires a password a few times to switch out the kernel module.
./benchmarking.sh --paper
```

## bootstrapping

All setup can be performed automatically by executing eurosp2025/bootstrap.sh in the eurosp2025 folder.

In its first step, this script will compile the custom kernel required to run fortdivide, this might take a while.
After compiling and installing the kernel as a Debian package the script will exit to prompt you to reboot to the correct kernel version.
All steps afterwards run fully automatically.