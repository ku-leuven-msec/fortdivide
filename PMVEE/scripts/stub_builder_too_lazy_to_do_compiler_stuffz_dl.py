#!/usr/bin/python
import os


## PARSE ARGS ##########################################################################################################
import argparse


parser = argparse.ArgumentParser(prog="stub builder", description="I'm too lazy to do compiler stuffz", 
                                 epilog="good luck using this!")
parser.add_argument("--input", "-i", type=str, required=True, help="input file to parse")
parser.add_argument("--output", "-o", type=str, required=True, help="output file to write to")
# parser.add_argument("--libc", "-l", type=str, required=True, help="pmvee libc source directory")
parser.add_argument("--verbose", "-v", action="store_true", required=False)
parser.add_argument("--compiler", "-c", type=str, required=False, default="clang", help="")
parser.add_argument("--no-compile", action="store_true", required=False, help="")
parser.add_argument("--all-one-file", action="store_true", required=False, help="")
parser.add_argument("--debug", "-d", action="store_true", required=False, help="")


args = parser.parse_args()
args.output = '/'.join([item for item in args.output.split('/') if item])
args.output = "%s/%s" % (os.getcwd(), args.output)
## PARSE ARGS ##########################################################################################################


## CONSTANTS ###########################################################################################################
PMVEE_COPY_PREFIX = "__pmvee_copy_"
PMVEE_STUB_PREFIX = "__pmvee_real_"
## CONSTANTS ###########################################################################################################


## UTILITY #############################################################################################################
def debugf(message):
    if args.verbose:
        print(" [DEBUG]: %s" % message.replace('\n', "\n   > "))


def printf(message):
    print(" [MESSG]: %s" % message.replace('\n', "\n   > "))


def exit_error(message):
    print(" [ERROR]: %s" % message.replace('\n', "\n   > "))
    exit(1)


def add_indentation(source, depth=1):
    return ("    "*depth if source else '') + source.replace('\n', "\n%s" % ("    "*depth)).strip(' ')


def add_indentation_partial(source):
    return source.replace('\n', "\n    ").strip(' ')


def list_used_definitions(function_name):
    used_pointer_definitions = []
    used_regular_definitions = []

    for argument_i in function_dict[function_name].arguments:
        if argument_i.type in struct_dict:
            if argument_i.pointer_depth:
                used_pointer_definitions.append(argument_i.type)
            else:
                used_regular_definitions.append(argument_i.type)
    
    new_found = True
    while new_found:
        for struct_i in used_pointer_definitions + used_regular_definitions:
            for member_i in struct_dict[struct_i].members:
                if member_i.type in struct_dict:
                    if member_i.type not in used_pointer_definitions and member_i.type not in used_pointer_definitions:
                        new_found = True
                    if member_i.pointer_depth and member_i.type not in used_pointer_definitions:
                        used_pointer_definitions.append(member_i.type)
                    elif member_i.type not in used_regular_definitions:
                        used_regular_definitions.append(member_i.type)

    return used_regular_definitions, used_pointer_definitions
## UTILITY #############################################################################################################


## DATA ################################################################################################################
 # function:
 #  - name: function name
 #  - ret: return type
 #  - arguments: list of argument_meta
 #  - ret_extra: e.g. static
 #  - ifdef: ifdef requirement
