"""Steam Heart's [T-En by Psyklax v0.99] crash fix.

The translation replaced the 2-byte character fetch in ST1-ST7.EXE
(mov ah,[si] / sub al,al / mov cl,[si+1]) with `lcall 25E3:xxxx`, where
xxxx is a helper the patch appended near the end of each stage (ASCII ->
half-width code, retf). 25E3 is an absolute segment from the translator's
own machine (load segment 13C6h) with no relocation entry, so under any
other DOS memory layout the call lands inside unrelated game code and the
stack unwinds into garbage. This makes each call relocatable: segment
25E3h -> 121Dh (relative to the image) plus a relocation entry. Behaviour on
the translator's layout is unchanged; every other layout now works.

Usage: python make_fix.py <translation.hdi> <out_dir> <dir with the HDI's ST1-ST7.EXE>
Writes <out_dir>/SteamHearts_T-En_v0.99_crashfix.ips, a patched HDI copy
and the patched EXEs. The input HDI is never modified.
"""
import os
import struct
import sys

ABS_SEG = 0x25E3
TRANSLATOR_LOAD = 0x13C6
REL_SEG = ABS_SEG - TRANSLATOR_LOAD            # 121Dh
HELPERS = (b'\x8a\x04\xb4\x85', b'\x8a\x07\xb4\x85')   # mov al,[si]/[bx]; mov ah,85h
SECTOR = 256


def fix_exe(x):
    x = bytearray(x)
    hdr = struct.unpack_from('<H', x, 8)[0] * 16
    nrel = struct.unpack_from('<H', x, 6)[0]
    rofs = struct.unpack_from('<H', x, 0x18)[0]
    img = x[hdr:]
    sites = [i for i in range(len(img) - 5)
             if img[i] == 0x9A and img[i + 3:i + 5] == b'\xe3\x25']
    relocs = {struct.unpack_from('<H', x, rofs + 4 * k + 2)[0] * 16 +
              struct.unpack_from('<H', x, rofs + 4 * k)[0] for k in range(nrel)}
    if not sites:
        return bytes(x), 0
    if rofs + 4 * (nrel + len(sites)) > hdr:
        raise SystemExit('no room for relocation entries')
    for i in sites:
        ip = struct.unpack_from('<H', img, i + 1)[0]
        target = REL_SEG * 16 + ip
        if img[target:target + 4] not in HELPERS:
            raise SystemExit('unexpected helper bytes at %05X' % target)
        if i + 3 in relocs:
            raise SystemExit('site already relocated')
        struct.pack_into('<H', x, hdr + i + 3, REL_SEG)
        struct.pack_into('<HH', x, rofs + 4 * nrel, (i + 3) & 0xF, (i + 3) >> 4)
        nrel += 1
    struct.pack_into('<H', x, 6, nrel)
    return bytes(x), len(sites)


def locate(hdi, data_start, exe, off):
    """HDI offset of byte `off` of `exe`, via its (unique) sector."""
    blk = off // SECTOR * SECTOR
    chunk = exe[blk:blk + SECTOR]
    hits, pos = [], hdi.find(chunk)
    while pos >= 0:
        if (pos - data_start) % SECTOR == 0:
            hits.append(pos)
        pos = hdi.find(chunk, pos + 1)
    if len(hits) != 1:
        raise SystemExit('sector of byte %X found %d times' % (off, len(hits)))
    return hits[0] + (off - blk)


def ips(orig, new):
    out = bytearray(b'PATCH')
    i = 0
    while i < len(orig):
        if orig[i] == new[i]:
            i += 1
            continue
        j = i
        while j < len(orig) and orig[j] != new[j] and j - i < 0xFFFF:
            j += 1
        start = i
        if start == 0x454F46:          # 'EOF' offset: start one byte earlier
            start -= 1
        out += start.to_bytes(3, 'big') + (j - start).to_bytes(2, 'big') + new[start:j]
        i = j
    return bytes(out + b'EOF')


def main():
    src, out_dir = sys.argv[1], sys.argv[2]
    exe_dir = sys.argv[3]
    hdi = open(src, 'rb').read()
    data_start = struct.unpack_from('<I', hdi, 8)[0]
    patched = bytearray(hdi)
    os.makedirs(out_dir, exist_ok=True)
    total = 0
    for n in range(1, 8):
        name = 'ST%d.EXE' % n
        exe = open(os.path.join(exe_dir, name), 'rb').read()
        fixed, count = fix_exe(exe)
        open(os.path.join(out_dir, name), 'wb').write(fixed)
        for off in range(len(exe)):
            if exe[off] != fixed[off]:
                patched[locate(hdi, data_start, exe, off)] = fixed[off]
        total += count
        print('%s: %d call(s) relocated' % (name, count))
    base = os.path.splitext(os.path.basename(src))[0]
    open(os.path.join(out_dir, base + ' (crash fix).hdi'), 'wb').write(patched)
    patch = ips(hdi, bytes(patched))
    open(os.path.join(out_dir, 'SteamHearts_T-En_v0.99_crashfix.ips'), 'wb').write(patch)
    print('%d calls fixed, IPS %d bytes' % (total, len(patch)))


if __name__ == '__main__':
    main()
