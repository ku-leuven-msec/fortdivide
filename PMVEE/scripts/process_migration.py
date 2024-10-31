#!/usr/bin/python3

import sys
import subprocess


if len(sys.argv) != 3:
    exit(1)


class section_t:
    def __init__(self, name, file_offset, address, size):
        self.name = name
        self.file_offset = file_offset
        self.address = address
        self.symbols = {}
        self.size = size


elf_files = {}


def populate_elf_file_path(file_path):
    if file_path in elf_files:
        return

    elf_data = [[], []]
    
    print(file_path)
    leader_section_headers_a = subprocess.run(["readelf", "--section-headers", "-W", file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode("utf-8").split('\n')
    for lsh_line in leader_section_headers_a:
        lsh_line = lsh_line.strip()
        if not lsh_line:
            continue
        if lsh_line[0] != '[' or "[Nr]" in lsh_line:
            continue
        lsh_line = [line_i for line_i in lsh_line.replace("[ ", '[').split(' ') if line_i]
        section = section_t(lsh_line[1], int(lsh_line[4], 16), int(lsh_line[3], 16), int(lsh_line[5], 16))
        if section.address == 0:
            continue
        leader_section_symbols_lines_a = subprocess.run(["objdump", "-j", lsh_line[1], "-t", file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode("utf-8").split('\n')
        for lss_line in leader_section_symbols_lines_a:
            lss_line = [element for element in lss_line.replace('\t', ' ').split(' ') if element]
            if not lss_line or lss_line[0][0] != '0':
                continue
            lss_address = int(lss_line[0], 16)
            while lss_line and lsh_line[1] not in lss_line[0]:
                lss_line = lss_line[1:]
            if not lss_line:
                pass
            lss_symbol = lss_line[-1]
            lss_size = int(lss_line[1], 16)
            # name, offset in section, size
            if lss_symbol not in section.symbols:
                section.symbols[lss_symbol] = []
            section.symbols[lss_symbol].append([ lss_symbol, lss_address, lss_size ])
        elf_data[0].append(section)

    elf_files[file_path] = elf_data


def get_address(line):
    line_a = line.split(";")
    address = int(line_a[3])
    size = int(line_a[4])
    symbol = line_a[2]
    if symbol == "??":
        return [ address, size ]
    file = line_a[1]
    for section in elf_files[file][0]:
        if symbol in section.symbols:
            symbol_info = section.symbols[symbol]
            if len(symbol_info) > 1:
                print(" > multiple definitions for %s, might need to re-run diff.")
                for symbol_info_i in symbol_info:
                    if symbol_info_i[1] == address and symbol_info_i[2] == size:
                        return [ address, size ]
            else:
                return [ symbol_info[0][1], symbol_info[0][2] ]
    exit(1)


write = {}
pointer_write = {}
with open(sys.argv[1], "r") as input_file:
    while True:
        line = input_file.readline().strip()
        if not line:
            break
        file = line.split(";")[1]
        populate_elf_file_path(file)
        pointer = line.split(";")[0]
        if pointer == "p":
            if file not in pointer_write:
                pointer_write[file] = []
            if line not in pointer_write[file]:
                pointer_write[file].append(line)
        else:
            if file not in write:
                write[file] = []
            if line not in write[file]:
                write[file].append(line)


with open(sys.argv[2], 'wb') as output_file:
    for file in write:
        output_file.write(bytes(file+"\0", "utf-8"))
        print((file+"\0", "utf-8"))
        output_file.write(len(write[file]).to_bytes(8, sys.byteorder))
        print(len(write[file]))
        for item in write[file]:
            address = get_address(item)
            output_file.write(int(address[0]).to_bytes(8, sys.byteorder))
            print(int(address[0]))
            output_file.write(int(address[1]).to_bytes(8, sys.byteorder))
            print(int(address[1]))
        if file in pointer_write:
            output_file.write(len(pointer_write[file]).to_bytes(8, sys.byteorder))
            print(len(pointer_write[file]))
            for item in pointer_write[file]:
                address = get_address(item)
                print(" %d - %d = %d" % (int(address[0]) ,int(item.split(';')[5]), int(address[0]) + int(item.split(';')[5])))
                output_file.write((int(address[0]) + int(item.split(';')[5])).to_bytes(8, sys.byteorder))
                print((int(address[0]) + int(item.split(';')[5])))
        else:
            output_file.write(int(0).to_bytes(8, sys.byteorder))
            print(int(0))
    for file in pointer_write:
        if file in write:
            continue
        output_file.write(bytes(file+'\0', "utf-8"))
        print((file+'\0', "utf-8"))
        output_file.write(int(0).to_bytes(8, sys.byteorder))
        print(int(0))
        output_file.write(len(pointer_write[file]).to_bytes(8, sys.byteorder))
        print(len(pointer_write[file]))
        for item in pointer_write[file]:
            address = get_address(item)
            print(" %d - %d = %d" % (int(address[0]) ,int(item.split(';')[5]), int(address[0]) + int(item.split(';')[5])))
            output_file.write((int(address[0]) + int(item.split(';')[5])).to_bytes(8, sys.byteorder))
            print((int(address[0]) + int(item.split(';')[5])))
    

with open(sys.argv[1], "w") as input_file:
    for file in write:
        for line in write[file]:
            input_file.write("%s\n" % line)
        if file in pointer_write:
            for pointer_line in pointer_write[file]:
                input_file.write("%s\n" % pointer_line)
    for file in pointer_write:
        if file not in write:
            for pointer_line in pointer_write[file]:
                input_file.write("%s\n" % pointer_line)