class function_meta:
    def __init__(self, json_source):
        self.name = json_source["name"]
        if "static" in json_source["return"]:
            self.ret_extra = "static"
            json_source["return"] = json_source["return"].replace("static", '').strip()
        else:
            self.ret_extra = None
        self.ret = json_source["return"]
        self.arguments = [ argument_meta(argument_i) for argument_i in json_source["arguments"] ] if "arguments" in json_source else []
        self.ifdef = ( json_source["ifdef"] if "ifdef" in json_source else None )
        self.relies_on = []
        self.library = ( json_source["library"] if "library" in json_source else False )
        self.enterexit = ( json_source["enterexit"] if "enterexit" in json_source else "enterexit" )
        self.diff = ( json_source["diff"] if "diff" in json_source else False )
        self.state = ( (json_source["state"] == "True") if "state" in json_source else True )
        self.copy = ( json_source["copy"] if "copy" in json_source else None )
        self.migration = ( json_source["migration"] if "migration" in json_source else None )


    def plain_definition(self, include_static=True):
        return "extern %s%s%s %s(\n    %s\n)%s" % (
            ( "#if %s\n" % self.ifdef ) if self.ifdef else '',
            ( "%s " % self.ret_extra ) if self.ret_extra and include_static else '',
            self.ret,
            self.name,
            ",\n    ".join([ add_indentation(argument_i.definition()) for argument_i in self.arguments ]),
            "\n#endif\n" if self.ifdef else ''
        )


    def pmvee_definition(self):
        return "extern %s%s%s %s%s(\n    %s\n);%s" % (
            ( "#if %s\n" % self.ifdef ) if self.ifdef else '',
            ( "%s " % self.ret_extra ) if self.ret_extra else '',
            self.ret,
            PMVEE_STUB_PREFIX,
            self.name,
            ",\n    ".join([ add_indentation(argument_i.definition()) for argument_i in self.arguments ]),
            "\n#endif" if self.ifdef else ''
        )


    def pmvee_pt_definition(self):
        return "%s%s%s %s%s(\n    %s\n) = 0x00;%s" % (
            ( "#if %s\n" % self.ifdef ) if self.ifdef else '',
            ( "%s " % self.ret_extra ) if self.ret_extra else '',
            self.ret,
            "(*__pmvee_real_%s_pt)" % self.name,
            ",\n    ".join([ add_indentation(argument_i.definition()) for argument_i in self.arguments ]),
            "\n#endif" if self.ifdef else ''
        )
    

    def write_args_definition(self):
        return "struct __pmvee_%s_args_t\n{\n    %s;\n};" % (self.name,
            ";\n    ".join([ add_indentation(argument_i.definition()) for argument_i in self.arguments ])
        ) if self.arguments else ""
    

    def write_stub_definition(self):
        written = ""
        
        if self.ifdef:
            written += "#if %s\n" % self.ifdef

        if self.arguments:
            if self.library:
                written += "%s (*__pmvee_real_%s_pt)(\n    %s\n) = (void*) 0x00;\n\n" % (
                    self.ret,
                    self.name,
                    ",\n    ".join([ add_indentation(argument_i.definition()) for argument_i in self.arguments ])
                )
            written += "%s%s __attribute__ ((noinline)) %s(\n    %s\n)\n{\n" % (
                ( "%s " % self.ret_extra ) if self.ret_extra else '',
                self.ret,
                self.name,
                ",\n    ".join([ add_indentation(argument_i.definition()) for argument_i in self.arguments ])
            )
        else:
            if self.library:
                written += "%s (*__pmvee_real_%s_pt)() = (void*) 0x00;\n\n" % (
                    self.ret,
                    self.name
                )
            written += "%s%s __attribute__ ((noinline)) %s()\n{\n" % (
                ( "%s " % self.ret_extra ) if self.ret_extra else '',
                self.ret,
                self.name
            )

        written += ('\n')

        written += ("#if   defined(PMVEE_LEADER)\n")
        written += add_indentation(self.write_pmvee_leader_stub())
        written += ("#elif defined(PMVEE_FOLLOWER)\n")
        written += add_indentation(self.write_pmvee_follower_stub())
        written += ("#else\n")
        written += add_indentation(self.write_pmvee_stub())
        written += ("#endif\n")


        written += ("}\n")

        if self.ifdef:
            written += ("#endif\n")

        return written


    def write_pmvee_leader_stub(self):
        if self.migration:
            extra_c_files.append(self.migration)
        if self.copy:
            extra_c_files.append(self.copy)
        written = ''
        if "enter" in self.enterexit:
            if self.state:
                pmvee_args_t = "__pmvee_%s_args_t" % self.name
                written += "size_t __pmvee_args_size = 0;\n"
        elif "exit" in self.enterexit:
            written += "PMVEE_EXIT;\n"
            written += "clear_pointer_lookup();\n"

        if self.arguments:
            if "enter" in self.enterexit:
                if self.state:
                    written += "char* __pmvee_zone = get_pmvee_copy();\n"
                    written += "struct %s* __pmvee_args = (struct %s*)(__pmvee_zone);\n" % (pmvee_args_t, pmvee_args_t)
                    written += "__pmvee_args_size += sizeof(struct %s);\n" % pmvee_args_t
                    written += "\n\n"

                    size_stack.append('&')
                    source_stack.append('')
                    destination_stack.append("__pmvee_args->")
                    for arguemnt_i in self.arguments:
                        written += "__pmvee_args->%s = %s" % (arguemnt_i.name, arguemnt_i.write_copy())
                    source_stack.pop()
                    size_stack.pop()
                    written += "void* full_state_copy_start = (void*) (__pmvee_zone + __pmvee_args_size);\n"
                    if self.copy:
                        written += "%s_copy(__pmvee_zone, &__pmvee_args_size, &%s);\n" % (self.name, self.name)
                    written += "void* state_copy_start = __pmvee_copy_state_leader(__pmvee_zone, &__pmvee_args_size, &%s);\n" % self.name
                    if self.migration:
                        written += "%s_migration(__pmvee_zone, &__pmvee_args_size, &%s);\n" % (self.name, self.name)
                    written += "void* state_copy_end = (void*)(__pmvee_zone + __pmvee_args_size);\n"
                    # written += "__pmvee_copy_all((unsigned long)state_copy_end-(unsigned long)__pmvee_zone);\n"

                    written += "\n\n"
                    # written += "printf(\"%ld\\n\", __pmvee_args_size); fflush(stdout);\n"
                    written += "PMVEE_ENTER(%d, PMVEE_GET_ZONE, full_state_copy_start, state_copy_start, state_copy_end);\n" % function_counter
                    # written += "printf(\"index:%ld\\n\", ngx_http_core_module.ctx_index);fflush(stdout);\n"
                else:
                    written += "PMVEE_ENTER(%d, PMVEE_VOID_ZONE, 0, 0, 0);\n" % function_counter
                    # written += "printf(\"index:%ld\\n\", ngx_http_core_module.ctx_index);fflush(stdout);\n"

                if self.diff:
                    written += "__asm(\"movq %0, %%rax; syscall;\" :: \"i\" (__NR_getpid), \"D\" (0x20) : \"rax\", \"rcx\", \"r11\", \"memory\", \"cc\");\n"

            if self.library:
                written += "\nif (!__pmvee_real_%s_pt)\n{\n" % self.name
                written += "    __pmvee_real_%s_pt = dlsym(RTLD_NEXT, \"%s\");\n" % (self.name, self.name)
                written += "    if (!__pmvee_real_%s_pt) _exit(42);\n" % self.name
                written += "}\n\n"
                written += "%s%s(\n    %s\n);\n" % (
                    ("%s return_val = " % self.ret) if self.ret != "void" else '',
                    "__pmvee_real_%s_pt" % self.name,
                    ",\n    ".join([ argument_i.name for argument_i in self.arguments ])
                )
            else:
                written += "%s%s%s(\n    %s\n);\n" % (
                    ("%s return_val = " % self.ret) if self.ret != "void" else '',
                    PMVEE_STUB_PREFIX,
                    self.name,
                    ",\n    ".join([ argument_i.name for argument_i in self.arguments ])
                )

        else:
            if "enter" in self.enterexit:
                if self.state:
                    written += "char* __pmvee_zone = get_pmvee_copy();\n"
                    written += "void* full_state_copy_start = (void*) (__pmvee_zone + __pmvee_args_size);\n"
                    if self.copy:
                        written += "%s_copy(__pmvee_zone, &__pmvee_args_size, &%s);\n" % (self.name, self.name)
                    written += "void* state_copy_start = __pmvee_copy_state_leader(__pmvee_zone, &__pmvee_args_size, &%s);\n" % self.name
                    if self.migration:
                        written += "%s_migration(__pmvee_zone, &__pmvee_args_size, &%s);\n" % (self.name, self.name)
                    written += "void* state_copy_end = (void*)(__pmvee_zone + __pmvee_args_size);\n"
                    # written += "__pmvee_copy_all((unsigned long)state_copy_end-(unsigned long)__pmvee_zone);\n"
                    # written += "printf(\"%ld\\n\", __pmvee_args_size); fflush(stdout);\n"
                    written += "PMVEE_ENTER(%d, PMVEE_GET_ZONE, full_state_copy_start, state_copy_start, state_copy_end);\n" % function_counter
                    # written += "printf(\"index:%ld\\n\", ngx_http_core_module.ctx_index);fflush(stdout);\n"
                else:
                    written += "PMVEE_ENTER(%d, PMVEE_VOID_ZONE, 0, 0, 0);\n" % function_counter
                    # written += "printf(\"index:%ld\\n\", ngx_http_core_module.ctx_index);fflush(stdout);\n"
            if self.diff:
                written += "__asm(\"movq %0, %%rax; syscall;\" :: \"i\" (__NR_getpid), \"D\" (0x20) : \"rax\", \"rcx\", \"r11\", \"memory\", \"cc\");\n"
            
            if self.library:
                written += "\nif (!__pmvee_real_%s_pt)\n{\n" % self.name
                written += "    __pmvee_real_%s_pt = dlsym(RTLD_NEXT, \"%s\");\n" % (self.name, self.name)
                written += "    if (!__pmvee_real_%s_pt) _exit(42);\n" % self.name
                written += "}\n\n"
                written += "%s%s();\n" % (
                    ("%s return_val = " % self.ret) if self.ret != "void" else '',
                    "__pmvee_real_%s_pt" % self.name
                )
            else:
                written += "%s%s%s();\n" % (
                    ("%s return_val = " % self.ret) if self.ret != "void" else '',
                    PMVEE_STUB_PREFIX,
                    self.name
                )

        if self.enterexit == "enterexit":
            written += "PMVEE_EXIT;\n"
            written += "clear_pointer_lookup();\n"
        written += "return return_val;\n" if self.ret != "void" else ''

        return written


    def write_pmvee_follower_stub(self):
        written = ''

        if "enter" in self.enterexit:
            if self.state:
                pmvee_args_t = "__pmvee_%s_args_t" % self.name
                written += "size_t __pmvee_args_size = 0;\n"
        elif "exit" in self.enterexit:
            written += "PMVEE_EXIT;\n"
            written += "printf(\"should not be reached by follower\\n\");fflush(stdout);\n"
            written += "asm(\"mov %%rax, (0);\" :: );\n"

        if self.arguments:
            if "enter" in self.enterexit:
                if self.state:
                    written += "PMVEE_ENTER(%d, PMVEE_GET_ZONE)\n" % function_counter
                    # written += "printf(\"index:%ld\\n\", ngx_http_core_module.ctx_index);fflush(stdout);\n"
                    if self.diff:
                        written += "__asm(\"movq %0, %%rax; syscall;\" :: \"i\" (__NR_getpid), \"D\" (0x20) : \"rax\", \"rcx\", \"r11\", \"memory\", \"cc\");\n"
                    # written += "__asm(\"movq %%rbx, (0);\" :: \"b\" (__pmvee_args_size));"
                    # written += "asm(\"syscall;\" :: \"a\" (60), \"m\" (__pmvee_args_size) :);\n"
                    # written += "__asm(\"syscall;\" : : \"a\" (__NR_getpid), \"D\" (__pmvee_args_size), \"S\" (0) : \"rcx\", \"r8\", \"r9\", \"r10\", \"r11\", \"memory\", \"cc\");"
                    written += "struct %s* __pmvee_args = (struct %s*)(__pmvee_zone);\n" % (pmvee_args_t, pmvee_args_t)
                    if self.copy:
                        written += "%s_copy(__pmvee_zone, &__pmvee_args_size, &%s);\n" % (self.name, self.name)
                    written += "__pmvee_copy_state_follower(__pmvee_zone, &__pmvee_args_size, &%s);\n" % self.name
                    if self.migration:
                        written += "%s_migration(__pmvee_zone, &__pmvee_args_size, &%s);\n" % (self.name, self.name)
                else:
                    written += "PMVEE_ENTER(%d, PMVEE_VOID_ZONE)\n" % function_counter
                    # written += "printf(\"index:%ld\\n\", ngx_http_core_module.ctx_index);fflush(stdout);\n"
                if self.library:
                    written += "\nif (!__pmvee_real_%s_pt)\n{\n" % self.name
                    written += "    __pmvee_real_%s_pt = dlsym(RTLD_NEXT, \"%s\");\n" % (self.name, self.name)
                    written += "    if (!__pmvee_real_%s_pt) _exit(42);\n" % self.name
                    written += "}\n\n"
                    written += "%s%s(\n    __pmvee_args->%s\n);\n" % (
                        ("%s return_val = " % self.ret) if self.ret != "void" else '',
                        "__pmvee_real_%s_pt" % self.name,
                        ",\n    __pmvee_args->".join([ argument_i.name for argument_i in self.arguments ])
                    )
                else:
                    written += "%s%s%s(\n    __pmvee_args->%s\n);\n" % (
                        ("%s return_val = " % self.ret) if self.ret != "void" else '',
                        PMVEE_STUB_PREFIX,
                        self.name,
                        ",\n    __pmvee_args->".join([ argument_i.name for argument_i in self.arguments ])
                    )
            # else:
            #     written += "%s%s%s(\n    %s\n);\n" % (
            #         ("%s return_val = " % self.ret) if self.ret != "void" else '',
            #         PMVEE_STUB_PREFIX,
            #         self.name,
            #         ",\n    ".join([ argument_i.name for argument_i in self.arguments ])
            #     )
        else:
            if "enter" in self.enterexit:
                if self.state:
                    written += "PMVEE_ENTER(%d, PMVEE_GET_ZONE)\n" % function_counter
                    # written += "printf(\"index:%ld\\n\", ngx_http_core_module.ctx_index);fflush(stdout);\n"
                    if self.diff:
                        written += "__asm(\"movq %0, %%rax; syscall;\" :: \"i\" (__NR_getpid), \"D\" (0x20) : \"rax\", \"rcx\", \"r11\", \"memory\", \"cc\");\n"
                    # written += "asm(\"movq (%[args]), %%rdi; syscall;\" :: \"a\" (60), [args] \"r\" (&__pmvee_args_size), \"m\" (__pmvee_args_size) : \"rdi\");\n"
                    if self.copy:
                        written += "%s_copy(__pmvee_zone, &__pmvee_args_size, &%s);\n" % (self.name, self.name)
                    written += "__pmvee_copy_state_follower(__pmvee_zone, &__pmvee_args_size, &%s);\n" % self.name
                    if self.migration:
                        written += "%s_migration(__pmvee_zone, &__pmvee_args_size, &%s);\n" % (self.name, self.name)
                else:
                    written += "PMVEE_ENTER(%d, PMVEE_VOID_ZONE)\n" % function_counter
                    # written += "printf(\"index:%ld\\n\", ngx_http_core_module.ctx_index);fflush(stdout);\n"
                    if self.diff:
                        written += "__asm(\"movq %0, %%rax; syscall;\" :: \"i\" (__NR_getpid), \"D\" (0x20) : \"rax\", \"rcx\", \"r11\", \"memory\", \"cc\");\n"
            if self.library:
                written += "\nif (!__pmvee_real_%s_pt)\n{\n" % self.name
                written += "    __pmvee_real_%s_pt = dlsym(RTLD_NEXT, \"%s\");\n" % (self.name, self.name)
                written += "    if (!__pmvee_real_%s_pt) _exit(42);\n" % self.name
                written += "}\n\n"
                written += "%s%s();\n" % (
                    ("%s return_val = " % self.ret) if self.ret != "void" else '',
                    "__pmvee_real_%s_pt" % self.name
                )
            else:
                written += "%s%s%s();\n" % (
                    ("%s return_val = " % self.ret) if self.ret != "void" else '',
                    PMVEE_STUB_PREFIX,
                    self.name
                )
        if self.enterexit == "enterexit":
            written += "PMVEE_EXIT;\n"
            written += "printf(\"should not be reched by follower\\n\");fflush(stdout);\n"
        written += "return return_val;\n" if self.ret != "void" else ''

        return written


    def write_pmvee_stub(self):
        written = ''
        return written



 # argument:
 #  - name: argument name
 #  - type: argument type
 #  - pointer_depth: argument's pointer depth.
 #  - ifdef: ifdef requirement
