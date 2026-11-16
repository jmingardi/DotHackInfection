#include "ps2/vu_ops.hpp"
#include <cstdio>
#include <vector>

namespace {
unsigned word = 0;
std::vector<unsigned> reads, addresses;
void capture(int unit, std::uint32_t address) {
    if (unit != 1) std::abort();
#if defined(__SSE2__)
    if (_mm_getcsr() & 0x40u) std::abort();
#endif
    reads.push_back(word);
    addresses.push_back(address);
}
void require(bool ok, const char *message) {
    if (!ok) { std::fprintf(stderr, "%s\n", message); std::exit(1); }
}
}

int main() {
    using ps2::vuops::KickPipe;
    word = 0x87654F; // Old vertex data would select ZBUF2 as an A+D address.
    {
        KickPipe immediate(0, capture);
        immediate.issue(10, 515);
        word = 0x43;
    }
    require(reads.size() == 1 && reads[0] == 0x87654F, "negative control must read stale data");
    reads.clear(); addresses.clear();
    word = 0x87654F;
#if defined(__SSE2__)
    const unsigned saved = _mm_getcsr();
    _mm_setcsr(saved | 0x40u);
#endif
    {
        KickPipe delayed(2, capture);
        delayed.issue(10, 515);
        delayed.advance(11);
        require(reads.empty(), "packet copied before following store");
        word = 0x43;
        delayed.advance(12);
        require(reads.size() == 1 && reads[0] == 0x43 && addresses[0] == 515,
                "packet must observe following store");
        word = 0x48;
        delayed.advance(13);
        require(reads.size() == 1 && reads[0] == 0x43, "later stores must not change a copied packet");
        delayed.issue(20, 516);
        delayed.issue(21, 517);
        require(reads.size() == 2 && addresses.back() == 516, "second kick must drain prior transfer");
    }
    require(reads.size() == 3 && addresses.back() == 517, "boundary must drain last transfer");
#if defined(__SSE2__)
    require((_mm_getcsr() & 0x40u) != 0, "caller floating point mode not restored");
    _mm_setcsr(saved);
#endif
    {
        KickPipe wrapped(2, capture);
        wrapped.issue(0xFFFFFFFEu, 518);
        wrapped.advance(0xFFFFFFFFu);
        require(reads.size() == 3, "cycle wrap fired early");
        wrapped.advance(0);
        require(reads.size() == 4 && addresses.back() == 518, "cycle wrap lost transfer");
    }
    std::puts("XGKICK delay, ordering, boundary, floating-point mode and negative control passed");
}
