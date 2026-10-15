#include "jali/espeak_voice.hpp"
#include <espeak-ng/speak_lib.h>
#include <algorithm>
#include <exception>
#include <mutex>
#include <stdexcept>
#include <utility>
#include <cstring>

namespace jali {
namespace {
std::mutex engine_mutex;
// Synchronous mode invokes this callback on the synthesizing thread.
thread_local AudioBuffer* destination = nullptr;
thread_local std::exception_ptr callback_error;
thread_local std::vector<PhonemeCue>* cue_destination = nullptr;
int collect(short* pcm, int count, espeak_EVENT* events) noexcept {
    try {
        if (events && cue_destination) for (auto* event = events; event->type != espeakEVENT_LIST_TERMINATED; ++event) {
            if (event->type == espeakEVENT_PHONEME) {
                const auto length = std::find(event->id.string, event->id.string + 8, '\0') - event->id.string;
                cue_destination->push_back({event->audio_position / 1000.0, std::string(event->id.string, static_cast<std::size_t>(length))});
            }
        }
        if (!pcm || count <= 0 || !destination) return 0;
        // Bound output to 60 seconds even if a malformed input causes excessive synthesis.
        if (destination->samples.size() + static_cast<std::size_t>(count) > destination->sample_rate * 60u)
            throw std::runtime_error("speech exceeded 60 second limit");
        for (int i = 0; i < count; ++i) destination->samples.push_back(pcm[i] / 32768.0f);
        return 0;
    } catch (...) {
        callback_error = std::current_exception();
        return 1;
    }
}
struct Shutdown {
    ~Shutdown() { espeak_Terminate(); destination = nullptr; cue_destination = nullptr; }
};
}
EspeakVoiceSource::EspeakVoiceSource(std::filesystem::path data_directory)
    : data_directory_(std::move(data_directory)) {}

AudioBuffer EspeakVoiceSource::synthesize(const VoiceRequest& request) {
    if (request.voice_id != "espeak-en") throw std::invalid_argument("only the built-in espeak-en voice is supported");
    if (request.text.empty() || request.text.size() > 500 || request.text.find('\0') != std::string::npos ||
        std::all_of(request.text.begin(), request.text.end(), [](unsigned char c) { return c <= ' '; }))
        throw std::invalid_argument("speech text must contain 1-500 bytes of nonblank text, without NUL");
    std::lock_guard<std::mutex> lock(engine_mutex);
    const auto path = data_directory_.string();
    // 0x8000 prevents the engine from exiting the process if data is missing.
    const auto rate = espeak_Initialize(AUDIO_OUTPUT_SYNCHRONOUS, 0,
                                       path.empty() ? nullptr : path.c_str(), 0x8001);
    if (rate <= 0) throw std::runtime_error("eSpeak initialization failed; check JALI_ESPEAK_DATA");
    Shutdown shutdown;
    AudioBuffer audio;
    audio.sample_rate = static_cast<std::uint32_t>(rate);
    audio.samples.reserve(audio.sample_rate * 15u);
    destination = &audio;
    phonemes_.clear();
    cue_destination = &phonemes_;
    callback_error = nullptr;
    espeak_SetSynthCallback(collect);
    if (espeak_SetVoiceByName("en-us") != EE_OK || espeak_SetParameter(espeakRATE, 155, 0) != EE_OK)
        throw std::runtime_error("eSpeak built-in English voice is unavailable");
    const auto status = espeak_Synth(request.text.c_str(), request.text.size() + 1, 0,
                                     POS_CHARACTER, 0, espeakCHARS_UTF8 | espeakENDPAUSE,
                                     nullptr, nullptr);
    if (callback_error) std::rethrow_exception(callback_error);
    if (status != EE_OK) throw std::runtime_error("eSpeak synthesis failed");
    validate_audio(audio);
    if (phonemes_.empty()) throw std::runtime_error("eSpeak returned no phoneme timing events");
    std::stable_sort(phonemes_.begin(), phonemes_.end(), [](const auto& a, const auto& b) { return a.seconds < b.seconds; });
    const auto duration=double(audio.samples.size()) / audio.sample_rate;
    for(auto& cue:phonemes_)cue.seconds=std::min(cue.seconds,duration);
    phonemes_.push_back({duration, "_"});
    return audio;
}
} // namespace jali
