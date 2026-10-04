#include <cuda_runtime.h>
#include <immintrin.h>
#include <omp.h>
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>
#include <vector>

using Clock = std::chrono::steady_clock;
void check(cudaError_t e) { if(e != cudaSuccess) { std::fprintf(stderr,"CUDA: %s\n",cudaGetErrorString(e)); std::exit(1); } }
double seconds(Clock::time_point t) { return std::chrono::duration<double>(Clock::now()-t).count(); }
volatile unsigned long long sink = 0;

int main() {
    std::printf("kind,device,threads,bytes_per_op,repeats,seconds,GB_s\n");
    const size_t ramBytes = 512ull<<20;
    auto ram = (unsigned long long*)_aligned_malloc(ramBytes,64);
    if (!ram) return 1;
    #pragma omp parallel for num_threads(16)
    for (long long i=0;i<(long long)(ramBytes/8);++i) ram[i]=(unsigned long long)i;
    for (int threads : {1,2,4,8,16}) {
        std::vector<double> rates;
        for (int trial=0;trial<3;++trial) {
            unsigned long long sum=0;
            auto start=Clock::now();
            #pragma omp parallel num_threads(threads) reduction(+:sum)
            {
                int id=omp_get_thread_num(), n=omp_get_num_threads();
                size_t begin=(ramBytes/32)*id/n, end=(ramBytes/32)*(id+1)/n;
                __m256i acc=_mm256_setzero_si256();
                for(int rep=0;rep<16;++rep)
                    for(size_t i=begin;i<end;++i) acc=_mm256_add_epi64(acc,_mm256_loadu_si256((__m256i*)ram+i));
                alignas(32) unsigned long long lane[4];
                _mm256_store_si256((__m256i*)lane,acc);
                sum+=lane[0]+lane[1]+lane[2]+lane[3];
            }
            sink=sum;
            double elapsed=seconds(start);
            std::printf("RAM_read,-1,%d,%zu,16,%.6f,%.3f\n",threads,ramBytes,elapsed,ramBytes*16.0/elapsed/1e9);
        }
    }
    _aligned_free(ram);
    const size_t gpuBytes=64ull<<20;
    void* host=nullptr;
    check(cudaHostAlloc(&host,gpuBytes,cudaHostAllocPortable));
    std::memset(host,7,gpuBytes);
    void* dev[2]={}; void* other[2]={}; cudaStream_t stream[2]={};
    for(int g=0;g<2;++g) {
        check(cudaSetDevice(g));
        check(cudaMalloc(&dev[g],gpuBytes)); check(cudaMalloc(&other[g],gpuBytes));
        check(cudaStreamCreateWithFlags(&stream[g],cudaStreamNonBlocking));
        check(cudaMemcpy(dev[g],host,gpuBytes,cudaMemcpyHostToDevice));
        check(cudaMemcpy(other[g],host,gpuBytes,cudaMemcpyHostToDevice));
    }
    for(int g=0;g<2;++g) for(size_t bytes : {3ull<<20,64ull<<20}) for(int trial=0;trial<3;++trial) {
        check(cudaSetDevice(g)); int repeat=bytes==(3ull<<20)?512:32;
        auto start=Clock::now();
        for(int i=0;i<repeat;++i) check(cudaMemcpyAsync(dev[g],host,bytes,cudaMemcpyHostToDevice,stream[g]));
        check(cudaStreamSynchronize(stream[g])); double elapsed=seconds(start);
        std::printf("H2D,%d,1,%zu,%d,%.6f,%.3f\n",g,bytes,repeat,elapsed,bytes*(double)repeat/elapsed/1e9);
    }
    for(int trial=0;trial<3;++trial) {
        auto start=Clock::now(); std::thread workers[2];
        for(int g=0;g<2;++g) workers[g]=std::thread([&,g]{
            check(cudaSetDevice(g));
            for(int i=0;i<32;++i) check(cudaMemcpyAsync(dev[g],host,gpuBytes,cudaMemcpyHostToDevice,stream[g]));
            check(cudaStreamSynchronize(stream[g]));
        });
        for(auto& w:workers) w.join(); double elapsed=seconds(start);
        std::printf("H2D_both,-1,2,%zu,32,%.6f,%.3f\n",gpuBytes,elapsed,gpuBytes*32.0*2/elapsed/1e9);
    }
    for(int g=0;g<2;++g) for(int trial=0;trial<3;++trial) {
        check(cudaSetDevice(g)); auto start=Clock::now();
        for(int i=0;i<128;++i) check(cudaMemcpyAsync(other[g],dev[g],gpuBytes,cudaMemcpyDeviceToDevice,stream[g]));
        check(cudaStreamSynchronize(stream[g])); double elapsed=seconds(start);
        std::printf("HBM_copy_read_plus_write,%d,1,%zu,128,%.6f,%.3f\n",g,gpuBytes,elapsed,gpuBytes*128.0*2/elapsed/1e9);
    }
    for(int g=0;g<2;++g) { check(cudaSetDevice(g)); cudaStreamDestroy(stream[g]); cudaFree(dev[g]); cudaFree(other[g]); }
    cudaFreeHost(host);
    return 0;
}
