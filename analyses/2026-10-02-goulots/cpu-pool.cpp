#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include "strata/kernels/cpu/native_expert.hpp"
#include "strata/kernels/cpu/pool.hpp"
#include "ggml.h"
#include <chrono>
#include <cstdio>
#include <cstring>
#include <random>
#include <vector>
namespace cpu=strata::kernels::cpu;
volatile float sink;
int main() {
    constexpr int H=2560,F=640,E=128;
    cpu::NativeFmt fmt; std::string error;
    if(!cpu::native_fmt(12,7,H,F,fmt,error)) return 1;
    std::vector<unsigned char> base(fmt.bytes);
    std::mt19937 random(42); std::normal_distribution<float> normal(0,.02f);
    auto quant=[&](int type,int rows,int cols,unsigned char* dst) {
        std::vector<float> floats((size_t)rows*cols);
        for(auto& value:floats) value=normal(random);
        ggml_quantize_chunk((ggml_type)type,floats.data(),dst,0,rows,cols,nullptr);
    };
    quant(12,F,H,base.data()); quant(12,F,H,base.data()+fmt.up_off); quant(7,H,F,base.data()+fmt.down_off);
    std::vector<unsigned char> weights(fmt.bytes*E);
    for(int e=0;e<E;++e) std::memcpy(weights.data()+fmt.bytes*e,base.data(),fmt.bytes);
    SetThreadAffinityMask(GetCurrentThread(),1);
    std::printf("workers,threads_including_host,tokens_per_expert,jobs_per_batch,repeats,seconds,experts_s,logical_weight_GB_s\n");
    for(int workers:{3,7,15}) {
        cpu::ExpertPool pool(workers,true,true);
        for(int nt:{1,2}) for(int jobs:{4,8,16}) {
            std::vector<float> input(nt*H,.15f),out(jobs*nt*H);
            std::vector<unsigned char> acts(nt*cpu::kNativeActBytes);
            std::vector<cpu::ExpertJobMulti> batch(jobs);
            for(int t=0;t<nt;++t) cpu::native_quant_act(fmt,input.data()+t*H,acts.data()+t*cpu::kNativeActBytes);
            for(int e=0;e<jobs;++e) {
                batch[e].nt=nt;
                for(int t=0;t<nt;++t) {
                    batch[e].nact[t]=acts.data()+t*cpu::kNativeActBytes;
                    batch[e].act[t]=nullptr;
                    batch[e].out[t]=out.data()+(e*nt+t)*H;
                }
            }
            for(int trial=0;trial<3;++trial) {
                auto start=std::chrono::steady_clock::now();
                constexpr int repeat=64;
                for(int r=0;r<repeat;++r) {
                    for(int e=0;e<jobs;++e) batch[e].blob=weights.data()+fmt.bytes*((r*jobs+e)%E);
                    pool.run_split_multi_native(fmt,batch.data(),jobs);
                }
                sink=out[17];
                double sec=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
                std::printf("%d,%d,%d,%d,%d,%.6f,%.1f,%.3f\n",workers,workers+1,nt,jobs,repeat,sec,jobs*repeat/sec,fmt.bytes*jobs*repeat/sec/1e9);
            }
        }
    }
    return 0;
}
