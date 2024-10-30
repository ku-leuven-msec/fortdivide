#!/bin/bash
set -e

## top level remon
## top level remon

## fortdivide changes to ReMon build and config
cd ../

./bootstrap.sh
cd build/
make enable-ipmon-pmvee && make benchmark && make -j 1>/dev/null
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
    CFLAGS="-g -O2 -fno-builtin -Wno-alloca-larger-than -ggdb -fno-omit-frame-pointer" ../configure --enable-stackguard-randomization --enable-obsolete-rpc --enable-pt_chown --with-selinux --enable-lock-elision=no --enable-addons=nptl --prefix=/usr/ --sysconfdir=/etc/ --no-create --no-recursion
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
sed -r -i "s.##benchmark_location##.$(readlink -f ./).g" ./pmvee_config/MVEE.ini.patch/*

cd ../
patch -d ./ -p 1 < eurosp2025/pmvee_config/MVEE.ini.patch


cd ./PMVEE/allocator/
make
cd ../
make lib
make module-install
cd ../eurosp2025
## final benchmark setup