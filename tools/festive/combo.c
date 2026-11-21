// find how the runtime combines the three part hashes: combo.exe  (values from the log for vc_stolb_5 pole)
#define XXH_INLINE_ALL
#include "xxhash.h"
#include <stdio.h>
#include <stdint.h>
int main(void) {
    uint64_t p[3] = { 0xb568b6197ccce348ull, 0xf5556e2cfe221c8full, 0xa781fbd796672214ull }, want = 0xa37201b919b26e2eull;
    const char* n = "pid"; int perm[6][3] = { {0,1,2},{0,2,1},{1,0,2},{1,2,0},{2,0,1},{2,1,0} };
    for (int k = 0; k < 6; k++) {
        int* o = perm[k];
        uint64_t a = XXH64(&p[o[1]], 8, p[o[0]]); a = XXH64(&p[o[2]], 8, a);
        uint64_t b = XXH3_64bits_withSeed(&p[o[1]], 8, p[o[0]]); b = XXH3_64bits_withSeed(&p[o[2]], 8, b);
        uint64_t c = XXH64(&p[o[0]], 8, 0); c = XXH64(&p[o[1]], 8, c); c = XXH64(&p[o[2]], 8, c);
        uint64_t d = XXH3_64bits_withSeed(&p[o[0]], 8, 0); d = XXH3_64bits_withSeed(&p[o[1]], 8, d); d = XXH3_64bits_withSeed(&p[o[2]], 8, d);
        uint64_t arr[3] = { p[o[0]], p[o[1]], p[o[2]] };
        uint64_t e = XXH64(arr, 24, 0), f = XXH3_64bits(arr, 24);
        uint64_t r[6] = { a, b, c, d, e, f };
        for (int j = 0; j < 6; j++) printf("%c%c%c m%d %016llx%s\n", n[o[0]], n[o[1]], n[o[2]], j, (unsigned long long)r[j], r[j] == want ? "  <== MATCH" : "");
    }
    return 0;
}
