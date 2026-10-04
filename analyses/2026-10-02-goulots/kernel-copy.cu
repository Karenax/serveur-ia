#include <cuda_runtime.h>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
void check(cudaError_t e) { if(e!=cudaSuccess) { std::fprintf(stderr,"%s\n",cudaGetErrorString(e)); std::exit(1); } }
// Exact loop and launch dimensions from Strata src/kernels/cuda/verify_kernels.cu.
__global__ void fetch_blobs_kernel(const unsigned long long* __restrict__ src,const int* __restrict__ n,
                                 uint4* __restrict__ dst,long long per) {
    const long long total=(long long)*n*per;
    for(long long i=(long long)blockIdx.x*blockDim.x+threadIdx.x;i<total;i+=(long long)gridDim.x*blockDim.x) {
        const long long k=i/per,off=i-k*per;
        dst[i]=((const uint4*)src[k])[off];
    }
}
int main() {
    std::printf("kind,device,experts,blob_bytes,repeats,seconds,GB_s\n");
    const size_t blob=3072000,bytes=20*blob;
    void* host=nullptr; check(cudaHostAlloc(&host,bytes,cudaHostAllocMapped|cudaHostAllocPortable));
    std::memset(host,17,bytes);
    for(int g=0;g<2;++g) {
        check(cudaSetDevice(g)); void* alias=nullptr; check(cudaHostGetDevicePointer(&alias,host,0));
        void* dst=nullptr; unsigned long long* ptr=nullptr; int* count=nullptr; cudaStream_t stream;
        check(cudaMalloc(&dst,bytes)); check(cudaMalloc((void**)&ptr,20*sizeof(*ptr))); check(cudaMalloc((void**)&count,4));
        check(cudaStreamCreateWithFlags(&stream,cudaStreamNonBlocking));
        std::vector<unsigned long long> pointers;
        for(int i=0;i<20;++i) pointers.push_back((unsigned long long)((char*)alias+i*blob));
        check(cudaMemcpy(ptr,pointers.data(),20*sizeof(*ptr),cudaMemcpyHostToDevice));
        for(int n : {6,12,20}) for(int mode=0;mode<2;++mode) for(int trial=0;trial<3;++trial) {
            check(cudaMemcpy(count,&n,4,cudaMemcpyHostToDevice));
            if(mode==0) fetch_blobs_kernel<<<384,256,0,stream>>>(ptr,count,(uint4*)dst,blob/16);
            else for(int i=0;i<n;++i) check(cudaMemcpyAsync((char*)dst+i*blob,(char*)host+i*blob,blob,cudaMemcpyHostToDevice,stream));
            check(cudaStreamSynchronize(stream));
            auto start=std::chrono::steady_clock::now();
            for(int r=0;r<128;++r) {
                if(mode==0) fetch_blobs_kernel<<<384,256,0,stream>>>(ptr,count,(uint4*)dst,blob/16);
                else for(int i=0;i<n;++i) check(cudaMemcpyAsync((char*)dst+i*blob,(char*)host+i*blob,blob,cudaMemcpyHostToDevice,stream));
            }
            check(cudaStreamSynchronize(stream));
            double sec=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
            std::printf("%s,%d,%d,%zu,128,%.6f,%.3f\n",mode==0?"Strata_fetch_kernel":"DMA_expert_copies",g,n,blob,sec,n*blob*128.0/sec/1e9);
            std::vector<unsigned char> got(n*blob); check(cudaMemcpy(got.data(),dst,got.size(),cudaMemcpyDeviceToHost));
            for(auto v:got) if(v!=17) { std::fprintf(stderr,"Copy mismatch\n"); return 2; }
        }
        cudaStreamDestroy(stream); cudaFree(dst); cudaFree(ptr); cudaFree(count);
    }
    cudaFreeHost(host); return 0;
}