class argument_meta:
    def __init__(self, json_source):
        self.name = json_source["name"]
        self.pointer_depth = json_source["type"].count('*')
        self.type = json_source["type"].replace('*', '').strip()
        self.size = ( json_source["size"] if "size" in json_source else None )
        self.ifdef = ( json_source["ifdef"] if "ifdef" in json_source else None )
        self.ignore = ( bool(json_source["ignore"]) if "ignore" in json_source else False )

    def definition(self):
        return "%s%s%s %s%s" % (
            ( "#if %s\n" % self.ifdef ) if self.ifdef else '',
            self.type,
            ( " %s" % "*"*self.pointer_depth ) if self.pointer_depth else '',
            self.name,
            "\n#endif" if self.ifdef else ''
        )
    

    def write_copy(self):
        written = ''

        if self.pointer_depth and not self.ignore:
            if self.type in struct_dict:
                struct_t = struct_dict[self.type]
                written += struct_t.write_copy_call(self.name)
            elif self.size:
                written += "(%s*) (__pmvee_zone + __pmvee_args_size);\n" % self.type
                written += "if (lookup_pointer((void*)%s%s, (void**)&%s%s, %s))\n{\n" % (
                    source_stack[-1],
                    self.name,
                    destination_stack[-1],
                    self.name,
                    self.size
                )
                written += "    __pmvee_args_size+=%s;\n" % self.size
                # written += "printf(\"memcpy(%%p, %%p, %%ld);\", %s%s, %s%s, ((char*) %s%s) - ((char*) %s%s));fflush(stdout);\n" % (
                #     destination_stack[-1],
                #     self.name,
                #     source_stack[-1],
                #     self.name,
                #     source_stack[-1],
                #     self.end,
                #     source_stack[-1],
                #     self.name
                # )
                written += "    assert(__pmvee_args_size < PMVEE_ZONE_ONE_DEFAULT_SIZE);\n"
                written += "    memcpy(%s%s, %s%s, %s);\n" % (
                    destination_stack[-1],
                    self.name,
                    source_stack[-1],
                    self.name,
                    self.size
                )
                written += "}"
            elif "const" in self.type:
                print("TODO: fixme")
                exit(-1)
            else:
                written += "(%s*) (__pmvee_zone + __pmvee_args_size);\n" % self.type
                written += "if (lookup_pointer((void*)%s%s, (void**)&%s%s, sizeof(%s)))\n{\n" % (
                    source_stack[-1],
                    self.name,
                    destination_stack[-1],
                    self.name,
                    self.type
                )
                written += "    __pmvee_args_size+=sizeof(%s);\n" % self.type;
                # written += "printf(\"memcpy(%%p, %%p, %%ld);\", %s%s, %s%s, ((char*) %s%s) - ((char*) %s%s));fflush(stdout);\n" % (
                #     destination_stack[-1],
                #     self.name,
                #     source_stack[-1],
                #     self.name,
                #     source_stack[-1],
                #     self.end,
                #     source_stack[-1],
                #     self.name
                # )
                written += "    assert(__pmvee_args_size < PMVEE_ZONE_ONE_DEFAULT_SIZE);\n"
                written += "    memcpy(%s%s, %s%s, sizeof(%s));\n" % (
                    destination_stack[-1],
                    self.name,
                    source_stack[-1],
                    self.name,
                    self.type
                )
                written += "}"
        else:
            written += self.name
        written += ";\n"

        return written


 # struct:
 #  - name: struct name
 #  - size: static size, if known
 #  - members: list of member_meta
 #  - ifdef: ifdef requirement
