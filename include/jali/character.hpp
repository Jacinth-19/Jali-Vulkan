#pragma once
#include "jali/phonemes.hpp"
#include <array>
#include <cstddef>
namespace jali {
inline constexpr std::size_t kMaxCharacterJoints = 128;
inline constexpr std::size_t kMaxCharacterNodes = 256;
using Mat4 = std::array<float,16>;
struct MeshVertex {
    std::array<float,3> position{}, normal{}, color{};
    std::array<std::uint32_t,4> joints{};
    std::array<float,4> weights{};
    std::array<float,3> jaw_delta{}, round_delta{}, close_delta{};
};
static_assert(sizeof(MeshVertex)==104, "skin shader input ABI");
struct CharacterJoint { std::string name; int parent=-1; Mat4 local{}, inverse_bind{}; };
struct Character {
    std::vector<MeshVertex> vertices;
    std::vector<std::uint32_t> indices;
    std::vector<CharacterJoint> joints;
    int jaw_joint=-1;
};
Mat4 identity_matrix();
Mat4 multiply(const Mat4& a, const Mat4& b);
Character load_character_glb(const std::filesystem::path& path);
using JointPalette = std::array<Mat4,kMaxCharacterJoints>;
JointPalette character_palette(const Character& character, SpeechPose pose);
std::vector<std::array<float,3>> deform_reference(const Character& character, SpeechPose pose);
} // namespace jali
