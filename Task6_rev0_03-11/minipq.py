"""Minimal pure-Python Parquet reader (enough for files written by pandas/pyarrow).

Supports: flat schemas, data page v1/v2, PLAIN + dictionary encodings, RLE/bit-packed levels,
UNCOMPRESSED / SNAPPY / GZIP codecs, types BOOLEAN, INT32, INT64, FLOAT, DOUBLE, BYTE_ARRAY,
timestamp logical types (tz kept from pandas metadata when present).
"""
import gzip
import io
import json
import struct
import zlib

import numpy as np
import pandas as pd


# ------------------------------------------------------------------ thrift compact protocol
class TReader:
    def __init__(self, buf, pos=0):
        self.b, self.p = buf, pos

    def byte(self):
        v = self.b[self.p]; self.p += 1; return v

    def varint(self):
        r = s = 0
        while True:
            x = self.byte(); r |= (x & 0x7F) << s; s += 7
            if not x & 0x80:
                return r

    def zz(self):
        v = self.varint(); return (v >> 1) ^ -(v & 1)

    def binary(self):
        n = self.varint(); v = self.b[self.p:self.p + n]; self.p += n; return v

    def value(self, t):
        if t in (1, 2):
            return t == 1
        if t == 3:
            v = self.byte(); return v - 256 if v > 127 else v
        if t in (4, 5, 6):
            return self.zz()
        if t == 7:
            v = struct.unpack_from("<d", self.b, self.p)[0]; self.p += 8; return v
        if t == 8:
            return self.binary()
        if t in (9, 10):
            h = self.byte(); n = h >> 4; et = h & 0x0F
            if n == 15:
                n = self.varint()
            if et in (1, 2):
                return [self.byte() == 1 for _ in range(n)]
            return [self.value(et) for _ in range(n)]
        if t == 11:
            n = self.varint()
            if n == 0:
                return {}
            kv = self.byte(); kt, vt = kv >> 4, kv & 0x0F
            return {self.value(kt): self.value(vt) for _ in range(n)}
        if t == 12:
            return self.struct()
        raise ValueError(f"thrift type {t}")

    def struct(self):
        out, last = {}, 0
        while True:
            h = self.byte()
            if h == 0:
                return out
            t = h & 0x0F; d = h >> 4
            fid = last + d if d else self.zz()
            last = fid
            out[fid] = self.value(t)


# ------------------------------------------------------------------ codecs
def snappy_decompress(src):
    r = TReader(src); n = r.varint(); out = bytearray(); p = r.p
    while p < len(src):
        tag = src[p]; p += 1; kind = tag & 3
        if kind == 0:
            ln = tag >> 2
            if ln >= 60:
                nb = ln - 59; ln = int.from_bytes(src[p:p + nb], "little"); p += nb
            ln += 1; out += src[p:p + ln]; p += ln
            continue
        if kind == 1:
            ln = ((tag >> 2) & 7) + 4; off = ((tag >> 5) << 8) | src[p]; p += 1
        elif kind == 2:
            ln = (tag >> 2) + 1; off = int.from_bytes(src[p:p + 2], "little"); p += 2
        else:
            ln = (tag >> 2) + 1; off = int.from_bytes(src[p:p + 4], "little"); p += 4
        start = len(out) - off
        for i in range(ln):
            out.append(out[start + i])
    assert len(out) == n
    return bytes(out)


def decompress(codec, data, size):
    if codec == 0:
        return data
    if codec == 1:
        return snappy_decompress(data)
    if codec == 2:
        return zlib.decompress(data, 47)
    raise ValueError(f"unsupported codec {codec}")


# ------------------------------------------------------------------ encodings
def rle_bitpacked(buf, bit_width, count, pos=0, end=None):
    end = len(buf) if end is None else end
    out = []; r = TReader(buf, pos); bw_bytes = (bit_width + 7) // 8
    while len(out) < count and r.p < end:
        h = r.varint()
        if h & 1:
            groups = h >> 1; nbytes = groups * bit_width
            chunk = int.from_bytes(buf[r.p:r.p + nbytes], "little"); r.p += nbytes
            mask = (1 << bit_width) - 1
            for i in range(groups * 8):
                out.append((chunk >> (i * bit_width)) & mask if bit_width else 0)
        else:
            n = h >> 1
            v = int.from_bytes(buf[r.p:r.p + bw_bytes], "little"); r.p += bw_bytes
            out.extend([v] * n)
    return out[:count]