class struct_meta:
    def __init__(self, json_source):
        self.name = json_source["name"]
        self.source = ( json_source["source"] if "source" in json_source else None )
        self.size = ( json_source["static size"] if "static size" in json_source else None )
        self.members = [ member_meta(member_i) for member_i in json_source["members"] ]
        self.ifdef = ( json_source["ifdef"] if "ifdef" in json_source else None )
        self.ngx_skip = ( [skip_i for skip_i in json_source["ngx skip"]] if "ngx skip" in json_source else None )
        self.relies_on = []
        self.always = ( "always" in json_source )

    def definition(self):
        return "%sstruct %s\n{\n    %s\n}%s" % (
            ( "#if %s\n" % self.ifdef ) if self.ifdef else '',
            self.name,
            "\n    ".join([ add_indentation(member_i.definition()) for member_i in self.members ]),
            "\n#endif" if self.ifdef else ''
        )

    def debug_definition(self):
        return "%sstruct %s\n{    %s\n}%s" % (
            ( "#if %s\n" % self.ifdef ) if self.ifdef else '',
            self.name,
            "\n    ".join([ add_indentation(member_i.debug_definition()) for member_i in self.members ]),
            "\n#endif" if self.ifdef else ''
        )
    

    def write_copy_definition(self):
        return "%s* __attribute__ ((noinline)) %s%s_ptr(\n    %s* __orig\n)" % (
            self.name,
            PMVEE_COPY_PREFIX,
            self.name,
            self.name
        )
    

    def write_non_ptr_copy_definition(self):
        return "void __attribute__ ((noinline)) %s%s(\n    %s* __orig,\n    %s* __new\n)" % (
            PMVEE_COPY_PREFIX,
            self.name,
            self.name,
            self.name
        )
    

    def write_copy_function(self):
        written = ''

        if self.ifdef:
            written += "#if %s" % self.ifdef
        written += self.write_copy_definition()
        written += "\n{\n"

        written += "    if (__orig == (void*) 0x00)\n    {\n"
        # written += "        printf(\" > ret: %s\"); fflush(stdout);\n" % skip_i
        written += "        return __orig;\n    }\n"
        if self.ngx_skip:
            for skip_i in self.ngx_skip:
                written += "    if (__orig == (void*) %s)\n    {\n" % skip_i
                # written += "        printf(\" > ret: %s\"); fflush(stdout);\n" % skip_i
                written += "        return __orig;\n    }\n"

        written += "    %s* __new;\n" % (self.name)
        written += "    if (!lookup_pointer((void*)__orig, (void**)&__new, sizeof(%s)))\n" % self.name
        written += "        return (void*) __new;\n\n"

        written += "    *(%s*) __new = *(%s*) (__orig);\n\n" % (self.name, self.name)

        written += self.write_copy_body()

        written += "\n    return (void*) __new;\n"

        written += "}\n"
        if self.ifdef:
            written += "#endif"

        return written


    def write_non_ptr_copy_function(self):
        written = ''

        if self.ifdef:
            written += "#if %s" % self.ifdef
        written += self.write_non_ptr_copy_definition()
        written += "\n{\n"

        written += self.write_copy_body()

        written += "}\n"
        if self.ifdef:
            written += "#endif"

        return written
    
    def write_copy_body(self):
        written = ''

        offset_stack = []
        size_stack.append('*')
        source_stack.append("__orig->")
        destination_stack.append("__new->")
        for member_i in self.members:
            if member_i.keep:
                written += "    // doing nothing for %s\n" % member_i.name
            elif not member_i.pointer_depth:
                if member_i.static_copy:
                    if member_i.ifdef:
                        written += "    #if %s\n" % member_i.ifdef
                    written += "    %s" % (add_indentation_partial(member_i.write_copy()))
                    if member_i.type in struct_dict:
                        for nested_member_i in struct_dict[member_i.type].members:
                            if nested_member_i.offset and ".." in nested_member_i.offset:
                                offset_member = nested_member_i.offset.replace("..", '')
                                written += "    __new->%s.%s = " % (member_i.name, nested_member_i.name)
                                written += "(%s*) (((char*)__new%s) + (((char*) __orig->%s.%s) - ((char*) __orig%s)));\n" % (
                                    nested_member_i.type,
                                    ("->%s" % offset_member) if offset_member else '',
                                    member_i.name,
                                    nested_member_i.name,
                                    ("->%s" % offset_member) if offset_member else ''
                                )

                    if member_i.ifdef:
                        written += "    #endif\n"
                else:
                    written += "    // doing nothing for %s\n" % member_i.name
            elif member_i.offset:
                if ".." in member_i.offset:
                    continue
                if member_i.ifdef:
                    offset_stack.append("    #if %s\n" % member_i.ifdef)
                offset_stack.append("    __new->%s = " % member_i.name)
                offset_stack.append("(%s*) (((char*)__new->%s) + (((char*) __orig->%s) - ((char*) __orig->%s)));\n" % (
                    member_i.type,
                    member_i.offset,
                    member_i.name,
                    member_i.offset
                ))
                if member_i.ifdef:
                    offset_stack.append("    #endif\n")
            else:
                if member_i.ifdef:
                    written += "    #if %s\n" % member_i.ifdef
                
                written_temp = add_indentation(member_i.write_copy())
                if member_i.ngx_skip:
                    if_pre = "if"
                    for ngx_skip_i in member_i.ngx_skip:
                        written += "    %s (%s%s == (void*)%s) %s%s = (%s%s)%s%s;\n" % (
                            if_pre,
                            source_stack[-1],
                            ngx_skip_i[0],
                            ngx_skip_i[1],
                            destination_stack[-1],
                            member_i.name,
                            member_i.type,
                            '*'*member_i.pointer_depth,
                            source_stack[-1],
                            member_i.name
                        )
                        if_pre = "else if"
                    written += "    else\n    {\n    "
                    written += add_indentation(written_temp)
                    written += "    }\n"
                else:
                    written += written_temp

                if member_i.ifdef:
                    written += "    #endif\n"
        
        for offset_i in offset_stack:
            written += offset_i
        source_stack.pop()
        destination_stack.pop()
        size_stack.pop()

        return written
    

    def write_copy_call(self, to_copy):
        if self.name not in used_definitions_stack:
            used_definitions_stack.append(self.name)
        return "%s%s_ptr(\n    %s%s\n)" % (
            PMVEE_COPY_PREFIX,
            self.name,
            source_stack[-1],
            to_copy
        )
    

    def write_non_ptr_copy_call(self, to_copy):
        if self.name not in used_static_definitions_stack:
            used_static_definitions_stack.append(self.name)
        return "%s%s(\n    &%s%s,\n    &%s%s\n)" % (
            PMVEE_COPY_PREFIX,
            self.name,
            source_stack[-1],
            to_copy,
            destination_stack[-1],
            to_copy
        )


 # member:
 #  - name: member name
 #  - type: member type
 #  - pointer_depth: member's pointer depth
 #  - static size: 
 #  - sub_size:
 #  - ifdef: ifdef requirement
