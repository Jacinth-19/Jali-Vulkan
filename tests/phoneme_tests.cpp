#include "jali/phonemes.hpp"
#include <iostream>
#include <limits>
#include <stdexcept>
#include <functional>
void check(bool ok){if(!ok)throw std::runtime_error("phoneme contract failed");}
void rejects(const std::function<void()>& run){try{run();}catch(const std::invalid_argument&){return;}throw std::runtime_error("invalid phoneme timeline accepted");}
int main(){try{
    const std::vector<jali::PhonemeCue> cues{{0,"m"},{.12,"a"},{.4,"u:"},{.6,"_"}};
    check(jali::sample_phonemes(cues,.05).close==1);
    check(jali::sample_phonemes(cues,.2).jaw>.7);
    check(jali::sample_phonemes(cues,.5).round==1);
    check(jali::sample_phonemes(cues,.7).jaw==0);
    const auto blend=jali::sample_phonemes(cues,.105);check(blend.close>0 && blend.close<1 && blend.jaw>0);
    check(jali::sample_phonemes({},1).jaw==0);
    check(jali::sample_phonemes({{1,"a"}},.5).jaw==0);
    check(jali::phoneme_pose("I2").jaw==jali::phoneme_pose("I").jaw);
    check(jali::phoneme_pose("a#").jaw>.7);
    rejects([&]{jali::sample_phonemes(cues,-1);});
    rejects([&]{jali::sample_phonemes(cues,std::numeric_limits<double>::quiet_NaN());});
    rejects([&]{jali::sample_phonemes({{1,"a"},{0,"m"}},1);});
    rejects([&]{jali::sample_phonemes({{std::numeric_limits<double>::infinity(),"a"}},1);});
    std::cout<<"phoneme classes, timing, silence, closure, stress and coarticulation passed\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