def plain(buf, ptype, n, pos=0):
    if ptype == 0:
        bits = np.unpackbits(np.frombuffer(buf, np.uint8, offset=pos), bitorder="little")
        return bits[:n].astype(bool)
    if ptype in (1, 2, 4, 5):
        dt = {1: "<i4", 2: "<i8", 4: "<f4", 5: "<f8"}[ptype]
        return np.frombuffer(buf, dt, count=n, offset=pos).copy()
    if ptype == 6:
        out = []; p = pos
        for _ in range(n):
            ln = struct.unpack_from("<i", buf, p)[0]; p += 4
            out.append(bytes(buf[p:p + ln]).decode("utf-8")); p += ln
        return np.array(out, dtype=object)
    raise ValueError(f"ptype {ptype}")


# ------------------------------------------------------------------ reader
def read_parquet(path):
    b = open(path, "rb").read()
    flen = int.from_bytes(b[-8:-4], "little")
    meta = TReader(b, len(b) - 8 - flen).struct()
    schema = meta[2]
    leaves = [s for s in schema[1:] if 5 not in s or not s.get(5)]
    names = [s[4].decode() for s in leaves]
    kv = {x[1].decode(): x.get(2, b"").decode() for x in meta.get(5, [])}
    pmeta = json.loads(kv["pandas"]) if "pandas" in kv else {}
    cols = {nm: [] for nm in names}
    for rg in meta[4]:
        for ci, cc in enumerate(rg[1]):
            md = cc[3]; ptype = md[1]; codec = md[4]
            nm = names[ci]; sch = leaves[ci]
            max_def = 1 if sch.get(3, 0) == 1 else 0
            start = md.get(11, md[9])
            r = TReader(b, start); total = md[5]; got = 0; dictv = None
            while got < total:
                ph = r.struct(); page = b[r.p:r.p + ph[3]]; r.p += ph[3]
                ptyp = ph[1]
                if ptyp == 2:                                 # dictionary page
                    d = decompress(codec, page, ph[2]); dh = ph[7]
                    dictv = plain(d, ptype, dh[1]); continue
                if ptyp == 0:                                 # data page v1
                    d = decompress(codec, page, ph[2]); dh = ph[5]; n = dh[1]; enc = dh[2]; p = 0
                    if max_def:
                        ln = struct.unpack_from("<i", d, 0)[0]
                        defs = rle_bitpacked(d, 1, n, 4, 4 + ln); p = 4 + ln
                    else:
                        defs = [1] * n
                elif ptyp == 3:                               # data page v2
                    dh = ph[8]; n = dh[1]; enc = dh[4]; dl = dh[5]; rl = dh.get(6, 0)
                    lv = page[:rl + dl]
                    defs = rle_bitpacked(lv, 1, n, rl, rl + dl) if max_def else [1] * n
                    body = page[rl + dl:]
                    compressed = dh.get(7, True)
                    d = decompress(codec, body, ph[2] - rl - dl) if compressed else body; p = 0
                else:
                    raise ValueError(f"page type {ptyp}")
                nn = int(sum(defs))
                if enc in (2, 8):                             # dictionary indices
                    bw = d[p]; idx = rle_bitpacked(d, bw, nn, p + 1)
                    vals = dictv[np.asarray(idx, dtype=np.int64)]
                elif enc == 0:
                    vals = plain(d, ptype, nn, p)
                else:
                    raise ValueError(f"encoding {enc}")
                if nn == n:
                    cols[nm].append(np.asarray(vals))
                else:
                    full = np.empty(n, dtype=object); m = np.asarray(defs, bool)
                    full[m] = vals; full[~m] = None
                    cols[nm].append(full)
                got += n
    df = pd.DataFrame({nm: np.concatenate(v) if v else [] for nm, v in cols.items()})
    tz = {c["name"]: (c.get("metadata") or {}).get("timezone") for c in pmeta.get("columns", [])}
    for s in leaves:
        nm = s[4].decode(); lt = s.get(10, {}); ct = s.get(6)
        if 8 in lt or ct in (9, 10):                          # TIMESTAMP
            unit = "ns"
            if 8 in lt:
                u = lt[8].get(2, {})
                unit = "ms" if 1 in u else "us" if 2 in u else "ns"
            elif ct == 9:
                unit = "ms"
            else:
                unit = "us"
            v = pd.to_numeric(df[nm], errors="coerce")
            ts = pd.to_datetime(v, unit=unit, utc=True)
            z = tz.get(nm)
            df[nm] = ts.dt.tz_convert(z) if z else ts.dt.tz_localize(None)
        elif df[nm].dtype == object and s[1] in (1, 2, 4, 5):
            df[nm] = pd.to_numeric(df[nm], errors="coerce")
        elif df[nm].dtype == object and s[1] == 0:
            df[nm] = df[nm].astype("boolean")
    return df