class member_meta:
    def __init__(self, json_source):
        self.name = json_source["name"]
        self.pointer_depth = json_source["type"].count('*')
        self.type = json_source["type"].replace('*', '').strip()
        self.static_size = ( json_source["static size"] if "static size" in json_source else None )
        self.member_size = ( json_source["member size"] if "member size" in json_source else None )
        self.sub_size = ( json_source["sub size"] if "sub size" in json_source else None )
        self.offset = ( json_source["offset"] if "offset" in json_source else None )
        self.end = ( json_source["end"] if "end" in json_source else None )
        self.ifdef = ( json_source["ifdef"] if "ifdef" in json_source else None )
        self.static_copy = ( bool(json_source["static copy"]) if "static copy" in json_source else False )
        self.ngx_skip = ( [[ngx_skip_i[0], ngx_skip_i[1]] for ngx_skip_i in  json_source["ngx skip"]] 
                         if "ngx skip" in json_source else None )
        self.keep = ( bool(json_source["keep"]) if "keep" in json_source else None )

    def definition(self):
        return "%s%s%s %s%s" % (
            ( "#if %s\n" % self.ifdef ) if self.ifdef else '',
            self.type,
            ( " %s" % "*"*self.pointer_depth ) if self.pointer_depth else '',
            self.name,
            "\n#endif" if self.ifdef else ''
        )

    def debug_definition(self):
        return "%s%s%s %s (static size: %s, member size: %s, sub size: %s)%s" % (
            ( "#if %s\n" % self.ifdef ) if self.ifdef else '',
            self.type,
            ( " %s" % "*"*self.pointer_depth ) if self.pointer_depth else '',
            self.name,
            self.static_size,
            self.member_size,
            self.sub_size,
            "\n#endif" if self.ifdef else ''
        )
    

    def write_copy(self):
        written = ''
        global pointer_counter

        structless_type = self.type.split("struct ")
        if len(structless_type) > 1:
            structless_type = structless_type[1]
        else:
            structless_type = self.type

        if self.pointer_depth > 1 and self.member_size:
            written += "%s%s;\n" % (source_stack[-1], self.name)
            written += "if (%s%s != (void*) 0x00)\n" % (source_stack[-1], self.name)
            written += "{\n"
            written += "    if (lookup_pointer((void*)__orig->%s, (void**)&__new->%s, %s%s * sizeof(%s%s)))\n" % (self.name, self.name, destination_stack[-1], self.member_size, self.type, "*"*(self.pointer_depth - 1))
            written += "    {\n"

            written += "        for (int i = 0; i < %s%s; i++)\n        {\n" % (destination_stack[-1], self.member_size)
            if self.pointer_depth == 1:
                print("TODO")
                return written + "}"
            elif self.pointer_depth - 1 == 1:
                if structless_type in struct_dict:
                    struct_t = struct_dict[structless_type]
                    written += add_indentation(struct_t.write_copy_call("%s[i]" % self.name), 3) + ';\n'
            else:
                print("FIXME")
                return written + "}"
            written += "        }\n"
            written += "    }\n"

            return written + "}\n"

        elif self.pointer_depth:
            while self.pointer_depth > 1:
                written += "(%s**) %s" % (self.type, hex(pointer_counter))
                pointer_counter += pointer_incr
                printf("FIXME")
                return written + ";\n"

            if structless_type in struct_dict:
                struct_t = struct_dict[structless_type]
                written += struct_t.write_copy_call(self.name)
            elif self.offset:
                exit_error("You should not get here.")
            elif self.end:
                written += "if (lookup_pointer((void*)%s%s, (void**)&%s%s, (int)(((char*) %s%s) - ((char*) %s%s))))\n{\n" % (
                    source_stack[-1],
                    self.name,
                    destination_stack[-1],
                    self.name,
                    source_stack[-1],
                    self.end,
                    source_stack[-1],
                    self.name
                )
                # written += "printf(\"memcpy(%%p, %%p, %%ld);\", %s%s, %s%s, ((char*) %s%s) - ((char*) %s%s));fflush(stdout);\n" % (
                #     destination_stack[-1],
                #     self.name,
                #     source_stack[-1],
                #     self.name,
                #     source_stack[-1],
                #     self.end,
                #     source_stack[-1],
                #     self.name
                # )
                written += "    memcpy(%s%s, %s%s, ((char*) %s%s) - ((char*) %s%s));\n" % (
                    destination_stack[-1],
                    self.name,
                    source_stack[-1],
                    self.name,
                    source_stack[-1],
                    self.end,
                    source_stack[-1],
                    self.name
                )
                written += "}"
            elif self.member_size:
                written += "if (lookup_pointer((void*)%s%s, (void**)&%s%s, %s%s))\n{\n" % (
                    source_stack[-1],
                    self.name,
                    destination_stack[-1],
                    self.name,
                    source_stack[-1],
                    self.member_size
                )
                # written += "printf(\"memcpy(%%p, %%p, %%ld);\", %s%s, %s%s, ((char*) %s%s) - ((char*) %s%s));fflush(stdout);\n" % (
                #     destination_stack[-1],
                #     self.name,
                #     source_stack[-1],
                #     self.name,
                #     source_stack[-1],
                #     self.end,
                #     source_stack[-1],
                #     self.name
                # )
                written += "    memcpy(%s%s, %s%s, %s%s);\n" % (
                    destination_stack[-1],
                    self.name,
                    source_stack[-1],
                    self.name,
                    source_stack[-1],
                    self.member_size
                )
                written += "}"
            else:
                written += "    __new->%s = (%s*) %s" % (self.name, self.type, hex(pointer_counter))
                pointer_counter += pointer_incr
        else:
            if self.type in struct_dict:
                if self.static_copy:
                    written += struct_dict[self.type].write_non_ptr_copy_call(self.name)
                else:
                    exit_error("The forgotten copy case.")
            else:
                written += self.name;
        written += ";\n"

        return written
