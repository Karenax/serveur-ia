#include "whisper.h"
#include "ggml-backend.h"
#include <algorithm>
#include <cstring>
#include <mutex>
#include <string>
#include <vector>

#ifdef _WIN32
#define API extern "C" __declspec(dllexport)
#else
#define API extern "C" __attribute__((visibility("default")))
#endif

namespace {
std::once_flag initialized;
thread_local std::string error;
void initialize() {std::call_once(initialized, []{ggml_backend_load_all();});}
std::vector<ggml_backend_dev_t> devices() {
    initialize();std::vector<ggml_backend_dev_t> result;
    for(size_t i=0;i<ggml_backend_dev_count();i++){
        auto dev=ggml_backend_dev_get(i);auto type=ggml_backend_dev_type(dev);
        if(type==GGML_BACKEND_DEVICE_TYPE_GPU||type==GGML_BACKEND_DEVICE_TYPE_IGPU)result.push_back(dev);
    }
    return result;
}
struct Session {whisper_context* context=nullptr;std::string text;};
}
struct GPUInfo {char name[64];char description[256];char pci_id[128];int kind;size_t free_bytes,total_bytes;};
API int ka_gpu_info_size(){return sizeof(GPUInfo);}
API int ka_gpu_count(){return (int)devices().size();}
API int ka_gpu_info(int index,GPUInfo* out){
    auto list=devices();if(!out||index<0||index>=(int)list.size())return -1;
    ggml_backend_dev_props props={};ggml_backend_dev_get_props(list[index],&props);
    *out={};
    strncpy(out->name,props.name?props.name:"",sizeof(out->name)-1);
    strncpy(out->description,props.description?props.description:"",sizeof(out->description)-1);
    strncpy(out->pci_id,props.device_id?props.device_id:"",sizeof(out->pci_id)-1);
    out->kind=(int)props.type;out->free_bytes=props.memory_free;out->total_bytes=props.memory_total;return 0;
}
API const char* ka_error(){return error.c_str();}
API void* ka_open(const char* model,const char* device){
    error.clear();initialize();if(!model||!device){error="Missing model/device";return nullptr;}
    auto params=whisper_context_default_params();params.use_gpu=strcmp(device,"CPU")!=0;params.flash_attn=false;
    if(params.use_gpu){
        auto list=devices();bool found=false;
        for(size_t i=0;i<list.size();i++)if(!strcmp(ggml_backend_dev_name(list[i]),device)){
            auto probe=ggml_backend_dev_init(list[i],nullptr);
            if(!probe){error="Selected GPU initialization failed";return nullptr;}
            ggml_backend_free(probe);params.gpu_device=(int)i;found=true;break;
        }
        if(!found){error="Selected GPU missing; no implicit fallback";return nullptr;}
    }
    auto context=whisper_init_from_file_with_params(model,params);
    if(!context){error="Whisper model initialization failed";return nullptr;}
    auto* session=new Session;session->context=context;return session;
}
typedef bool (*Cancel)(void*);
API const char* ka_transcribe(void* owner,const float* audio,int count,bool final,Cancel cancel,void* data){
    error.clear();auto* session=(Session*)owner;
    if(!session||!audio||count<1600||count>28*16000){error="Invalid audio bounds";return nullptr;}
    auto params=whisper_full_default_params(WHISPER_SAMPLING_GREEDY);
    params.language="fr";params.detect_language=false;params.translate=false;params.no_context=true;
    params.n_threads=6;params.print_progress=false;params.print_realtime=false;params.print_timestamps=false;
    params.print_special=false;params.no_timestamps=false;params.single_segment=false;
    params.temperature=0;params.temperature_inc=0;params.greedy.best_of=1;
    // Whisper's default pads every preview to 30 s. Keep one second of
    // right context, aligned to encoder blocks, instead of recomputing silence.
    params.audio_ctx=std::min(1500,std::max(256,(((count+319)/320+64+127)/128)*128));
    params.suppress_blank=true;params.suppress_nst=true;params.abort_callback=cancel;params.abort_callback_user_data=data;
    if(whisper_full(session->context,params,audio,count)!=0){error="Whisper decoding failed or cancelled";return nullptr;}
    session->text.clear();
    for(int i=0;i<whisper_full_n_segments(session->context);i++){
        const char* text=whisper_full_get_segment_text(session->context,i);
        if(text)session->text+=text;
    }
    return session->text.c_str();
}
API void ka_close(void* owner){auto* session=(Session*)owner;if(session){whisper_free(session->context);delete session;}}
