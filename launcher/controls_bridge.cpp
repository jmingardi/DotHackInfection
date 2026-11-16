// Reuse the pinned runtime's MIT keymap implementation, not a second parser.
#include "keymap.hpp"
#include <SDL.h>
#include <string>
#include <vector>

namespace {
std::string result, error;
keymap::Config parse(const char* text) {
    auto config = keymap::defaults();
    std::vector<std::string> problems;
    keymap::parse(text ? text : "", config, problems);
    return config;
}
}
#define API extern "C" __declspec(dllexport)
API const char* dh_error() { return error.c_str(); }
API const char* dh_defaults() { result = keymap::default_file_text(); return result.c_str(); }
API const char* dh_validate(const char* text) {
    auto config = keymap::defaults();
    std::vector<std::string> problems;
    keymap::parse(text ? text : "", config, problems);
    result.clear();
    for (const auto& p : problems) result += p + "\n";
    return result.c_str();
}
API const char* dh_values(const char* text) {
    auto config = parse(text);
    result.clear();
    for (int a = 0; a < keymap::ActionCount; ++a)
        result += std::to_string(a) + "\t" + keymap::keys_text(config, a) + "\n";
    result += "look\t" + std::to_string(config.look >= 0 ? config.look : keymap::kDefaultLook) + "\n";
    result += "scale\t" + std::to_string(config.scale > 0 ? config.scale : 1) + "\n";
    result += "sharp\t" + std::to_string(config.sharp_2d >= 0 ? config.sharp_2d : 1) + "\n";
    return result.c_str();
}
API const char* dh_bind(const char* text, int action, int input) {
    error.clear();
    if (action < 0 || action >= keymap::ActionCount) { error = "Unknown controller button."; return nullptr; }
    auto config = parse(text);
    std::vector<int> changed;
    if (!keymap::assign_input(config, action, input, changed, error)) return nullptr;
    result = text;
    for (int a : changed) result = keymap::with_inputs(result, a, config.inputs[a]);
    return result.c_str();
}
API const char* dh_set_binding(const char* text, int action, const char* value) {
    error.clear();
    if (action < 0 || action >= keymap::ActionCount) { error = "Unknown controller button."; return nullptr; }
    auto config = keymap::defaults();
    std::vector<std::string> problems;
    keymap::parse(std::string(keymap::action_name(action)) + " = " + (value ? value : "none"), config, problems);
    if (!problems.empty()) { error = problems.front(); return nullptr; }
    result = keymap::with_inputs(text, action, config.inputs[action]);
    return result.c_str();
}
API const char* dh_options(const char* text, int look, int scale, int sharp) {
    result = keymap::with_sharp_2d(keymap::with_scale(keymap::with_look(text, look), scale), sharp);
    return result.c_str();
}
API const char* dh_reset(const char* text) {
    auto config = parse(text);
    std::vector<int> changed;
    keymap::restore_default_inputs(config, changed);
    result = text;
    for (int a : changed) result = keymap::with_inputs(result, a, config.inputs[a]);
    return result.c_str();
}
