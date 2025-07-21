import array

# pyright: reportUndefinedVariable=false

# PWG RLE compress an input buffer to an output buffer
# r0: input buffer (const unsigned char *)
# r1: input size (unsigned int)
# r2: output buffer (unsigned char *)
@micropython.asm_thumb
def pwgrle_encode(r0, r1, r2) -> uint:
    add(r1, r0, r1)

    # r0 = input_ptr, on return length of output
    # r1 = end of input
    # r2 = output_ptr
    # r3 = start of output
    # r4 = start of literal or duplicate
    # r5 = end of literal or duplicate
    # r6 = scratch
    # r7 = scratch

    push({r2})                      # push start of output

    label(main_loop)
    cmp(r0, r1)                     # compare input_ptr with end of input
    bge(done)                       # if input_ptr >= end then done

    # find a literal run
    mov(r4, r0)                     # r4 = literal_start = input_ptr
    mov(r5, r0)                     # r5 = literal_end = input_ptr

    label(literal_loop)
    cmp(r5, r1)                     # compare literal_end with end of input
    bge(literal_loop_end)           # if literal_end >= end then break

    add(r6, r5, 1)                  # r6 = literal_end + 1
    cmp(r6, r1)                     # check if literal_end + 1 is within bounds
    bge(check_literal_max_len)      # if not, can't check for 2 identical bytes

    ldrb(r7, [r5, 0])               # r7 = input[literal_end]
    ldrb(r6, [r6, 0])               # r6 = input[literal_end + 1]
    cmp(r7, r6)                     # compare input[literal_end] with input[literal_end + 1]
    beq(literal_loop_end)           # if equal, found at least 2 identical bytes, break literal scan

    label(check_literal_max_len)
    sub(r6, r5, r4)                 # r6 = literal_end - literal_start
    cmp(r6, 128)                    # compare with max literal run length (128)
    bge(literal_loop_end)           # if >= 128, break

    add(r5, 1)                      # literal_end++
    b(literal_loop)

    label(literal_loop_end)
    sub(r6, r5, r4)                 # r6 = count = literal_end - literal_start

    cmp(r6, 2)                      # if count >= 2, process literal run
    blt(try_duplicate_run)          # if count < 2, no literal run (or single byte case), try duplicate

    movw(r7, 257)                   # r6 = 257 - count (control byte for literal)
    sub(r6, r7, r6)
    strb(r6, [r2, 0])               # store control byte at output_ptr
    add(r2, 1)                      # output_ptr++

    mov(r7, r4)                     # r7 = copy_ptr = literal_start
    label(copy_literal_bytes_loop)
    cmp(r7, r5)                     # compare copy_ptr with literal_end
    bge(literal_copy_done)          # if copy_ptr >= literal_end, done copying
    ldrb(r6, [r7, 0])               # r6 = input[copy_ptr]
    strb(r6, [r2, 0])               # store literal byte at output_ptr
    add(r7, 1)                      # copy_ptr++
    add(r2, 1)                      # output_ptr++
    b(copy_literal_bytes_loop)

    label(literal_copy_done)
    mov(r0, r5)                     # input ptr = literal_end + 1
    b(main_loop)                    # continue to next iteration of main loop

    label(try_duplicate_run)
    cmp(r0, r1)                     # compare input_ptr with end of input (redundant if coming from literal section)
    bge(done)                       # if input_ptr >= end then done

    # find a duplicate run
    mov(r4, r0)                     # r4 = duplicate_start = input_ptr
    mov(r5, r0)                     # r5 = duplicate_end = input_ptr

    label(duplicate_loop)
    add(r6, r5, 1)                  # r6 = duplicate_end + 1
    cmp(r6, r1)                     # check if duplicate_end + 1 is within bounds
    bge(duplicate_loop_end)         # if not, break

    ldrb(r7, [r5, 0])               # r7 = input[duplicate_end]
    ldrb(r6, [r6, 0])               # r6 = input[duplicate_end + 1]
    cmp(r7, r6)                     # compare input[duplicate_end] with input[duplicate_end + 1]
    bne(duplicate_loop_end)         # if not equal, break

    sub(r6, r5, r4)                 # r6 = duplicate_end - duplicate_start
    cmp(r6, 127)                    # compare with max duplicate run length (127 = count - 1)
    bge(duplicate_loop_end)         # if >= 127, break

    add(r5, 1)                      # duplicate_end++
    b(duplicate_loop)

    label(duplicate_loop_end)

    sub(r6, r5, r4)                 # r6 = control byte for duplicate = count - 1 = (duplicate_end - duplicate_start)
    strb(r6, [r2, 0])               # store control byte at output_ptr
    add(r2, 1)                      # output_ptr++

    ldrb(r7, [r4, 0])               # r7 = input[duplicate_start] (the duplicated byte)
    strb(r7, [r2, 0])               # store the duplicated byte
    add(r2, 1)                      # output_ptr++

    add(r5, 1)                      # input_ptr = duplicate_end + 1
    mov(r0, r5)
    b(main_loop)                    # continue to next iteration of main loop

    label(done)
    pop({r3})                       # r3 = pop start of output
    sub(r0, r2, r3)                 # return output buffer length = output_ptr - start of output

