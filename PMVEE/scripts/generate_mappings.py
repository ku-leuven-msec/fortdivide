#!/usr/bin/python3

import json
import subprocess
import argparse

parser = argparse.ArgumentParser(prog="stub builder", description="I'm too lazy to do compiler stuffz", epilog="good luck using this!")
parser.add_argument("--stubs", "-s", type=str, required=False, help=".json file used to generate stubs")
parser.add_argument("--leaders", "-l", type=str, required=False, help="leader binaries to parse")
parser.add_argument("--followers", "-f", type=str, required=False, help="follower binaries to parse")
parser.add_argument("--extras", type=str, default=None, required=False, help="extra offsets in binaries to parse")
parser.add_argument("--state-copies", "-sc", type=str, required=False, help="files to check for state copy functions.")
parser.add_argument("--state-migrations", "-sm", type=str, required=False, help="files to check for state migration functions.")
parser.add_argument("--output", "-o", type=str, required=False, help="output file to write to")
args = parser.parse_args()


stubs_json = json.load(open(args.stubs))
interested_syms = []
for entry in stubs_json:
    if entry["meta"] == "function":
        interested_syms.append(entry["name"])

max_id = 0


extras_to_check = {}
extra_syms = {}
if args.extras:
    with open(args.extras, 'r') as extras_file:
        while True:
            line = extras_file.readline()
            if not line:
                break
            line = line.replace('\n', '').split(';')
            if not line[0]:
                continue
            print(line)
            extra_file = "%s;%s" % (line[0], line[1])
            if extra_file not in extras_to_check:
                extras_to_check[extra_file] = []
            if line[2] not in extras_to_check[extra_file]:
                extras_to_check[extra_file].append(line[2])
for extra_files in extras_to_check:
    extra_files_a = extra_files.split(';')
    all_syms = subprocess.run(["objdump", "--syms", extra_files_a[0]], stdout=subprocess.PIPE).stdout.decode("utf-8").split('\n')
    for sym in all_syms:
        if not sym:
            continue
        sym = sym.split('\n')[0].split(' ')
        if sym[0][0] != "0":
            continue
        if sym[-1] in extras_to_check[extra_files]:
            extra_syms[sym[-1]] = [ extra_files_a[0], int(sym[0], 16), extra_files_a[1], -1 ]
    all_syms = subprocess.run(["objdump", "--syms", extra_files_a[1]], stdout=subprocess.PIPE).stdout.decode("utf-8").split('\n')
    for sym in all_syms:
        if not sym:
            continue
        sym = sym.split('\n')[0].split(' ')
        if sym[0][0] != "0":
            continue
        if sym[-1] in extra_syms:
            extra_syms[sym[-1]][3] = int(sym[0], 16)

# for line in leader_extra_offsets:
#     leader_syms = subprocess.run(["objdump", "--syms", binary], stdout=subprocess.PIPE).stdout.decode("utf-8").split('\n')
#     for sym in leader_syms:
#         if not sym:
#             continue
#         sym = sym.split('\n')[0].split(' ')
#         if sym[0][0] != "0":
#             continue
#         if int(sym[0], 16) in leader_extra_offsets[binary]:
#             if binary not in extra_syms:
#                 extra_syms[binary] = {}
#             if sym[-1] not in extra_syms[binary]:
#                 extra_syms[binary][sym[-1]] = [-1, -1]

mappings = {}
leaders = args.leaders.split(':')
for leader in leaders:
    leader_syms = subprocess.run(["objdump", "--syms", leader], stdout=subprocess.PIPE).stdout.decode("utf-8").split('\n')
    leader_addresses = []
    for sym in leader_syms:
        actual_sym = sym.split('\n')[0].split(' ')[-1]
        if actual_sym in interested_syms:
            leader_addresses.append(int(sym.split(' ')[0].strip(' '), 16))
            print("found %s at offset %lx" % (actual_sym, leader_addresses[-1]))
    for leader_address in leader_addresses:
        next_offset = 0
        next_hit = ""
        next_hit_id = -1
        file = ""
        lines = subprocess.run(["objdump", "-M", "intel", "--start-address=%d" % leader_address, "--stop-address=%s" % (leader_address + 500), "-S", leader], stdout=subprocess.PIPE).stdout.decode("utf-8").split('\n')
        for line in lines:
            if "file format" in line:
                file = line.split(':')[0]
            elif ">:" in line:
                next_offset = line.split(' ')[0].split('\t')[0]
                next_offset = int(next_offset if next_offset else "0", 16)
                next_hit = line.split('<')[-1].split(">:")[0]
            elif "syscall" in line:
                print("hit")
                if next_hit_id in mappings:
                    print("duplicate id")
                    print(line)
                    exit(-1)
                if next_hit_id != -1:
                    next_offset = int(line.split(':')[0], 16) + 2
                    mappings[next_hit_id] = [next_hit, next_offset, file]
                next_hit_id = -1
                break
            elif "r8d,0x" in line and "mov" in line:
                next_hit_id = int(line.split(',')[-1], 16)
                print("found id %lx in %s" % (next_hit_id, line))
                if next_hit_id > max_id:
                    max_id = next_hit_id
            else:
                next_hit_id = -1
                
