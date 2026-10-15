#include "jali/espeak_voice.hpp"
#include "jali/vulkan_renderer.hpp"
#include <json.hpp>
#include <chrono>
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
using nlohmann::json;
int main(int argc,char** argv) {
    try {
        std::filesystem::path output="artifacts/live-session",asset=JALI_DEFAULT_CHARACTER;
        std::string text="Hello. I am Jali. My face is now a skinned character driven by phonemes.";
        std::uint32_t size=512;bool hardware=false;
        for(int i=1;i<argc;++i) {
            std::string flag=argv[i];if(flag=="--require-hardware"){hardware=true;continue;}
            if(i+1>=argc)throw std::invalid_argument("missing live option value");std::string value=argv[++i];
            if(flag=="--output")output=value;else if(flag=="--text")text=value;else if(flag=="--asset")asset=value;
            else if(flag=="--size") {if(value.empty() || value.find_first_not_of("0123456789")!=std::string::npos)throw std::invalid_argument("invalid size");const auto requested=std::stoul(value);if(requested<32 || requested>1024)throw std::invalid_argument("live size must be 32-1024");size=static_cast<std::uint32_t>(requested);}
            else throw std::invalid_argument("unknown live option");
        }
        const auto start=std::chrono::steady_clock::now();
        const auto* data=std::getenv("JALI_ESPEAK_DATA");jali::EspeakVoiceSource speech(data?data:"");
        auto audio=speech.synthesize({text,"espeak-en"});const double duration=double(audio.samples.size())/audio.sample_rate;
        if(!std::any_of(speech.phonemes().begin(),speech.phonemes().end(),[](const auto& c){return !c.symbol.empty() && c.symbol[0]!='_';}))
            throw std::invalid_argument("Text produced no spoken phonemes");
        jali::write_pcm_wav(output/"session.wav",audio);
        json cues=json::array();for(const auto& cue:speech.phonemes())cues.push_back({{"seconds",cue.seconds},{"symbol",cue.symbol}});
        std::ofstream phonemes(output/"phonemes.json");phonemes<<cues.dump(2)<<'\n';phonemes.close();if(!phonemes)throw std::runtime_error("cannot write phonemes");
        jali::VulkanFaceRenderer renderer(size,size,JALI_DEFAULT_FACE_SHADER,hardware);renderer.load_character(asset);
        const auto character=jali::load_character_glb(asset);
        json meta={{"mode","live-mesh"},{"voice","espeak"},{"alignment","tts-phoneme-events"},{"device",renderer.device_name()},
          {"hardware_accelerated",renderer.hardware_accelerated()},{"width",size},{"height",size},{"duration_seconds",duration},
          {"sample_rate",audio.sample_rate},{"vertices",character.vertices.size()},{"triangles",character.indices.size()/3},
          {"bones",character.joints.size()},{"morph_targets",3},{"phoneme_count",speech.phonemes().size()},
          {"text",text},{"prepare_seconds",std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()}};
        std::ofstream session(output/"session.json");session<<meta.dump(2)<<'\n';session.close();if(!session)throw std::runtime_error("cannot write live metadata");
        std::cout<<meta.dump()<<'\n'<<std::flush;
        // Persistent renderer protocol: one finite audio-clock time per line, one tightly packed RGBA frame back.
        std::string line;
        while(std::getline(std::cin,line)) {
            if(line=="quit")break;std::size_t end=0;const double time=std::stod(line,&end);
            if(end!=line.size() || !std::isfinite(time) || time<0 || time>duration+0.25)throw std::invalid_argument("invalid live timestamp");
            const auto pixels=renderer.render_pose(jali::sample_phonemes(speech.phonemes(),time));
            std::cout.write(reinterpret_cast<const char*>(pixels.data()),static_cast<std::streamsize>(pixels.size()));std::cout.flush();if(!std::cout)break;
        }
        return 0;
    }catch(const std::exception& error) {std::cerr<<"jali_live: "<<error.what()<<'\n';return 2;}
}
