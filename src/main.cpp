#include "jali/pipeline.hpp"
#ifdef JALI_HAS_ESPEAK
#include "jali/espeak_voice.hpp"
#endif
#ifdef JALI_HAS_VULKAN
#include "jali/vulkan_renderer.hpp"
#endif
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>

namespace {
std::uint32_t number(const std::string& value) {
    if (value.empty() || value.find_first_not_of("0123456789") != std::string::npos)
        throw std::invalid_argument("expected an unsigned integer");
    const auto n = std::stoul(value);
    if (n > 2048) throw std::invalid_argument("numeric option exceeds limit");
    return static_cast<std::uint32_t>(n);
}
}
int main(int argc, char** argv) {
    try {
        std::filesystem::path output = "artifacts/demo";
        jali::VoiceRequest request{"one two three four five"};
        std::string voice_kind = "mock", renderer_kind = "headless";
        std::uint32_t size = 512, fps = 24;
#ifdef JALI_HAS_VULKAN
        std::filesystem::path shader = JALI_DEFAULT_FACE_SHADER;
#else
        std::filesystem::path shader;
#endif
        for (int i = 1; i < argc; ++i) {
            const std::string flag = argv[i];
            if (flag == "--help") {
                std::cout << "jali_demo [--output DIRECTORY] [--text TEXT]\n"
                          << "          [--voice mock|espeak] [--renderer headless|vulkan]\n"
                          << "          [--size 32..2048] [--fps 1..60] [--shader FILE]\n"
                          << "eSpeak is a built-in synthetic voice, not voice cloning.\n"
                          << "Vulkan renders a procedural 3D face, not an imported skinned rig.\n";
                return 0;
            }
            if (flag != "--output" && flag != "--text" && flag != "--voice" && flag != "--renderer" &&
                flag != "--size" && flag != "--fps" && flag != "--shader")
                throw std::invalid_argument("unknown option: " + flag);
            if (i + 1 >= argc) throw std::invalid_argument("missing value: " + flag);
            const std::string value = argv[++i];
            if (flag == "--output") output = value;
            else if (flag == "--text") request.text = value;
            else if (flag == "--voice") voice_kind = value;
            else if (flag == "--renderer") renderer_kind = value;
            else if (flag == "--size") size = number(value);
            else if (flag == "--fps") fps = number(value);
            else if (flag == "--shader") shader = value;
        }
        if (size < 32 || fps < 1 || fps > 60) throw std::invalid_argument("invalid size or FPS");
        std::unique_ptr<jali::IVoiceSource> voice;
        if (voice_kind == "mock") voice = std::make_unique<jali::MockVoiceSource>();
        else if (voice_kind == "espeak") {
#ifdef JALI_HAS_ESPEAK
            request.voice_id = "espeak-en";
            const auto* data = std::getenv("JALI_ESPEAK_DATA");
            voice = std::make_unique<jali::EspeakVoiceSource>(data ? data : "");
#else
            throw std::runtime_error("eSpeak backend was not built; configure with JALI_ENABLE_ESPEAK=ON");
#endif
        } else throw std::invalid_argument("unknown voice backend");
        if (renderer_kind != "headless" && renderer_kind != "vulkan")
            throw std::invalid_argument("unknown renderer backend");
        jali::EnvelopeVisemeMapper mapper;
        const auto audio = voice->synthesize(request);
        const auto frames = mapper.map(audio);
        const auto metrics = jali::analyze_sync(audio, frames, 100);
        jali::write_artifacts(output, audio, frames, metrics, voice_kind == "mock");
        const auto duration = double(audio.samples.size()) / audio.sample_rate;
        std::string device = "none";
        std::uint32_t frame_count = 0;
        if (renderer_kind == "vulkan") {
#ifdef JALI_HAS_VULKAN
            jali::VulkanFaceRenderer renderer(size, size, shader);
            renderer.submit(jali::make_fixture_rig(), frames);
            device = renderer.device_name();
            std::cout << "Vulkan device: " << device << "\nRendering " << duration << " seconds...\n" << std::flush;
            frame_count = renderer.write_sequence(output / "frames.rgba", duration, fps);
#else
            throw std::runtime_error("Vulkan backend was not built; configure with JALI_ENABLE_VULKAN=ON");
#endif
        } else {
            jali::HeadlessRenderer renderer;
            renderer.submit(jali::make_fixture_rig(), frames);
        }
        std::ofstream session(output / "session.json");
        session << "{\n  \"voice\": " << std::quoted(voice_kind)
                << ",\n  \"renderer\": " << std::quoted(renderer_kind)
                << ",\n  \"device\": " << std::quoted(device)
                << ",\n  \"width\": " << size << ",\n  \"height\": " << size
                << ",\n  \"fps\": " << fps << ",\n  \"frame_count\": " << frame_count
                << ",\n  \"duration_seconds\": " << std::setprecision(12) << duration << "\n}\n";
        session.flush();
        if (!session) throw std::runtime_error("cannot write session metadata");
        std::cout << "Curve onset sync " << (metrics.passed ? "PASS" : "FAIL")
                  << ": signed onset lag " << metrics.signed_lag_ms << " ms\n"
                  << "Artifacts: " << output.string() << "\n";
        return metrics.passed ? 0 : 1;
    } catch (const std::exception& error) {
        std::cerr << "jali_demo: " << error.what() << '\n';
        return 2;
    }
}
