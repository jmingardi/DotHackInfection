#include "ps2/generated.hpp"
#include <cstdio>
#include <cstring>

static void image_a(ps2::Cpu &cpu, std::uint32_t, std::uint32_t) { cpu.r[2].d[0] = 1; }
static void image_b(ps2::Cpu &cpu, std::uint32_t, std::uint32_t) { cpu.r[2].d[0] = 2; }

int main(int argc, char **) {
    const bool notify = argc == 1;
    constexpr std::uint32_t base = 0x400000;
    const std::uint16_t entries[] = {1, 0};
    const ps2::UnitInfo a[] = {{0, 8, image_a, entries}};
    const ps2::UnitInfo b[] = {{0, 8, image_b, entries}};
    const std::uint32_t guards_a[] = {0, 0x12345678, 4, 0x11111111};
    const std::uint32_t guards_b[] = {0, 0x12345678, 4, 0x22222222};
    const ps2::ModuleInfo modules[] = {
        {"a", base, 8, guards_a, 2, a, 1}, {"b", base, 8, guards_b, 2, b, 1}};
    ps2::register_units(a, 0);
    ps2::register_modules(modules, 2);
    ps2::Cpu cpu{};
    auto dispatch = [&] { cpu.pc = base; ps2::dispatch(cpu, 0, 0); return cpu.r[2].d[0]; };
    std::uint32_t words[] = {0x12345678, 0x11111111};
    std::memcpy(ps2::g_ram + base, words, 8);
    if (dispatch() != 1) return 1;
    words[1] = 0x22222222;
    std::memcpy(ps2::g_ram + base + 4, words + 1, 4);
    if (notify) ps2::watch_span(base + 4, 4, "test:overlay_dma");
    if (dispatch() != 2) { std::puts("FAIL: stale overlay after DMA"); return 1; }
    words[1] = 0x11111111;
    std::memcpy(ps2::g_ram + base + 4, words + 1, 4);
    if (notify) ps2::watch_span(0xA0000000u + base + 5, 3, "test:partial_alias_dma");
    if (dispatch() != 1) { std::puts("FAIL: stale overlay after aliased partial write"); return 1; }
    std::puts("overlay replacement: both directions and partial aliased guard writes passed");
}
