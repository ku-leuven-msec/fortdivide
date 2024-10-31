#!/bin/bash
set -e

## top level remon
## top level remon

## fortdivide changes to ReMon build and config
cd ../

./bootstrap.sh
cd build/
make enable-ipmon-pmvee && ake block-shm && make benchmark && make -j 1>/dev/null
cd ../

cd eurosp2025/
## fortdivide changes to ReMon build and config

## fortdivide changes to ReMon libc build and config
if [ ! -e ReMon-glibc ]
then
    git clone https://github.com/ReMon-MVEE/ReMon-glibc.git
    cd ReMon-glibc/
    mkdir build-tree
    patch -d ./ -p 1 < ../patches/ReMon-glibc.patch
    cd build-tree
    CFLAGS="-g -O2 -fno-builtin -Wno-alloca-larger-than -ggdb -fno-omit-frame-pointer" ../configure --enable-stackguard-randomization --enable-obsolete-rpc --enable-pt_chown --with-selinux --enable-lock-elision=no --enable-addons=nptl --prefix=/usr/ --sysconfdir=/etc/
    make -j
    # ln -fs $(readlink -f ./) ../../../patched_binaries/libc/amd64/
    ln -fs $(readlink -f ./elf/ld-linux-x86-64.so.2) ../../../patched_binaries/libc/amd64/ld-linux.so # ld-2.31.so
    ln -fs $(readlink -f ./libc.so) ../../../patched_binaries/libc/amd64/libc.so.6 # libc-2.31.so
    ln -fs $(readlink -f ./dlfcn/libdl.so) ../../../patched_binaries/libc/amd64/libdl.so.2 # libdl-2.31.so
    ln -fs $(readlink -f ./math/libm.so) ../../../patched_binaries/libc/amd64/libm.so.6 # libm-2.31.so
    ln -fs $(readlink -f ./nptl/libpthread.so) ../../../patched_binaries/libc/amd64/libpthread.so.0 # libpthread-2.31.so
    ln -fs $(readlink -f ./resolv/libresolv.so) ../../../patched_binaries/libc/amd64/libresolv.so.2 # libresolv-2.31.so
    ln -fs $(readlink -f ./rt/librt.so) ../../../patched_binaries/libc/amd64/librt.so.1 # librt-2.31.so
    ln -fs $(readlink -f ./login/libutil.so) ../../../patched_binaries/libc/amd64/libutil.so.1 # libutil-2.31.so

    cd ../../
fi
## fortdivide changes to ReMon libc build and config

## nginx
if [ ! -e nginx-1.23.3 ]
then
    git clone https://github.com/nginx/nginx.git nginx-1.23.3
    cd nginx-1.23.3
    git checkout release-1.23.3
    patch -d ./ -p 2 < ../patches/nginx-1.23.3.patch
    ln -fs ../build_scripts/nginx-1.23.3-build.sh ./
    ./auto/configure
    cd ../
fi
## nginx

## lighttpd
if [ ! -e lighttpd-1.4.60 ]
then
    git clone https://git.lighttpd.net/lighttpd/lighttpd1.4.git lighttpd-1.4.60
    cd lighttpd-1.4.60
    git checkout lighttpd-1.4.60
    patch -d ./ -p 2 < ../patches/lighttpd-1.4.60.patch
    ln -fs ../build_scripts/lighttpd-1.4.60-build.sh ./
    cd ../
fi
## lighttpd

## final benchmark setup
sed -r -i "s.##benchmark_location##.$(readlink -f ./).g" ./pmvee_config/nginx-1.23.3/*
sed -r -i "s.##benchmark_location##.$(readlink -f ./).g" ./pmvee_config/lighttpd-1.4.60/*
sed -r -i "s.##benchmark_location##.$(readlink -f ../).g" ./microbenchmarks/mapping_count/mapping_count.json
sed -r -i "s.##fortdivide_location##.$(readlink -f ../).g" ./pmvee_config/MVEE.ini.patch

ln -fs $(readlink -f ./pmvee_config/nginx-1.23.3/lib/nginx_l.so) ../patched_binaries/gnomelibs/amd64/

cd ../
patch -d ./ -p 1 < eurosp2025/pmvee_config/MVEE.ini.patch

cd ./PMVEE/allocator/
make
cd ../
make lib
make module-install
cd ../eurosp2025
## final benchmark setup