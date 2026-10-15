#include "jali/pipeline.hpp"
#include <cmath>
#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {
int checks = 0;
void check(bool value, const char* label) {
    ++checks;
    if (!value) throw std::runtime_error(label);
}
void rejects(const std::function<void()>& function, const char* label) {
    try { function(); }
    catch (const std::invalid_argument&) { ++checks; return; }
    throw std::runtime_error(label);
}
}
int main() {
    try {
        const auto nan = std::numeric_limits<float>::quiet_NaN();
        jali::MockVoiceSource voice;
        jali::EnvelopeVisemeMapper mapper;
        auto rig = jali::make_fixture_rig();
        const auto audio = voice.synthesize({"one two three four five"});
        const auto again = voice.synthesize({"one two three four five"});
        check(audio.samples == again.samples, "mock must be deterministic");
        auto frames = mapper.map(audio);
        jali::HeadlessRenderer renderer;
        renderer.submit(rig, frames);
        check(renderer.frames().size() == frames.size(), "headless stores frames");
        const auto result = jali::analyze_sync(audio, frames, 0);
        check(result.passed && result.signed_lag_ms == 0, "aligned fixture");
        check(std::abs(result.audio_onset_seconds - 0.2) < 1e-9, "known audio onset");
        rejects([&] { voice.synthesize({""}); }, "empty text");
        rejects([&] { voice.synthesize({std::string(4097, 'x')}); }, "oversized text");
        rejects([&] { voice.synthesize({"hello", "real-person"}); }, "real voice rejected");
        auto bad_audio = audio;
        bad_audio.sample_rate = 0;
        rejects([&] { mapper.map(bad_audio); }, "bad sample rate");
        bad_audio = audio; bad_audio.samples[0] = nan;
        rejects([&] { mapper.map(bad_audio); }, "NaN audio");
        bad_audio.samples[0] = 2;
        rejects([&] { mapper.map(bad_audio); }, "unnormalized audio");
        bad_audio.samples.clear();
        rejects([&] { mapper.map(bad_audio); }, "empty audio");
        bad_audio = audio;
        for (auto& sample : bad_audio.samples) sample = 0;
        rejects([&] { jali::analyze_sync(bad_audio, mapper.map(bad_audio), 100); }, "silent audio");
        for (double shift : {-0.15, 0.15}) {
            auto shifted = frames;
            for (auto& frame : shifted) {
                // Shift activity within the fixed timeline rather than introducing negative times.
                const auto source = frame.audio_time_seconds - shift;
                frame.morph_weights[0] = source >= 0.2 && source < 0.35 ? 0.8f : 0;
            }
            check(!jali::analyze_sync(audio, shifted, 100).passed, "lead and lag must fail");
        }
        auto bad_rig = rig;
        bad_rig.bones[0].parent = 1;
        rejects([&] { jali::validate_rig(bad_rig); }, "cycle");
        bad_rig = rig; bad_rig.bones[1].parent = 99;
        rejects([&] { jali::validate_rig(bad_rig); }, "bad parent");
        bad_rig = rig; bad_rig.bones[1].parent = -2;
        rejects([&] { jali::validate_rig(bad_rig); }, "negative parent");
        bad_rig = rig; bad_rig.bones[1].name = "root";
        rejects([&] { jali::validate_rig(bad_rig); }, "duplicate bones");
        bad_rig = rig; bad_rig.vertices[0].influences[0].joint = 99;
        rejects([&] { jali::validate_rig(bad_rig); }, "invalid joint");
        bad_rig = rig; bad_rig.vertices[0].influences[0].weight = 0.5;
        rejects([&] { jali::validate_rig(bad_rig); }, "weight sum");
        bad_rig.vertices[0].influences[0].weight = -1;
        rejects([&] { jali::validate_rig(bad_rig); }, "negative skin weight");
        bad_rig.vertices[0].influences[0].weight = nan;
        rejects([&] { jali::validate_rig(bad_rig); }, "NaN skin weight");
        bad_rig = rig; bad_rig.vertices[0].x = nan;
        rejects([&] { jali::validate_rig(bad_rig); }, "NaN vertex");
        bad_rig = rig; bad_rig.vertices[0].influences.resize(5, {0, 0});
        rejects([&] { jali::validate_rig(bad_rig); }, "influence policy");
        bad_rig = rig; bad_rig.morph_channels[0].minimum = 2;
        rejects([&] { jali::validate_rig(bad_rig); }, "invalid range");
        auto bad_frames = frames;
        bad_frames[0].morph_weights[0] = nan;
        rejects([&] { renderer.submit(rig, bad_frames); }, "NaN morph");
        bad_frames = frames; bad_frames[0].morph_weights[0] = 2;
        rejects([&] { renderer.submit(rig, bad_frames); }, "morph range");
        bad_frames = frames; bad_frames[0].morph_weights.push_back(0);
        rejects([&] { renderer.submit(rig, bad_frames); }, "channel mismatch");
        bad_frames = frames; bad_frames[1].audio_time_seconds = 0;
        rejects([&] { renderer.submit(rig, bad_frames); }, "duplicate timestamp");
        bad_frames = frames; bad_frames[0].audio_time_seconds = -1;
        rejects([&] { renderer.submit(rig, bad_frames); }, "negative timestamp");
        bad_frames = frames; bad_frames[0].audio_time_seconds = nan;
        rejects([&] { renderer.submit(rig, bad_frames); }, "NaN timestamp");
        rejects([&] { renderer.submit(rig, {}); }, "empty timeline");
        bad_frames = frames; bad_frames.back().audio_time_seconds = 99;
        rejects([&] { jali::analyze_sync(audio, bad_frames, 100); }, "out of duration");
        rejects([&] { jali::analyze_sync(audio, frames, -1); }, "negative tolerance");
        rejects([&] { jali::analyze_sync(audio, frames, nan); }, "NaN tolerance");
        // Ranges belong to the rig: negative corrective shapes are not globally invalid.
        rig.morph_channels[0].minimum = -1;
        frames[0].morph_weights[0] = -0.5;
        renderer.submit(rig, frames);
        check(renderer.frames()[0].morph_weights[0] == -0.5f, "rig-specific corrective range");
        std::cout << checks << " contract checks passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "test failure: " << error.what() << '\n';
        return 1;
    }
}