## DATA ################################################################################################################


## READ IN DATA FROM INPUT #############################################################################################
import json


function_dict     = {}
struct_dict       = {}
includes          = []
compiler_includes = []
extra_c_files     = []


with open(args.input, 'r') as input_file:
    input_json = json.load(input_file)
    for item in input_json:
        if item["meta"] == "function":
            if item["name"] in function_dict:
                exit_error("function with name %s already defined. Previous defintion:\n%s" % (
                    item["name"],
                    function_dict[item["name"]].definition()
                ))
            function_dict[item["name"]] = function_meta(item)
            debugf("Added function info:\n%s" % function_dict[item["name"]].plain_definition())
        if item["meta"] == "struct":
            if item["name"] in struct_dict:
                exit_error("struct with name %s already defined. Previous defintion:\n%s" % (
                    item["name"],
                    struct_dict[item["name"]].definition()
                ))
            struct_dict[item["name"]] = struct_meta(item)
            debugf("Added struct info:\n%s" % struct_dict[item["name"]].debug_definition())
        if item["meta"] == "includes":
            includes = item["includes"]
        if item["meta"] == "compiler includes":
            compiler_includes = item["includes"]

function_counter = 0
pointer_counter = 0x800850000
pointer_incr = 0x1000000000
## READ IN DATA FROM INPUT #############################################################################################


