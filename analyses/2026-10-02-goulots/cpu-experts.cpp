#include "strata/kernels/cpu/native_expert.hpp"
#include "ggml.h"
#include <omp.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <random>
#include <string>
#include <vector>
namespace cpu = strata::kernels::cpu;
volatile float result_sink=0;
int main() {
    constexpr int H=2560,F=640,E=128;
    std::printf("gu_type,down_type,tokens_per_expert,threads,expert_jobs,seconds,experts_s,logical_weight_GB_s\n");
    for(auto types : {std::pair{12,7},std::pair{12,8},std::pair{13,8}}) {
        cpu::NativeFmt fmt; std::string err;
        if(!cpu::native_fmt(types.first,types.second,H,F,fmt,err)) { std::fprintf(stderr,"%s\n",err.c_str()); return 1; }
        std::vector<unsigned char> base(fmt.bytes);
        std::mt19937 random(42); std::normal_distribution<float> normal(0,.02f);
        auto quant=[&](int type,int rows,int cols,unsigned char* dst) {
            std::vector<float> weights((size_t)rows*cols);
            for(auto& x:weights) x=normal(random);
            ggml_quantize_chunk((ggml_type)type,weights.data(),dst,0,rows,cols,nullptr);
        };
        quant(types.first,F,H,base.data()); quant(types.first,F,H,base.data()+fmt.up_off);
        quant(types.second,H,F,base.data()+fmt.down_off);
        std::vector<unsigned char> weights(fmt.bytes*E);
        for(int i=0;i<E;++i) std::memcpy(weights.data()+fmt.bytes*i,base.data(),fmt.bytes);
        for(int nt : {1,2}) {
            std::vector<float> x(nt*H,.15f),ff(E*nt*F),out(E*nt*H);
            std::vector<unsigned char> acts(nt*cpu::kNativeActBytes),hq(E*nt*cpu::kNativeHBytes);
            const void* a[2];
            for(int t=0;t<nt;++t) { a[t]=acts.data()+t*cpu::kNativeActBytes; cpu::native_quant_act(fmt,x.data()+t*H,(void*)a[t]); }
            auto run=[&](int threads,int repeat) {
                auto start=std::chrono::steady_clock::now();
                for(int r=0;r<repeat;++r) {
                    #pragma omp parallel for num_threads(threads) schedule(static)
                    for(int e=0;e<E;++e) {
                        float* fp[2]; float* op[2]; const void* hp[2];
                        for(int t=0;t<nt;++t) { fp[t]=ff.data()+(e*nt+t)*F; op[t]=out.data()+(e*nt+t)*H; hp[t]=hq.data()+(e*nt+t)*cpu::kNativeHBytes; }
                        cpu::native_gu_rows(fmt,weights.data()+fmt.bytes*e,a,nt,fp,0,F);
                        for(int t=0;t<nt;++t) cpu::native_quant_h(fmt,fp[t],(void*)hp[t]);
                        cpu::native_down_rows(fmt,weights.data()+fmt.bytes*e,hp,nt,op,0,H);
                    }
                }
                result_sink=out[17];
                return std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
            };
            for(int threads : {1,4,8,16}) {
                run(threads,1);
                for(int trial=0;trial<3;++trial) {
                    const int reps=4; double elapsed=run(threads,reps);
                    std::printf("%d,%d,%d,%d,%d,%.6f,%.1f,%.3f\n",types.first,types.second,nt,threads,E*reps,elapsed,E*reps/elapsed,fmt.bytes*E*reps/elapsed/1e9);
                }
            }
        }
    }
    return 0;
}