# Packbits compress an input buffer to an output buffer
# r0: input buffer (const unsigned char *)
# r1: input size (unsigned int)
# r2: output buffer (unsigned char *)
@micropython.asm_thumb
def packbits_encode(r0, r1, r2) -> uint:
    add(r1, r0, r1)

    # r0 = input_ptr, on return length of output
    # r1 = end of input
    # r2 = output_ptr
    # r3 = start of output
    # r4 = start of literal or duplicate
    # r5 = end of literal or duplicate
    # r6 = scratch
    # r7 = scratch

    push({r2})                      # push start of output

    label(main_loop)
    cmp(r0, r1)                     # compare input_ptr with end of input
    bge(done)                       # if input_ptr >= end then done

    # find a literal run
    mov(r4, r0)                     # r4 = literal_start = input_ptr
    mov(r5, r0)                     # r5 = literal_end = input_ptr

    label(literal_loop)
    cmp(r5, r1)                     # compare literal_end with end of input
    bge(literal_loop_end)           # if literal_end >= end then break

    add(r6, r5, 1)                  # r6 = literal_end + 1
    cmp(r6, r1)                     # check if literal_end + 1 is within bounds
    bge(check_literal_max_len)      # if not, can't check for 3 identical bytes

    ldrb(r7, [r5, 0])               # r7 = input[literal_end]
    ldrb(r6, [r6, 0])               # r6 = input[literal_end + 1]
    cmp(r7, r6)                     # compare input[literal_end] with input[literal_end + 1]
    bne(check_literal_max_len)      # if not equal, no potential duplicate here, continue literal scan

    add(r6, r5, 2)                  # r6 = literal_end + 2
    cmp(r6, r1)                     # check if literal_end + 2 is within bounds
    bge(check_literal_max_len)      # if not, can't check for 3 identical bytes

    ldrb(r6, [r6, 0])               # r6 = input[literal_end + 2]
    cmp(r7, r6)                     # compare input[literal_end] with input[literal_end + 2]
    beq(literal_loop_end)           # if equal, found at least 3 identical bytes, break literal scan

    label(check_literal_max_len)
    sub(r6, r5, r4)                 # r6 = literal_end - literal_start
    cmp(r6, 128)                    # compare with max literal run length (128)
    bge(literal_loop_end)           # if >= 128, break

    add(r5, 1)                      # literal_end++
    b(literal_loop)

    label(literal_loop_end)
    sub(r6, r5, r4)                 # r6 = count = literal_end - literal_start

    cmp(r6, 0)                      # if count > 0, process literal run
    ble(try_duplicate_run)          # if count <= 0, no literal run (or single byte case), try duplicate

    sub(r6, 1)                      # r6 = count - 1 (control byte for literal)
    strb(r6, [r2, 0])               # store control byte at output_ptr
    add(r2, 1)                      # output_ptr++

    mov(r7, r4)                     # r7 = copy_ptr = literal_start
    label(copy_literal_bytes_loop)
    cmp(r7, r5)                     # compare copy_ptr with literal_end
    bge(literal_copy_done)          # if copy_ptr >= literal_end, done copying
    ldrb(r6, [r7, 0])               # r6 = input[copy_ptr]
    strb(r6, [r2, 0])               # store literal byte at output_ptr
    add(r7, 1)                      # copy_ptr++
    add(r2, 1)                      # output_ptr++
    b(copy_literal_bytes_loop)

    label(literal_copy_done)
    mov(r0, r5)                     # input ptr = literal_end + 1
    b(main_loop)                    # continue to next iteration of main loop

    label(try_duplicate_run)
    cmp(r0, r1)                     # compare input_ptr with end of input (redundant if coming from literal section)
    bge(done)                       # if input_ptr >= end then done

    # find a duplicate run
    mov(r4, r0)                     # r4 = duplicate_start = input_ptr
    mov(r5, r0)                     # r5 = duplicate_end = input_ptr

    label(duplicate_loop)
    add(r6, r5, 1)                  # r6 = duplicate_end + 1
    cmp(r6, r1)                     # check if duplicate_end + 1 is within bounds
    bge(duplicate_loop_end)         # if not, break

    ldrb(r7, [r5, 0])               # r7 = input[duplicate_end]
    ldrb(r6, [r6, 0])               # r6 = input[duplicate_end + 1]
    cmp(r7, r6)                     # compare input[duplicate_end] with input[duplicate_end + 1]
    bne(duplicate_loop_end)         # if not equal, break

    sub(r6, r5, r4)                 # r6 = duplicate_end - duplicate_start
    cmp(r6, 127)                    # compare with max duplicate run length (127)
    bge(duplicate_loop_end)         # if >= 127, break

    add(r5, 1)                      # duplicate_end++
    b(duplicate_loop)

    label(duplicate_loop_end)
    sub(r6, r5, r4)                 # r6 = count = (duplicate_end - duplicate_start) + 1
    add(r6, 1)

    cmp(r6, 2)                      # need at least 2 identical bytes for a duplicate run
    blt(single_byte_literal)        # if count < 2, cannot form duplicate run, treat as single literal

    mov(r7, 1)                      # r7 = 1 - count (negative value, control byte for duplicate)
    sub(r7, r7, r6)
    strb(r7, [r2, 0])               # store control byte at output_ptr
    add(r2, 1)                      # output_ptr++

    ldrb(r7, [r4, 0])               # r7 = input[duplicate_start] (the duplicated byte)
    strb(r7, [r2, 0])               # store the duplicated byte
    add(r2, 1)                      # output_ptr++

    add(r5, 1)                      # input_ptr = duplicate_end + 1
    mov(r0, r5)
    b(main_loop)                    # continue to next iteration of main loop

    label(single_byte_literal)
    cmp(r0, r1)                     # compare input_ptr with end of input
    bge(done)                       # if input_ptr >= end then done (shouldn't happen if loop condition is correct)

    mov(r7, 0)                      # control byte for 1 literal byte is 0
    strb(r7, [r2, 0])               # store control byte
    add(r2, 1)                      # output_ptr++

    ldrb(r7, [r0, 0])               # r7 = input[input_ptr]
    strb(r7, [r2, 0])               # store the literal byte
    add(r2, 1)                      # output_ptr++
    add(r0, 1)                      # input_ptr++
    b(main_loop)                    # continue to next iteration of main loop

    label(done)
    pop({r3})                       # r3 = pop start of output
    sub(r0, r2, r3)                 # return output buffer length = output_ptr - start of output