## PROCESSORS ##########################################################################################################
## PROCESSORS ##########################################################################################################


## WRITE FUNCTION STUBS ################################################################################################
used_definitions_stack = []
used_static_definitions_stack = []
source_stack = []
destination_stack = []
size_stack = []

for struct in struct_dict:
    if struct_dict[struct].always:
        print("struct: %s" % struct)
        used_definitions_stack.append(struct)

if not os.path.exists(args.output):
    os.mkdir(args.output)
processing_definitions = []
processing_static_definitions = []

output_file_name = "%s/stubs.c" % args.output if args.all_one_file else ""
output_mode = 'a' if args.all_one_file else 'w'

if args.all_one_file:
    with open(output_file_name, 'w') as output_file:
        output_file.write("")
        output_file.write("#if defined(PMVEE_LEADER) || defined(PMVEE_FOLLOWER)\n\n")


for function_name in function_dict:
    if not args.all_one_file:
        output_file_name = "%s/%s.c" % (args.output, function_name)
    with open(output_file_name, output_mode) as output_file:
        output_file.write("#include \"stubs.h\"\n\n")

        debugf("Writing stub for %s" % function_name)
        function_counter += 1
        output_file.write(function_dict[function_name].write_stub_definition())


while True:
    for struct_name in used_definitions_stack:
        debugf("writing function for %s pointer copy" % struct_name)
        if struct_name not in processing_definitions:
            processing_definitions.append(struct_name)
        else:
            continue
        if not args.all_one_file:
            output_file_name = "%s/%s_ptr.c" % (args.output, struct_name.replace(' ', '_'))
        with open(output_file_name, output_mode) as output_file:
            output_file.write("#include \"stubs.h\"\n\n")
            output_file.write("#ifdef PMVEE_LEADER\n")
            output_file.write(struct_dict[struct_name].write_copy_function())
            output_file.write("#endif\n\n")

    for struct_name in used_static_definitions_stack:
        debugf("writing function for %s static copy" % struct_name)
        if struct_name not in processing_static_definitions:
            processing_static_definitions.append(struct_name)
        else:
            continue
        if not args.all_one_file:
            output_file_name = "%s/%s.c" % (args.output, struct_name.replace(' ', '_'))
        with open(output_file_name, output_mode) as output_file:
            output_file.write("#include \"stubs.h\"\n\n")
            output_file.write("#ifdef PMVEE_LEADER\n")
            output_file.write(struct_dict[struct_name].write_non_ptr_copy_function())
            output_file.write("#endif\n")

    if len(processing_definitions) == len(used_definitions_stack) and len(processing_static_definitions) == len(used_static_definitions_stack):
        break


