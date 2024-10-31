#!/bin/bash

__follower_libc_offset=$(objdump -M intel -t ##benchmark_location##/ReMon-glibc/build/libc.so | grep __pmvee_copy_state_malloc_follower | cut -d ' ' -f 1)
__leader_libc_offset=$(objdump -M intel -t ##benchmark_location##/ReMon-glibc/build/libc.so | grep __pmvee_copy_state_malloc_leader | cut -d ' ' -f 1)

if [[ -z $__follower_libc_offset ]] || [[ -z $__leader_libc_offset ]]
then
    exit 0
else
    echo "c;__pmvee_copy_state_malloc_;$(printf "%d" 0x$__leader_libc_offset);##benchmark_location##/ReMon-glibc/build/libc.so;$(printf "%d" 0x$__follower_libc_offset);##benchmark_location##/ReMon-glibc/build/libc.so"
fi