#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <immintrin.h>
#include <omp.h>
#include <vector>
#include <cstdio>
#include <cstdlib>
#include <chrono>

using Clock = std::chrono::steady_clock;
volatile unsigned long long sink;
std::vector<DWORD_PTR> affinity;
void pin(int id) {
    if (!SetThreadAffinityMask(GetCurrentThread(), affinity[id])) {
        std::fprintf(stderr, "SetThreadAffinityMask failed %lu\n", GetLastError()); std::exit(2);
    }
}
int main(int argc,char**) {
    DWORD len=0;
    GetLogicalProcessorInformationEx(RelationProcessorCore,nullptr,&len);
    std::vector<char> topology(len);
    if (!GetLogicalProcessorInformationEx(RelationProcessorCore,(PSYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX)topology.data(),&len)) return 1;
    std::vector<DWORD_PTR> siblings;
    for (size_t offset=0;offset<len;) {
        auto* e=(PSYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX)(topology.data()+offset);
        if(e->Relationship==RelationProcessorCore) {
            DWORD_PTR mask=e->Processor.GroupMask[0].Mask;
            if(e->Processor.GroupMask[0].Group!=0) return 1;
            DWORD_PTR first=mask & (~mask+1);
            affinity.push_back(first);
            for(int bit=0;bit<64;++bit) if((mask & ((DWORD_PTR)1<<bit)) && ((DWORD_PTR)1<<bit)!=first) siblings.push_back((DWORD_PTR)1<<bit);
        }
        offset+=e->Size;
    }
    if(argc>1) {
        std::vector<DWORD_PTR> spread;
        size_t half=(affinity.size()+1)/2;
        for(size_t i=0;i<half;++i) {
            spread.push_back(affinity[i]);
            if(i+half<affinity.size()) spread.push_back(affinity[i+half]);
        }
        affinity=spread;
    }
    std::fprintf(stderr,"physical cores %zu, SMT siblings %zu; masks:",affinity.size(),siblings.size());
    affinity.insert(affinity.end(),siblings.begin(),siblings.end());
    for(auto mask:affinity) std::fprintf(stderr," %llx",(unsigned long long)mask);
    std::fprintf(stderr,"\n");
    constexpr size_t bytes=512ull<<20,N=bytes/sizeof(double);
    auto* a=(double*)_aligned_malloc(bytes,64);
    auto* b=(double*)_aligned_malloc(bytes,64);
    auto* dest=(double*)_aligned_malloc(bytes,64);
    if(!a||!b||!dest) return 1;
    omp_set_dynamic(0);
    std::printf("kind,threads,affinity,bytes_per_pass,repeats,seconds,GB_s\n");
    for(int threads:{1,4,8,16,32}) {
        if(threads>(int)affinity.size()) continue;
        #pragma omp parallel num_threads(threads)
        {
            int id=omp_get_thread_num(); pin(id);
            size_t begin=N*id/threads,end=N*(id+1)/threads;
            for(size_t i=begin;i<end;++i) { a[i]=1.0; b[i]=2.0; dest[i]=0.0; }
        }
        for(int kind=0;kind<2;++kind) for(int trial=0;trial<3;++trial) {
            auto start=Clock::now(); unsigned long long sum=0;
            #pragma omp parallel num_threads(threads) reduction(+:sum)
            {
                int id=omp_get_thread_num(); pin(id);
                size_t begin=N*id/threads,end=N*(id+1)/threads;
                if(kind==0) {
                    __m256i acc[8]; for(auto& v:acc) v=_mm256_setzero_si256();
                    for(int rep=0;rep<8;++rep) for(size_t i=begin;i<end;i+=32) {
                        for(int k=0;k<8;++k) acc[k]=_mm256_add_epi64(acc[k],_mm256_load_si256((__m256i*)(a+i+k*4)));
                    }
                    for(int k=1;k<8;++k) acc[0]=_mm256_add_epi64(acc[0],acc[k]);
                    alignas(32) unsigned long long lanes[4]; _mm256_store_si256((__m256i*)lanes,acc[0]);
                    sum+=lanes[0]+lanes[1]+lanes[2]+lanes[3];
                } else {
                    __m256d scale=_mm256_set1_pd(3.0);
                    for(int rep=0;rep<8;++rep) for(size_t i=begin;i<end;i+=32) {
                        for(int k=0;k<8;++k) {
                            size_t j=i+k*4;
                            __m256d value=_mm256_add_pd(_mm256_load_pd(a+j),_mm256_mul_pd(scale,_mm256_load_pd(b+j)));
                            _mm256_stream_pd(dest+j,value);
                        }
                    }
                    _mm_sfence();
                }
            }
            sink=sum;
            double sec=std::chrono::duration<double>(Clock::now()-start).count();
            if(kind && (dest[0]!=7.0||dest[N-1]!=7.0)) return 3;
            double moved=bytes*8.0*(kind?3:1);
            std::printf("%s,%d,%s,%zu,8,%.6f,%.3f\n",kind?"triad_non_temporal":"read_8_accumulators",threads,argc>1?"spread-physical-first":"physical-first",bytes*(kind?3:1),sec,moved/sec/1e9);
        }
    }
    _aligned_free(a); _aligned_free(b); _aligned_free(dest);
    return 0;
}
