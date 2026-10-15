#pragma once
#include "jali/pipeline.hpp"
#include "jali/phonemes.hpp"

namespace jali {
// Optional eSpeak NG backend. Uses a built-in synthetic voice, never a cloned identity.
// eSpeak is process-global; calls are serialized internally.
class EspeakVoiceSource final : public IVoiceSource {
public:
    explicit EspeakVoiceSource(std::filesystem::path data_directory = {});
    AudioBuffer synthesize(const VoiceRequest& request) override;
    const std::vector<PhonemeCue>& phonemes() const { return phonemes_; }
private:
    std::vector<PhonemeCue> phonemes_;
    std::filesystem::path data_directory_;
};
} // namespace jali
