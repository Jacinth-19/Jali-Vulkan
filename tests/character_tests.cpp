#include "jali/character.hpp"
#include <json.hpp>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
using nlohmann::json;
std::uint32_t u32(const unsigned char* p){return std::uint32_t(p[0])|(std::uint32_t(p[1])<<8)|(std::uint32_t(p[2])<<16)|(std::uint32_t(p[3])<<24);}
void put(std::ostream& out,std::uint32_t n){for(int i=0;i<4;++i)out.put(char((n>>(i*8))&255));}
int main(){
    const auto temporary=std::filesystem::path("invalid-character-test.glb");
    struct Clean {std::filesystem::path p;~Clean(){std::error_code e;std::filesystem::remove(p,e);}} clean{temporary};
    try {
        std::ifstream file(JALI_DEFAULT_CHARACTER,std::ios::binary|std::ios::ate);const auto n=file.tellg();
        std::vector<unsigned char> bytes(static_cast<std::size_t>(n));file.seekg(0);file.read(reinterpret_cast<char*>(bytes.data()),n);
        const auto json_size=u32(bytes.data()+12);auto original=json::parse(bytes.begin()+20,bytes.begin()+20+json_size);
        const auto bin_start=20+json_size+8;std::vector<unsigned char> bin(bytes.begin()+bin_start,bytes.end());int rejected=0;
        auto reject=[&](const json& model,const std::vector<unsigned char>& data){
            auto text=model.dump();while(text.size()%4)text+=' ';
            std::ofstream out(temporary,std::ios::binary);put(out,0x46546c67);put(out,2);put(out,std::uint32_t(28+text.size()+data.size()));
            put(out,std::uint32_t(text.size()));put(out,0x4e4f534a);out.write(text.data(),text.size());put(out,std::uint32_t(data.size()));put(out,0x004e4942);out.write(reinterpret_cast<const char*>(data.data()),data.size());out.close();
            try{jali::load_character_glb(temporary);}catch(const std::invalid_argument&){++rejected;return;}throw std::runtime_error("malformed GLB was accepted");
        };
        auto m=original;m["nodes"][1]["children"]={0};reject(m,bin);
        m=original;m["nodes"][1]["translation"]={0,1e100,0};reject(m,bin);
        m=original;m["nodes"][1]["scale"]={2,1,1};reject(m,bin);
        m=original;m["accessors"][0]["byteOffset"]=999999999;reject(m,bin);
        m=original;m["meshes"][0]["extras"]["targetNames"]={"jawOpen","wrong","mouthClose"};reject(m,bin);
        m=original;m["buffers"][0]["uri"]="../private.wav";reject(m,bin);
        m=original;m["skins"][0]["joints"]={0,0};reject(m,bin);
        m=original;m["skins"][0]["joints"]=std::vector<int>(jali::kMaxCharacterJoints+1,0);reject(m,bin);
        m=original;m["meshes"][0]["primitives"][0]["attributes"].erase("WEIGHTS_0");reject(m,bin);
        auto bad=bin;int a=original["meshes"][0]["primitives"][0]["attributes"]["JOINTS_0"];int v=original["accessors"][a]["bufferView"];
        std::size_t at=original["bufferViews"][v]["byteOffset"];bad[at]=255;bad[at+1]=255;reject(original,bad);
        bad=bin;a=original["meshes"][0]["primitives"][0]["attributes"]["WEIGHTS_0"];v=original["accessors"][a]["bufferView"];at=original["bufferViews"][v]["byteOffset"];
        std::fill_n(bad.begin()+at,4,0);reject(original,bad);
        bad=bin;v=original["accessors"][0]["bufferView"];at=original["bufferViews"][v]["byteOffset"];bad[at]=0;bad[at+1]=0;bad[at+2]=0x80;bad[at+3]=0x7f;reject(original,bad);
        std::ifstream rich_file(JALI_RICH_FIXTURE,std::ios::binary|std::ios::ate);const auto rich_size=rich_file.tellg();std::vector<unsigned char> rb(static_cast<std::size_t>(rich_size));rich_file.seekg(0);rich_file.read(reinterpret_cast<char*>(rb.data()),rich_size);
        const auto rjson=u32(rb.data()+12);original=json::parse(rb.begin()+20,rb.begin()+20+rjson);bin.assign(rb.begin()+28+rjson,rb.end());
        m=original;m["extras"]["jaliNativeProfile"]="unknown";reject(m,bin);
        m=original;m["extras"]["nativeAtlas"]["width"]="bad";reject(m,bin);
        m=original;m["extras"]["nativeAtlas"]["height"]=-1;reject(m,bin);
        m=original;m["extras"]["nativeAtlas"]["width"]=1.5;reject(m,bin);
        m=original;m["extras"]["nativeAtlas"]["width"]=1e100;reject(m,bin);
        m=original;m["extras"]["nativeAtlas"]["width"]=2;reject(m,bin);
        m=original;m["extras"]["nativeAtlas"]["normalBufferView"]=999999;reject(m,bin);
        m=original;m["extras"]["camera"]={0,0};reject(m,bin);
        m=original;m["extras"]["camera"]={0,0,0,-1};reject(m,bin);
        m=original;m["nodes"][0]["children"]={0};reject(m,bin);
        m=original;m["meshes"][0]["extras"]["targetNames"]={"viseme_PP","viseme_PP","viseme_U"};reject(m,bin);
        m=original;m["meshes"][0]["primitives"][0]["targets"].erase(0);reject(m,bin);
        m=original;m["meshes"][0]["primitives"][0]["material"]=999;reject(m,bin);
        m=original;m["materials"][0]["pbrMetallicRoughness"]["roughnessFactor"]=2;reject(m,bin);
        m=original;m["buffers"][0]["uri"]="../private.wav";reject(m,bin);
        std::cout<<rejected<<" malformed GLB cases rejected\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
