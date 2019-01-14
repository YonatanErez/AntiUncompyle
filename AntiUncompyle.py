import marshal
import bytecode_graph
from dis import opmap
import time
import struct
import os
import argparse


__author__ = "Yonatan Erez"
__version__ = "1.0"


PYTHON_MAGIC = {
    # Python 1
    20121: (1, 5),
    50428: (1, 6),

    # Python 2
    50823: (2, 0),
    60202: (2, 1),
    60717: (2, 2),
    62011: (2, 3),  # a0
    62021: (2, 3),  # a0
    62041: (2, 4),  # a0
    62051: (2, 4),  # a3
    62061: (2, 4),  # b1
    62071: (2, 5),  # a0
    62081: (2, 5),  # a0
    62091: (2, 5),  # a0
    62092: (2, 5),  # a0
    62101: (2, 5),  # b3
    62111: (2, 5),  # b3
    62121: (2, 5),  # c1
    62131: (2, 5),  # c2
    62151: (2, 6),  # a0
    62161: (2, 6),  # a1
    62171: (2, 7),  # a0
    62181: (2, 7),  # a0
    62191: (2, 7),  # a0
    62201: (2, 7),  # a0
    62211: (2, 7),  # a0

    # Python 3
    3000: (3, 0),
    3010: (3, 0),
    3020: (3, 0),
    3030: (3, 0),
    3040: (3, 0),
    3050: (3, 0),
    3060: (3, 0),
    3061: (3, 0),
    3071: (3, 0),
    3081: (3, 0),
    3091: (3, 0),
    3101: (3, 0),
    3103: (3, 0),
    3111: (3, 0),  # a4
    3131: (3, 0),  # a5

    # Python 3.1
    3141: (3, 1),  # a0
    3151: (3, 1),  # a0

    # Python 3.2
    3160: (3, 2),  # a0
    3170: (3, 2),  # a1
    3180: (3, 2),  # a2

    # Python 3.3
    3190: (3, 3),  # a0
    3200: (3, 3),  # a0
    3220: (3, 3),  # a1
    3230: (3, 3),  # a4

    # Python 3.4
    3250: (3, 4),  # a1
    3260: (3, 4),  # a1
    3270: (3, 4),  # a1
    3280: (3, 4),  # a1
    3290: (3, 4),  # a4
    3300: (3, 4),  # a4
    3310: (3, 4),  # rc2

    # Python 3.5
    3320: (3, 5),  # a0
    3330: (3, 5),  # b1
    3340: (3, 5),  # b2
    3350: (3, 5),  # b2
    3351: (3, 5),  # 3.5.2

    # Python 3.6
    3360: (3, 6),  # a0
    3361: (3, 6),  # a0
    3370: (3, 6),  # a1
    3371: (3, 6),  # a1
    3372: (3, 6),  # a1
    3373: (3, 6),  # b1
    3375: (3, 6),  # b1
    3376: (3, 6),  # b1
    3377: (3, 6),  # b1
    3378: (3, 6),  # b2
    3379: (3, 6),  # rc1

    # Python 3.7
    3390: (3, 7),  # a1
    3391: (3, 7),  # a2
    3392: (3, 7),  # a4
    3393: (3, 7),  # b1
    3394: (3, 7),  # b5
}

# python2 pyc header size
MAGIC_SIZE = 4
TIME_SIZE = 4
HEADER_SIZE = MAGIC_SIZE + TIME_SIZE


def get_version_from_magic(magic):
    magic_number = struct.unpack("<H", magic.replace('\r\n', ''))[0]
    return '.'.join([str(i) for i in PYTHON_MAGIC[magic_number]])


def get_timestamp(bin_timestamp):
    modtime = time.asctime(time.localtime(struct.unpack('L', bin_timestamp)[0]))
    return str(modtime)


def edit_code(code):
    bcg = bytecode_graph.BytecodeGraph(code)
    nodes = [x for x in bcg.nodes()]

    for i in xrange(2):
        # NOP
        bcg.add_node(nodes[1], bytecode_graph.Bytecode(0, chr(opmap['NOP'])))
        # Swap twice
        bcg.add_node(nodes[1], bytecode_graph.Bytecode(0, chr(opmap['ROT_TWO'])))
        bcg.add_node(nodes[1], bytecode_graph.Bytecode(0, chr(opmap['ROT_TWO'])))
        # NOP
        bcg.add_node(nodes[1], bytecode_graph.Bytecode(0, chr(opmap['NOP'])))
        # Swap Three times
        bcg.add_node(nodes[1], bytecode_graph.Bytecode(0, chr(opmap['ROT_THREE'])))
        bcg.add_node(nodes[1], bytecode_graph.Bytecode(0, chr(opmap['ROT_THREE'])))
        bcg.add_node(nodes[1], bytecode_graph.Bytecode(0, chr(opmap['ROT_THREE'])))
    return bcg.get_code()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pycfile", action="store", metavar='file.pyc', help="path to .pyc file")
    args = parser.parse_args()

    if not os.path.isfile(args.pycfile):
        print "Error: can't find file - %s " % args.pycfile
        exit(1)

    file_size = os.stat(args.pycfile).st_size
    if file_size <= HEADER_SIZE:
        print "Error: File too small: %s bytes" % file_size
        exit(1)

    # Extract data from the given file
    infile = open(args.pycfile, 'rb')
    magic = infile.read(MAGIC_SIZE)
    timestamp = infile.read(TIME_SIZE)
    try:
        code = marshal.load(infile)
    except ValueError:
        print "Error: incorrect marshal format of code object"
        infile.close()
        exit(1)
    infile.close()

    # Parsing file's content
    interpreter_version = None
    creation_time = None
    try:
        interpreter_version = get_version_from_magic(magic)
        creation_time = get_timestamp(timestamp)
    except struct.error as e:
        print "Error: while parsing header, %s" % e
        exit(1)

    print "Creator interpreter version: python %s" % interpreter_version
    print "Creation time: %s" % creation_time
    print "Code : %s" % code

    # Create protected pyc file
    outfile = open('NEW-' + args.pycfile, 'wb')
    outfile.write(magic)
    outfile.write(timestamp)
    new_code = edit_code(code)
    marshal.dump(new_code, outfile)
    outfile.close()


if __name__ == '__main__':
    main()