# Convert a bitmap to a bytemap where each bit becomes a byte
# Scales up by scale factor, and maps clear & set bits to corresponding bytes
#
# r0: input bitmap (const unsigned char *)
# r1: input bitmap size in bytes (unsigned int)
# r2: output bytemap (unsigned char *)
# r3: [clear byte (unsigned char), set byte (unsigned char), scale factor (unsigned char)]
# returns r0: output bytemap size in bytes
@micropython.asm_thumb
def bitmaptobytemap(r0, r1, r2, r3) -> uint:
    add(r1, r0, r1)                 # change r1 from count to end of input

    push({r2})                      # push start of output

    label(main_loop)

    cmp(r0, r1)                     # if we're at the end of input then we're done
    bge(done)

    # get bitmask at input_ptr and process bits in most significant->least significant order
    ldrb(r7, [r0, 0])               # r7 = bitmask = input[input_ptr]
    mov(r4, 24)
    lsl(r7, r4)                     # shift bitmask left (value <= 24)
    mov(r6, 8)                      # r6 = bitcount (8 bits)

    label(nextbit)

    # map most significant bit to a bytevalue corresponding to the clear or set byte
    mov(r4, 1)
    lsl(r7, r4)                     # get the most significant bit into carry (value <= 1)
    bcs(bitset)
    ldrb(r5, [r3, 0])               # r5 = r3[0] if top bit is clear
    b(bitclear)
    label(bitset)
    ldrb(r5, [r3, 1])               # r5 = r3[1] if top bit is set
    label(bitclear)

    # output bytevalue scale factor times
    ldrb(r4, [r3, 2])               # r4 = r3[2] = repeatcount = scale factor
    cmp(r4, 0)                      # if repeatcount <= 0 then we're done
    ble(done)
    label(repeat)
    strb(r5, [r2, 0])               # output[output_ptr] = bytevalue
    add(r2, 1)                      # output_ptr++
    sub(r4, 1)                      # repeatcount--
    bne(repeat)                     # next repeat

    sub(r6, 1)                      # bitcount--
    bne(nextbit)                    # go back for the next bit

    add(r0, 1)                      # input_ptr++
    b(main_loop)                    # go back for the next bitmask

    label(done)
    pop({r4})                       # r4 = pop start of output
    sub(r0, r2, r4)                 # return output buffer length = output_ptr - start of output

def bitmap_to_escpr(bufin, bufout, scale):
    return bitmaptobytemap(bufin, len(bufin), bufout, array.array('B', [0x01, 0x00, scale]))

def bitmap_to_pwg(bufin, bufout, scale):
    return bitmaptobytemap(bufin, len(bufin), bufout, array.array('B', [0xFF, 0x00, scale]))

if __name__ == '__main__':
    # buf = b'AB'*50
    # # buf = bytearray(range(129))
    # # buf = bytearray(range(16))
    # # buf = bytearray(range(129))+b'\x80\x80'+bytearray(range(1))
    # rlebuf = bytearray(2000)
    # rlelen = pwgrle_encode(buf, len(buf), rlebuf)
    # print(rlelen)
    # rleout = rlebuf[:rlelen]
    # print(rleout)

    b2bbuf = bytearray(2000)
    buf = b'\x0f\x10'
    b2blen = bitmap_to_escpr(buf, b2bbuf, 2)
    b2bout = b2bbuf[:b2blen]
    print(b2bout)

