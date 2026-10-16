#pragma once
#include "jali/pipeline.hpp"
#include "jali/character.hpp"
#include <memory>

namespace jali {
// Optional offscreen native Vulkan compute renderer of a procedural 3D android face.
// Also supports imported GLB meshes through a compute morph/skin pass + rasterization.
class VulkanFaceRenderer final : public IRenderer {
public:
    VulkanFaceRenderer(std::uint32_t width, std::uint32_t height,
                       const std::filesystem::path& shader, bool require_hardware = false);
    ~VulkanFaceRenderer() override;
    VulkanFaceRenderer(const VulkanFaceRenderer&) = delete;
    VulkanFaceRenderer& operator=(const VulkanFaceRenderer&) = delete;
    void submit(const Rig& rig, const std::vector<FaceFrame>& frames) override;
    std::vector<std::uint8_t> render(double audio_time_seconds);
    std::uint32_t write_sequence(const std::filesystem::path& raw_output,
                                 double duration_seconds, std::uint32_t fps);
    std::string device_name() const;
    bool hardware_accelerated() const;
    void load_character(const std::filesystem::path& glb);
    std::vector<std::uint8_t> render_pose(SpeechPose pose);
    std::vector<std::uint8_t> render_named_pose(const MorphWeights& weights,BoneMotion motion={});
    std::vector<std::array<float,3>> deformed_normals() const;
    std::vector<std::array<float,3>> deformed_positions() const;
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
    std::vector<FaceFrame> frames_;
};
} // namespace jali
