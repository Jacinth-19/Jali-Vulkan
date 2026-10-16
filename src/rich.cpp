// Bounded native named-morph renderer protocol, separate from speech inference.
#include "jali/vulkan_renderer.hpp"
#include <json.hpp>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
using nlohmann::json;
int main(int argc,char** argv){
    try{
        std::filesystem::path asset,output="artifacts/native-head-proof";std::uint32_t size=512;bool test=false,hardware=false;
        for(int i=1;i<argc;++i){const std::string flag=argv[i];if(flag=="--test"){test=true;continue;}if(flag=="--require-hardware"){hardware=true;continue;}
            if(i+1>=argc)throw std::invalid_argument("missing rich renderer option");const std::string value=argv[++i];
            if(flag=="--asset")asset=value;else if(flag=="--output")output=value;else if(flag=="--size"){if(value.empty()||value.find_first_not_of("0123456789")!=std::string::npos)throw std::invalid_argument("invalid size");size=std::stoul(value);if(size<32||size>1024)throw std::invalid_argument("size must be 32-1024");}else throw std::invalid_argument("unknown rich renderer option");
        }
        const auto c=jali::load_character_glb(asset);if(c.morph_names.empty())throw std::invalid_argument("requires rich named-morph profile");
        jali::VulkanFaceRenderer renderer(size,size,JALI_DEFAULT_FACE_SHADER,hardware);renderer.load_character(asset);std::filesystem::create_directories(output);
        json metadata={{"renderer","native-vulkan-rich-v1"},{"device",renderer.device_name()},{"hardware_accelerated",renderer.hardware_accelerated()},{"width",size},{"height",size},{"vertices",c.vertices.size()},{"triangles",c.indices.size()/3},{"palette_nodes",c.joints.size()},{"primitive_groups",c.ranges.size()},{"named_targets",c.morph_names.size()},{"atlas_width",c.atlas_width},{"atlas_height",c.atlas_height}};
        if(test){
            json poses=json::array();
            for(const auto& weights:std::vector<jali::MorphWeights>{{},{{"viseme_PP",.95f}},{{"viseme_aa",.88f}},{{"viseme_FF",.85f}},{{"viseme_U",.88f},{"viseme_O",.12f}},{{"viseme_nn",.65f},{"viseme_DD",.22f}},{{"eyeBlinkLeft",1},{"eyeBlinkRight",1}},{{"mouthSmileLeft",.16f},{"mouthSmileRight",.16f}}}){
                const auto pixels=renderer.render_named_pose(weights);const auto cpu=jali::deform_named_reference(c,weights);const auto gpu=renderer.deformed_positions(),normals=renderer.deformed_normals();float position_error=0,normal_error=0;
                for(std::size_t i=0;i<gpu.size();++i)for(int k=0;k<3;++k){position_error=std::max(position_error,std::abs(gpu[i][k]-cpu.positions[i][k]));normal_error=std::max(normal_error,std::abs(normals[i][k]-cpu.normals[i][k]));}
                if(position_error>3e-5||normal_error>3e-4)throw std::runtime_error("rich CPU/GPU deformation mismatch");
                const auto prefix="reference-"+std::to_string(poses.size());
                std::ofstream positions(output/(prefix+".bin"),std::ios::binary);positions.write(reinterpret_cast<const char*>(cpu.positions.data()),std::streamsize(cpu.positions.size()*sizeof(cpu.positions[0])));
                poses.push_back({{"position_file",prefix+".bin"},{"weights",weights},{"max_position_error",position_error},{"max_normal_error",normal_error}});
            }
            try{renderer.render_named_pose({{"unknown",1}});throw std::runtime_error("unknown target accepted");}catch(const std::invalid_argument&){}
            metadata["cpu_gpu_poses"]=poses;std::ofstream(output/"gpu-reference.json")<<metadata.dump(2)<<'\n';
        }
        std::cout<<metadata.dump()<<'\n'<<std::flush;
        std::string line;std::size_t frames=0;
        while(std::getline(std::cin,line)){
            if(line=="quit")break;if(line.size()>16384||++frames>10000)throw std::invalid_argument("protocol budget exceeded");
            const auto request=json::parse(line);if(!request.is_object()||request.size()>jali::kMaxCharacterMorphs)throw std::invalid_argument("expected named weights object");
            jali::BoneMotion motion;auto object=request;
            if(request.contains("weights")){
                if(request.size()>2||(request.size()==2&&!request.contains("motion"))||!request["weights"].is_object())throw std::invalid_argument("invalid named pose envelope");object=request["weights"];
                if(request.contains("motion")){
                    const auto m=request["motion"].get<std::map<std::string,float>>();for(const auto& [k,v]:m){if(k=="head_yaw")motion.head_yaw=v;else if(k=="head_roll")motion.head_roll=v;else if(k=="eye_yaw")motion.eye_yaw=v;else if(k=="eye_pitch")motion.eye_pitch=v;else throw std::invalid_argument("unknown bone motion");}
                }
            }
            const auto weights=object.get<jali::MorphWeights>();const auto pixels=renderer.render_named_pose(weights,motion);
            std::cout.write(reinterpret_cast<const char*>(pixels.data()),std::streamsize(pixels.size()));std::cout.flush();if(!std::cout)break;
        }
        return 0;
    }catch(const std::exception& error){std::cerr<<"jali_rich: "<<error.what()<<'\n';return 1;}
}