with open("%s/stubs.h" % args.output, 'w') as output_header:
    output_header.write("#ifndef __PMVEE_%s_H\n"   % args.output.split('/')[-1].upper())
    output_header.write("#define __PMVEE_%s_H\n\n" % args.output.split('/')[-1].upper())
    output_header.write("#define _GNU_SOURCE\n\n")
    output_header.write("#include \"assert.h\"\n")
    output_header.write("#include \"string.h\"\n")
    output_header.write("#include \"PMVEE.h\"\n\n")
    written_sources = []
    for struct_name in struct_dict:
        struct_temp = struct_dict[struct_name]
        if struct_temp.source:
            for source_file in struct_temp.source:
                if source_file in written_sources:
                    continue
                output_header.write("#include \"%s\"\n" % source_file)
                written_sources.append(source_file)
    for include_i in includes:
        if include_i in written_sources:
            continue
        output_header.write("#include \"%s\"\n" % include_i)
        written_sources.append(include_i)
    output_header.write("\n")
    for function_name in function_dict:
        output_header.write(function_dict[function_name].write_args_definition())
    output_header.write("\n\n")
    output_header.write("#ifdef PMVEE_LEADER\n")
    for struct_name in used_definitions_stack:
        output_header.write("%s;\n\n" % struct_dict[struct_name].write_copy_definition())
    for struct_name in used_static_definitions_stack:
        output_header.write("%s;\n\n" % struct_dict[struct_name].write_non_ptr_copy_definition())
    output_header.write("#endif\n\n")
    for function_name in function_dict:
        output_header.write("%s;\n" % function_dict[function_name].pmvee_definition())
        output_header.write("%s;\n" % function_dict[function_name].plain_definition())
    output_header.write("\n#endif\n")


if args.all_one_file:
    with open(output_file_name, 'a') as output_file:
        output_file.write("\n\n#endif")
## WRITE FUNCTION STUBS ################################################################################################

## COMPILE #############################################################################################################
if args.no_compile:
    exit(0)
import os
import subprocess

command_includes = []
for source in written_sources:
    if "/".join(source.split("/")[:-1]) not in command_includes:
        command_includes.append("-I%s" % "/".join(source.split("/")[:-1]))

os.chdir(args.output)
command = [
    args.compiler,
    "-DPMVEE_LEADER",
    "-o",
    "%s_l.so" % args.input.split('/')[-1].split('.')[0],
    "-shared",
    "-O3",
    "-I##fortdivide_location##/PMVEE/",
    "-L##fortdivide_location##/PMVEE/",
    "-lpmvee",
    # "-ldl",
    "-g",
    "-DPMVEE_LIBC_COPY",
    "-fPIC"
]
command += [ "-I%s" % include for include in compiler_includes ]
command += [ c_file for c_file in extra_c_files ]
command += command_includes
for function_name in function_dict:
    command.append("%s/%s.c" % (args.output, function_name))
for struct_name in used_definitions_stack:
    command.append("%s/%s_ptr.c" % (args.output, struct_name.replace(' ', '_')))
for struct_name in used_static_definitions_stack:
    command.append("%s/%s.c" % (args.output, struct_name.replace(' ', '_')))
compilation_result = subprocess.run(command, capture_output=True, text=True)
if compilation_result.returncode:
    print(compilation_result.stderr)
    exit(1)
command[1] = "-DPMVEE_FOLLOWER"
command[3] = "%s_f.so" % args.input.split('/')[-1].split('.')[0]
compilation_result = subprocess.run(command, capture_output=True, text=True)
if compilation_result.returncode:
    print(compilation_result.stderr)
    exit(1)
## COMPILE #############################################################################################################