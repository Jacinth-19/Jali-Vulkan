#include "jali/pipeline.hpp"
#ifdef JALI_HAS_ESPEAK
#include "jali/espeak_voice.hpp"
#endif
#ifdef JALI_HAS_VULKAN
#include "jali/vulkan_renderer.hpp"
#endif
#include <cmath>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>

void expect(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
void rejects(const std::function<void()>& run) {
    try { run(); } catch (const std::invalid_argument&) { return; }
    throw std::runtime_error("invalid backend input was accepted");
}
int main() {
    try {
#ifdef JALI_HAS_ESPEAK
        const auto* data = std::getenv("JALI_ESPEAK_DATA");
        jali::EspeakVoiceSource speech(data ? data : "");
        rejects([&] { speech.synthesize({"hello", "unauthorized-person"}); });
        rejects([&] { speech.synthesize({"", "espeak-en"}); });
        rejects([&] { speech.synthesize({"   ", "espeak-en"}); });
        rejects([&] { speech.synthesize({std::string("a\0b", 3), "espeak-en"}); });
        auto audio = speech.synthesize({"Welcome to Jali. This is real synthesized speech.", "espeak-en"});
        expect(audio.samples.size() > audio.sample_rate, "speech unexpectedly shorter than one second");
        double energy = 0;
        for (auto sample : audio.samples) energy += sample * sample;
        expect(energy > 1, "speech PCM is silent");
        expect(!speech.phonemes().empty(), "phoneme event capture is empty");
        expect(jali::phoneme_pose("m").close==1 && jali::phoneme_pose("u:").round==1 && jali::phoneme_pose("a").jaw>0.7f,"distinct viseme classes");
        auto second = speech.synthesize({"Hello again.", "espeak-en"});
        expect(!second.samples.empty(), "second synthesis failed");
        std::cout << "eSpeak PCM: " << audio.samples.size() << " samples at " << audio.sample_rate << " Hz\n";
#endif
#ifdef JALI_HAS_VULKAN
        jali::VulkanFaceRenderer renderer(96, 96, JALI_DEFAULT_FACE_SHADER);
        rejects([&] { renderer.render(0); });
        auto rig = jali::make_fixture_rig();
        renderer.submit(rig, {{0, {0}}, {1, {1}}});
        const auto closed = renderer.render(0);
        const auto open = renderer.render(1);
        const auto middle = renderer.render(0.5);
        expect(closed.size() == 96 * 96 * 4, "invalid readback size");
        std::size_t changed = 0;
        for (std::size_t i = 0; i < closed.size(); i += 4) {
            expect(closed[i+3] == 255 && open[i+3] == 255, "shader failed to write alpha");
            if (closed[i] != open[i] || closed[i+1] != open[i+1] || closed[i+2] != open[i+2]) ++changed;
        }
        expect(changed > 10, "jawOpen did not change rendered pixels");
        expect(middle != closed && middle != open, "timeline interpolation did not change the image");
        expect(renderer.render(0) == closed, "same pose render is nondeterministic");
        rejects([&] { renderer.render(-1); });
        rejects([&] { renderer.render(std::numeric_limits<double>::quiet_NaN()); });
        rig.morph_channels[0].name = "wrong";
        rejects([&] { renderer.submit(rig, {{0, {0}}}); });
        const auto character = jali::load_character_glb(JALI_DEFAULT_CHARACTER);
        renderer.load_character(JALI_DEFAULT_CHARACTER);
        expect(character.joints.size()==2 && character.vertices.size()>1000,"real imported GLB skin");
        auto neutral = renderer.render_pose({});
        auto rounded = renderer.render_pose({0.4f,1,0});
        auto closed_lips = renderer.render_pose({0.02f,0,1});
        expect(neutral!=rounded && rounded!=closed_lips,"distinct rendered visemes");
        for (const auto pose : {jali::SpeechPose{}, jali::SpeechPose{0.8f,0.5f,0}, jali::SpeechPose{0.1f,0,1}}) {
            renderer.render_pose(pose);
            const auto gpu=renderer.deformed_positions();const auto cpu=jali::deform_reference(character,pose);
            expect(gpu.size()==cpu.size(),"deformation readback count");
            for(std::size_t i=0;i<gpu.size();++i)for(int k=0;k<3;++k)
                expect(std::isfinite(gpu[i][k]) && std::abs(gpu[i][k]-cpu[i][k])<2e-5,"GPU/CPU morph-then-skin mismatch");
        }
        rejects([&] { renderer.render_pose({2,0,0}); });
        if(!renderer.hardware_accelerated()) {
            bool failed=false;try { jali::VulkanFaceRenderer required(96,96,JALI_DEFAULT_FACE_SHADER,true); } catch(const std::runtime_error&) {failed=true;}
            expect(failed,"hardware-required mode silently accepted a software driver");
        }
        std::cout << "Imported " << character.vertices.size() << " vertices: CPU/GPU skin + 3 morphs agree\n";
        std::cout << "Vulkan readback: " << renderer.device_name() << "; jaw changed " << changed << " pixels\n";
#endif
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "backend test: " << error.what() << '\n';
        return 1;
    }
}
