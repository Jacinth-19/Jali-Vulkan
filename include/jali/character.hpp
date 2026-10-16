#pragma once
#include "jali/phonemes.hpp"
#include <array>
#include <cstddef>
#include <map>
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
inline constexpr std::size_t kMaxCharacterMorphs = 80;
struct MorphDelta { std::array<float,3> position{}, normal{}; };
struct MeshSurface { std::array<float,2> uv{}; std::array<float,4> factor{1,1,1,1}, material{0,1,.5f,-1}; float normal_scale=0; };
static_assert(sizeof(MorphDelta)==24 && sizeof(MeshSurface)==44,"rich shader ABI");
struct MeshRange { std::uint32_t first=0,count=0; bool blend=false; float depth=0; };
struct BoneMotion { float head_yaw=0,head_roll=0,eye_yaw=0,eye_pitch=0; };
using MorphWeights = std::map<std::string,float>;
struct DeformedMesh { std::vector<std::array<float,3>> positions,normals; };
struct Character {
    std::vector<MeshVertex> vertices;
    std::vector<std::uint32_t> indices;
    std::vector<CharacterJoint> joints;
    int jaw_joint=-1;
    std::vector<std::string> morph_names;
    std::vector<std::vector<MorphDelta>> morphs;
    std::vector<MeshSurface> surfaces;
    std::vector<MeshRange> ranges;
    std::vector<std::uint8_t> atlas{255,255,255,255};
    std::vector<std::uint8_t> normal_atlas{128,128,255,255};
    std::uint32_t atlas_width=1,atlas_height=1;
    std::array<float,4> camera{};
};
DeformedMesh deform_named_reference(const Character& character,const MorphWeights& weights,BoneMotion motion={});
std::array<float,kMaxCharacterMorphs> character_morph_weights(const Character& character,const MorphWeights& weights);
Mat4 identity_matrix();
Mat4 multiply(const Mat4& a, const Mat4& b);
Character load_character_glb(const std::filesystem::path& path);
using JointPalette = std::array<Mat4,kMaxCharacterJoints>;
JointPalette character_palette(const Character& character, SpeechPose pose,BoneMotion motion={});
std::vector<std::array<float,3>> deform_reference(const Character& character, SpeechPose pose);
} // namespace jali
