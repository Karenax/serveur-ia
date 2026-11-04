// Exact mma_884 function from Strata v0.2.10 src/split/src/moe_mma.cuh.
__device__ __forceinline__ void mma_884(float (&d)[8], unsigned a0, unsigned a1, unsigned b0, unsigned b1) {
    asm volatile("mma.sync.aligned.m8n8k4.row.col.f32.f16.f16.f32 {%0,%1,%2,%3,%4,%5,%6,%7}, {%8,%9}, {%10,%11}, "
                 "{%0,%1,%2,%3,%4,%5,%6,%7};\n"
                 : "+f"(d[0]), "+f"(d[1]), "+f"(d[2]), "+f"(d[3]), "+f"(d[4]), "+f"(d[5]), "+f"(d[6]), "+f"(d[7])
                 : "r"(a0), "r"(a1), "r"(b0), "r"(b1));
}
extern "C" __global__ void probe(float *out) { float d[8] = {}; mma_884(d,0,0,0,0); for (int i=0;i<8;++i) out[i]=d[i]; }
