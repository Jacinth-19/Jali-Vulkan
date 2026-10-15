#include "jali/pipeline.hpp"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <limits>
#include <set>
#include <stdexcept>

namespace jali {
namespace {
void require(bool condition, const char* message) {
    if (!condition) throw std::invalid_argument(message);
}
std::size_t window_size(const AudioBuffer& audio) {
    return std::max<std::size_t>(1, audio.sample_rate / 100); // ~10 ms
}
double rms(const AudioBuffer& audio, std::size_t start, std::size_t count) {
    double energy = 0;
    const auto end = std::min(audio.samples.size(), start + count);
    for (auto i = start; i < end; ++i) energy += double(audio.samples[i]) * audio.samples[i];
    return std::sqrt(energy / double(end - start));
}
void validate_timeline(const std::vector<FaceFrame>& frames) {
    require(!frames.empty(), "empty face timeline");
    double previous = -1;
    for (const auto& frame : frames) {
        require(std::isfinite(frame.audio_time_seconds) && frame.audio_time_seconds >= 0 &&
                frame.audio_time_seconds > previous, "invalid or unordered timestamp");
        require(!frame.morph_weights.empty(), "missing jaw channel");
        for (auto value : frame.morph_weights)
            require(std::isfinite(value), "non-finite morph weight");
        previous = frame.audio_time_seconds;
    }
}
void little_endian(std::ostream& out, std::uint32_t value, unsigned bytes) {
    for (unsigned i = 0; i < bytes; ++i) out.put(static_cast<char>((value >> (i * 8)) & 0xff));
}
} // namespace

void validate_audio(const AudioBuffer& audio) {
    require(audio.sample_rate >= 100 && audio.sample_rate <= 192000, "unsupported sample rate");
    require(!audio.samples.empty(), "empty audio");
    for (auto sample : audio.samples)
        require(std::isfinite(sample) && sample >= -1 && sample <= 1, "invalid normalized PCM");
}
void validate_rig(const Rig& rig) {
    require(!rig.bones.empty() && !rig.vertices.empty(), "rig needs bones and vertices");
    std::set<std::string> names;
    for (std::size_t i = 0; i < rig.bones.size(); ++i) {
        const auto& bone = rig.bones[i];
        require(!bone.name.empty() && names.insert(bone.name).second, "invalid/duplicate bone name");
        require(bone.parent >= -1 && (bone.parent == -1 ||
                static_cast<std::size_t>(bone.parent) < rig.bones.size()), "invalid bone parent");
        auto parent = static_cast<int>(i);
        std::size_t steps = 0;
        while (parent != -1) {
            require(++steps <= rig.bones.size(), "cyclic bone hierarchy");
            // Check each link before following it, even if that bone has not been visited yet.
            const auto next = rig.bones[static_cast<std::size_t>(parent)].parent;
            require(next >= -1 && (next == -1 || static_cast<std::size_t>(next) < rig.bones.size()),
                    "invalid bone parent");
            parent = next;
        }
    }
    for (const auto& vertex : rig.vertices) {
        require(std::isfinite(vertex.x) && std::isfinite(vertex.y) && std::isfinite(vertex.z),
                "non-finite vertex");
        // Starter engine policy, NOT a glTF format limit.
        require(!vertex.influences.empty() && vertex.influences.size() <= 4,
                "starter supports 1-4 joint influences");
        double total = 0;
        for (const auto& influence : vertex.influences) {
            require(influence.joint < rig.bones.size(), "invalid joint index");
            require(std::isfinite(influence.weight) && influence.weight >= 0 && influence.weight <= 1,
                    "invalid skin weight");
            total += influence.weight;
        }
        require(std::abs(total - 1) <= 1e-4, "skin weights must sum to one");
    }
    require(!rig.morph_channels.empty(), "missing morph channels");
    names.clear();
    for (const auto& channel : rig.morph_channels) {
        require(!channel.name.empty() && names.insert(channel.name).second, "invalid/duplicate morph name");
        require(std::isfinite(channel.minimum) && std::isfinite(channel.maximum) &&
                channel.minimum <= channel.maximum, "invalid morph range");
    }
}
void validate_frames(const Rig& rig, const std::vector<FaceFrame>& frames) {
    validate_rig(rig);
    validate_timeline(frames);
    for (const auto& frame : frames) {
        require(frame.morph_weights.size() == rig.morph_channels.size(), "morph channel count mismatch");
        for (std::size_t i = 0; i < frame.morph_weights.size(); ++i)
            require(frame.morph_weights[i] >= rig.morph_channels[i].minimum &&
                    frame.morph_weights[i] <= rig.morph_channels[i].maximum, "morph weight out of range");
    }
}
Rig make_fixture_rig() {
    return {{{"root", -1}, {"jaw", 0}},
            {{-0.5f, 0, 0, {{0, 1}}}, {0.5f, 0, 0, {{0, 0.5f}, {1, 0.5f}}},
             {0, 1, 0, {{1, 1}}}}, {{"jawOpen", 0, 1}}};
}
AudioBuffer MockVoiceSource::synthesize(const VoiceRequest& request) {
    require(request.voice_id == "synthetic-fixture", "mock does not clone real voices");
    require(!request.text.empty() && request.text.size() <= 4096, "text must contain 1-4096 bytes");
    const auto words = std::min<std::size_t>(8, 1 + std::count(request.text.begin(), request.text.end(), ' '));
    AudioBuffer audio;
    const auto lead = audio.sample_rate / 5;
    const auto segment = audio.sample_rate / 4;
    const auto active = audio.sample_rate / 6;
    audio.samples.resize(lead * 2 + words * segment, 0);
    constexpr double pi = 3.14159265358979323846;
    for (std::size_t word = 0; word < words; ++word)
        for (std::size_t i = 0; i < active; ++i)
            audio.samples[lead + word * segment + i] =
                static_cast<float>(0.4 * std::sin(2 * pi * (220 + word * 30) * i / audio.sample_rate));
    return audio; // Synthetic tones, NOT intelligible speech.
}
std::vector<FaceFrame> EnvelopeVisemeMapper::map(const AudioBuffer& audio) {
    validate_audio(audio);
    std::vector<FaceFrame> frames;
    const auto window = window_size(audio);
    for (std::size_t start = 0; start < audio.samples.size(); start += window)
        frames.push_back({double(start) / audio.sample_rate,
                          {static_cast<float>(std::clamp(rms(audio, start, window) * 3, 0.0, 1.0))}});
    return frames;
}
void HeadlessRenderer::submit(const Rig& rig, const std::vector<FaceFrame>& frames) {
    validate_frames(rig, frames);
    frames_ = frames;
}
SyncMetrics analyze_sync(const AudioBuffer& audio, const std::vector<FaceFrame>& frames,
                         double max_lag_ms) {
    validate_audio(audio);
    validate_timeline(frames);
    require(std::isfinite(max_lag_ms) && max_lag_ms >= 0, "invalid lag tolerance");
    SyncMetrics result;
    bool found_audio = false, found_face = false;
    const auto window = window_size(audio);
    for (std::size_t start = 0; start < audio.samples.size(); start += window) {
        if (rms(audio, start, window) > 0.05) {
            result.audio_onset_seconds = double(start) / audio.sample_rate;
            found_audio = true;
            break;
        }
    }
    for (const auto& frame : frames) {
        require(frame.audio_time_seconds < double(audio.samples.size()) / audio.sample_rate,
                "face frame outside audio duration");
        require(frame.morph_weights[0] >= 0 && frame.morph_weights[0] <= 1, "invalid jaw weight");
        if (!found_face && frame.morph_weights[0] > 0.1) {
            result.face_onset_seconds = frame.audio_time_seconds;
            found_face = true;
        }
    }
    require(found_audio && found_face, "inconclusive sync: missing audio or mouth activity");
    result.signed_lag_ms = (result.face_onset_seconds - result.audio_onset_seconds) * 1000;
    result.passed = std::abs(result.signed_lag_ms) <= max_lag_ms + 1e-9;
    return result;
}
void write_pcm_wav(const std::filesystem::path& path, const AudioBuffer& audio) {
    validate_audio(audio);
    require(audio.samples.size() <= (std::numeric_limits<std::uint32_t>::max() - 36) / 2,
            "audio exceeds WAV size limit");
    if (!path.parent_path().empty()) std::filesystem::create_directories(path.parent_path());
    std::ofstream wav(path, std::ios::binary);
    if (!wav) throw std::runtime_error("cannot create WAV");
    const auto bytes = static_cast<std::uint32_t>(audio.samples.size() * 2);
    wav.write("RIFF", 4); little_endian(wav, bytes + 36, 4); wav.write("WAVEfmt ", 8);
    little_endian(wav, 16, 4); little_endian(wav, 1, 2); little_endian(wav, 1, 2);
    little_endian(wav, audio.sample_rate, 4); little_endian(wav, audio.sample_rate * 2, 4);
    little_endian(wav, 2, 2); little_endian(wav, 16, 2); wav.write("data", 4);
    little_endian(wav, bytes, 4);
    for (auto sample : audio.samples) {
        const auto pcm = static_cast<std::int16_t>(std::lround(sample * 32767));
        little_endian(wav, static_cast<std::uint16_t>(pcm), 2);
    }
    wav.flush();
    if (!wav) throw std::runtime_error("WAV write failed");
}
void write_artifacts(const std::filesystem::path& directory, const AudioBuffer& audio,
                     const std::vector<FaceFrame>& frames, const SyncMetrics& metrics, bool fixture_only) {
    validate_audio(audio);
    validate_timeline(frames);
    require(audio.samples.size() <= (std::numeric_limits<std::uint32_t>::max() - 36) / 2,
            "audio exceeds WAV size limit");
    std::filesystem::create_directories(directory);
    write_pcm_wav(directory / "session.wav", audio);
    std::ofstream csv(directory / "face.csv");
    std::ofstream json(directory / "metrics.json");
    if (!csv || !json) throw std::runtime_error("cannot create artifacts");
    csv << "audio_time_seconds,jaw_open\n" << std::setprecision(12);
    for (const auto& frame : frames) csv << frame.audio_time_seconds << ',' << frame.morph_weights[0] << '\n';
    json << std::setprecision(12) << "{\n  \"fixture_only\": "
         << (fixture_only ? "true" : "false") << ",\n  \"audio_onset_seconds\": "
         << metrics.audio_onset_seconds << ",\n  \"face_onset_seconds\": " << metrics.face_onset_seconds
         << ",\n  \"signed_lag_ms\": " << metrics.signed_lag_ms
         << ",\n  \"passed\": " << (metrics.passed ? "true" : "false") << "\n}\n";
    csv.flush(); json.flush();
    if (!csv || !json) throw std::runtime_error("artifact write failed");
}
} // namespace jali
