#include "jali/phonemes.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
namespace jali {
SpeechPose phoneme_pose(const std::string& symbol) {
    auto p=symbol;
    while(!p.empty() && (p.back()=='#' || (p.back()>='0' && p.back()<='9')))p.pop_back();
    if (p.empty() || p[0] == '_' || p == "pau") return {};
    if (p == "p" || p == "b" || p == "m") return {0.02f, 0, 1};
    if (p == "f" || p == "v") return {0.12f, 0, 0.65f};
    if (p == "w" || p == "u:" || p == "U" || p == "oU" || p == "O:" || p == "o:" || p == "@U")
        return {0.38f, 1, 0};
    if (p == "a" || p == "a:" || p == "A:" || p == "aI" || p == "aU" || p == "aa" || p == "V" || p == "Q")
        return {0.85f, 0, 0};
    if (p == "E" || p == "e" || p == "eI" || p == "e:" || p == "{" || p == "@" || p == "3:")
        return {0.55f, 0.1f, 0};
    if (p == "i:" || p == "I" || p == "i" || p == "j") return {0.3f, 0, 0};
    return {0.19f, 0.05f, 0}; // tongue/consonant approximation, explicit fallback
}
SpeechPose sample_phonemes(const std::vector<PhonemeCue>& cues, double time) {
    if (!std::isfinite(time) || time < 0) throw std::invalid_argument("invalid phoneme time");
    double previous = -1;
    for (const auto& cue : cues) {
        if (!std::isfinite(cue.seconds) || cue.seconds < 0 || cue.seconds < previous)
            throw std::invalid_argument("invalid phoneme timeline");
        previous = cue.seconds;
    }
    if (cues.empty() || time < cues.front().seconds) return {};
    const auto next = std::upper_bound(cues.begin(), cues.end(), time,
        [](double t, const PhonemeCue& cue) { return t < cue.seconds; });
    const auto& current = *(next-1);
    const auto pose = phoneme_pose(current.symbol);
    if (next == cues.end()) return pose;
    // Short bounded anticipation/coarticulation; preserves a full interval of lip closure.
    const auto blend_start = std::max(current.seconds, next->seconds - 0.035);
    const auto alpha = next->seconds > blend_start ? std::clamp((time-blend_start)/(next->seconds-blend_start),0.0,1.0) : 0;
    const auto other = phoneme_pose(next->symbol);
    return {float(pose.jaw*(1-alpha)+other.jaw*alpha), float(pose.round*(1-alpha)+other.round*alpha),
            float(pose.close*(1-alpha)+other.close*alpha)};
}
} // namespace jali
