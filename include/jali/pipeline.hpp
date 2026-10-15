#pragma once

#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

namespace jali {
// Mono normalized PCM. All timestamps use the audio playback clock, in seconds.
struct AudioBuffer {
    std::uint32_t sample_rate = 24000;
    std::vector<float> samples;
};
struct VoiceRequest {
    std::string text;
    // Only "synthetic-fixture" is accepted by MockVoiceSource. No real identity.
    std::string voice_id = "synthetic-fixture";
};
class IVoiceSource {
public:
    virtual ~IVoiceSource() = default;
    virtual AudioBuffer synthesize(const VoiceRequest& request) = 0;
};
struct FaceFrame {
    double audio_time_seconds = 0;
    std::vector<float> morph_weights;
};
class IVisemeMapper {
public:
    virtual ~IVisemeMapper() = default;
    virtual std::vector<FaceFrame> map(const AudioBuffer& audio) = 0;
};
struct Bone {
    std::string name;
    int parent = -1;
};
struct Influence {
    std::uint32_t joint = 0;
    float weight = 0;
};
struct Vertex {
    float x = 0, y = 0, z = 0;
    std::vector<Influence> influences;
};
struct MorphChannel {
    std::string name;
    float minimum = 0, maximum = 1;
};
struct Rig {
    std::vector<Bone> bones;
    std::vector<Vertex> vertices;
    std::vector<MorphChannel> morph_channels;
};
void validate_audio(const AudioBuffer& audio);
void validate_rig(const Rig& rig);
void validate_frames(const Rig& rig, const std::vector<FaceFrame>& frames);
Rig make_fixture_rig();

class MockVoiceSource final : public IVoiceSource {
public:
    AudioBuffer synthesize(const VoiceRequest& request) override;
};
// RMS envelope -> one jawOpen channel. Not a phoneme recognizer or neural mapper.
class EnvelopeVisemeMapper final : public IVisemeMapper {
public:
    std::vector<FaceFrame> map(const AudioBuffer& audio) override;
};
class IRenderer {
public:
    virtual ~IRenderer() = default;
    // Synchronous single-threaded contract; no hidden ownership or GPU work.
    virtual void submit(const Rig& rig, const std::vector<FaceFrame>& frames) = 0;
};
class HeadlessRenderer final : public IRenderer {
public:
    void submit(const Rig& rig, const std::vector<FaceFrame>& frames) override;
    const std::vector<FaceFrame>& frames() const { return frames_; }
private:
    std::vector<FaceFrame> frames_;
};
struct SyncMetrics {
    double audio_onset_seconds = 0;
    double face_onset_seconds = 0;
    double signed_lag_ms = 0; // positive = face lags audio
    bool passed = false;
};
// Missing signal is an error, never an automatic pass. Gates both lead and lag.
SyncMetrics analyze_sync(const AudioBuffer& audio,
                         const std::vector<FaceFrame>& frames, double max_lag_ms);
void write_pcm_wav(const std::filesystem::path& path, const AudioBuffer& audio);
void write_artifacts(const std::filesystem::path& directory, const AudioBuffer& audio,
                     const std::vector<FaceFrame>& frames, const SyncMetrics& metrics,
                     bool fixture_only = true);
} // namespace jali
