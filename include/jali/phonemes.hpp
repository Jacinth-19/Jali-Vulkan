#pragma once
#include "jali/pipeline.hpp"
#include <array>
namespace jali {
struct PhonemeCue { double seconds = 0; std::string symbol; };
struct SpeechPose { float jaw = 0, round = 0, close = 0; };
// eSpeak mnemonic phonemes, not ARKit facial coefficients.
SpeechPose phoneme_pose(const std::string& symbol);
SpeechPose sample_phonemes(const std::vector<PhonemeCue>& cues, double seconds);
} // namespace jali
