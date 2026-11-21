// Remix D3D9 geometry asset hash (positions,indices,geometrydescriptor), same maths as gta4-rtx d3d9_asset_hash.
// input file: u32 n; n * { u32 stride, vcount, icount; u8 verts[stride*vcount]; u16 idx[icount] }  (position = float3 at offset 0)
#define XXH_INLINE_ALL
#include "xxhash.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
int main(int argc, char** argv) {
    FILE* f = fopen(argv[1], "rb"); uint32_t n; if (!f || fread(&n, 4, 1, f) != 1) return 1;
    for (uint32_t g = 0; g < n; g++) {
        uint32_t h[3]; fread(h, 4, 3, f);
        uint32_t stride = h[0], vcount = h[1], icount = h[2];
        uint8_t* v = malloc((size_t)stride * vcount); uint16_t* idx = malloc(icount * 2);
        fread(v, stride, vcount, f); fread(idx, 2, icount, f);
        uint32_t mn = 0xFFFF, mx = 0;
        for (uint32_t i = 0; i < icount; i++) { if (idx[i] < mn) mn = idx[i]; if (idx[i] > mx) mx = idx[i]; }
        uint32_t vc = mx - mn + 1; uint8_t* used = calloc(vc, 1);
        for (uint32_t i = 0; i < icount; i++) { idx[i] -= (uint16_t)mn; used[idx[i]] = 1; }
        XXH64_hash_t ph = 0;
        for (uint32_t i = 0; i < vc; i++) if (used[i]) ph = XXH3_64bits_withSeed(v + (size_t)(mn + i) * stride, 12, ph);
        XXH64_hash_t ih = XXH3_64bits(idx, icount * 2);
        uint32_t topo = 3, itype = 0;
        XXH64_hash_t dh = XXH3_64bits_withSeed(&icount, 4, 0);
        dh = XXH3_64bits_withSeed(&vc, 4, dh); dh = XXH3_64bits_withSeed(&topo, 4, dh); dh = XXH3_64bits_withSeed(&itype, 4, dh);
        XXH64_hash_t hash = XXH64(&ih, 8, ph); hash = XXH64(&dh, 8, hash);
        printf("%016llX %016llx %016llx %016llx %u %u\n", (unsigned long long)hash, (unsigned long long)ph, (unsigned long long)ih, (unsigned long long)dh, icount, vc);
        free(v); free(idx); free(used);
    }
    return 0;
}