followers = args.followers.split(':')
for follower in followers:
    follower_syms = subprocess.run(["objdump", "--syms", follower], stdout=subprocess.PIPE).stdout.decode("utf-8").split('\n')
    follower_addresses = []
    for sym in follower_syms:
        actual_sym = sym.split('\n')[0].split(' ')[-1]
        if actual_sym in interested_syms:
            follower_addresses.append(int(sym.split(' ')[0].strip(' '), 16))
    for follower_address in follower_addresses:
        next_offset = 0
        next_hit = ""
        next_hit_id = -1
        file = ""
        lines = subprocess.run(["objdump", "-M", "intel", "--start-address=%d" % follower_address, "--stop-address=%s" % (follower_address + 500), "-S", follower], stdout=subprocess.PIPE).stdout.decode("utf-8").split('\n')
        for line in lines:
            if "file format" in line:
                file = line.split(':')[0]
            elif ">:" in line:
                next_offset = line.split(' ')[0].split('\t')[0]
                next_offset = int(next_offset if next_offset else "0", 16)
                next_hit = line.split('<')[-1].split(">:")[0]
                next_hit_id = -1
            elif "syscall" in line:
                print(next_hit_id)
                print(line)
                if next_hit_id != -1:
                    if next_hit_id not in mappings:
                        print("non-existant id")
                        exit(-1)
                    mappings[next_hit_id].append(next_offset)
                    mappings[next_hit_id].append(file)
                else:
                    continue
                next_hit_id = -1
                break
            elif "r8d,0x" in line and "mov" in line:
                print(line)
                next_hit_id = int(line.split(',')[-1], 16)
            else:
                next_hit_id = -1


if args.state_copies:
    state_copy_sources = [source.split(':') for source in args.state_copies.split(',')]
    for source in state_copy_sources:

        leader_subprocess = subprocess.run(["objdump", "--syms", source[0]], check=True, capture_output=True)
        leader_syms = [sym for sym in subprocess.run(["grep", "__pmvee_state_copy"], input=leader_subprocess.stdout, stdout=subprocess.PIPE).stdout.decode("utf-8").split('\n') if sym]
        if len(leader_syms) > 0 and leader_syms[0] == '':
            leader_syms = None

        follower_subprocess = subprocess.run(["objdump", "--syms", source[1]], check=True, capture_output=True)
        follower_syms = [sym for sym in subprocess.run(["grep", "__pmvee_state_copy"], input=follower_subprocess.stdout, stdout=subprocess.PIPE).stdout.decode("utf-8").strip().split('\n')if sym]
        if len(follower_syms) > 0 and follower_syms[0] == '':
            follower_syms = None

        if leader_syms and follower_syms:
            offsets = {}
            for sym in leader_syms:
                sym = [sym_i for sym_i in sym.strip().split(' ') if sym_i]
                print(sym)
                if sym[-1] in offsets:
                    exit(1)
                offsets[sym[-1]] = [int(sym[0], 16)]
            for sym in follower_syms:
                sym = [sym_i for sym_i in sym.strip().split(' ') if sym_i]
                print(sym)
                if sym[-1] not in offsets:
                    exit(1)
                offsets[sym[-1]] += [int(sym[0], 16)]
                

            for function in offsets:
                max_id+=1
                mappings["c%s" % max_id] = [function, offsets[function][0], source[0], offsets[function][1], source[1]]


if args.state_migrations:
    state_migration_sources = [source.split(':') for source in args.state_migrations.split(',')]
    for source in state_migration_sources:

        leader_subprocess = subprocess.run(["objdump", "--syms", source[0]], check=True, capture_output=True)
        leader_syms = [sym for sym in subprocess.run(["grep", "__pmvee_state_migration"], input=leader_subprocess.stdout, stdout=subprocess.PIPE).stdout.decode("utf-8").split('\n') if sym]
        if len(leader_syms) > 0 and leader_syms[0] == '':
            leader_syms = None

        follower_subprocess = subprocess.run(["objdump", "--syms", source[1]], check=True, capture_output=True)
        follower_syms = [sym for sym in subprocess.run(["grep", "__pmvee_state_migration"], input=follower_subprocess.stdout, stdout=subprocess.PIPE).stdout.decode("utf-8").strip().split('\n')if sym]
        if len(follower_syms) > 0 and follower_syms[0] == '':
            follower_syms = None

        if leader_syms and follower_syms:
            offsets = {}
            for sym in leader_syms:
                sym = [sym_i for sym_i in sym.strip().split(' ') if sym_i]
                print(sym)
                if sym[-1] in offsets:
                    exit(1)
                offsets[sym[-1]] = [int(sym[0], 16)]
            for sym in follower_syms:
                sym = [sym_i for sym_i in sym.strip().split(' ') if sym_i]
                print(sym)
                if sym[-1] not in offsets:
                    exit(1)
                offsets[sym[-1]] += [int(sym[0], 16)]
                

            for function in offsets:
                max_id+=1
                mappings["m%s" % max_id] = [function, offsets[function][0], source[0], offsets[function][1], source[1]]

for extra_sym in extra_syms:
    max_id+=1
    print(extra_sym)
    mappings["%s" % max_id] = [extra_sym, extra_syms[extra_sym][1], extra_syms[extra_sym][0], extra_syms[extra_sym][3], extra_syms[extra_sym][2]]



print(mappings)
with open(args.output, 'w') as output_file:
    for id in mappings:
        output_file.write("%s\n" % ';'.join([str(item) for item in ['c' if 'c' in str(id) else ('m' if 'm' in str(id) else id)] + mappings[id]]))
