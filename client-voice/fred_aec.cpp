// Windows Voice Capture DSP: system echo cancellation, noise suppression and AGC.
#include <windows.h>
#include <mediaobj.h>
#include <uuids.h>
#include <dmo.h>
#include <wmcodecdsp.h>
#include <propsys.h>
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <vector>
#include <algorithm>

class Buffer final : public IMediaBuffer {
    LONG references=1;
public:
    std::vector<BYTE> data;
    DWORD length=0;
    explicit Buffer(DWORD size):data(size){}
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid,void** value) override {
        if(!value)return E_POINTER;
        *value=nullptr;
        if(iid==IID_IUnknown||iid==IID_IMediaBuffer){*value=this;AddRef();return S_OK;}
        return E_NOINTERFACE;
    }
    ULONG STDMETHODCALLTYPE AddRef() override {return InterlockedIncrement(&references);}
    ULONG STDMETHODCALLTYPE Release() override {auto n=InterlockedDecrement(&references);if(!n)delete this;return n;}
    HRESULT STDMETHODCALLTYPE SetLength(DWORD n) override {if(n>data.size())return E_INVALIDARG;length=n;return S_OK;}
    HRESULT STDMETHODCALLTYPE GetMaxLength(DWORD* n) override {*n=(DWORD)data.size();return S_OK;}
    HRESULT STDMETHODCALLTYPE GetBufferAndLength(BYTE** p,DWORD* n) override {if(p)*p=data.data();if(n)*n=length;return S_OK;}
};
struct Capture {
    IMediaObject* object=nullptr;
    Buffer* buffer=new Buffer(3200);
    bool initialized=false;
    IAudioClient* render=nullptr;
    IAudioRenderClient* silence=nullptr;
    UINT32 render_frames=0;
    ~Capture(){if(object){object->FreeStreamingResources();object->Release();}if(render)render->Stop();if(silence)silence->Release();if(render)render->Release();buffer->Release();if(initialized)CoUninitialize();}
    HRESULT fill_silence(){
        UINT32 padding=0;auto hr=render->GetCurrentPadding(&padding);
        if(FAILED(hr)||padding>=render_frames)return hr;
        BYTE* bytes=nullptr;const auto frames=render_frames-padding;
        hr=silence->GetBuffer(frames,&bytes);
        return FAILED(hr)?hr:silence->ReleaseBuffer(frames,AUDCLNT_BUFFERFLAGS_SILENT);
    }
};
static thread_local HRESULT last_error=S_OK;
extern "C" __declspec(dllexport) LONG fred_aec_last_error(){return last_error;}

// Source-mode AEC produces no microphone output without an active rendering
// stream, even while the assistant is silent. Keep a shared silent reference
// on the same default endpoint used by the browser, without changing devices.
static HRESULT start_reference(Capture* capture){
    IMMDeviceEnumerator* devices=nullptr;IMMDevice* device=nullptr;
    auto hr=CoCreateInstance(__uuidof(MMDeviceEnumerator),nullptr,CLSCTX_ALL,__uuidof(IMMDeviceEnumerator),(void**)&devices);
    if(SUCCEEDED(hr))hr=devices->GetDefaultAudioEndpoint(eRender,eConsole,&device);
    if(SUCCEEDED(hr))hr=device->Activate(__uuidof(IAudioClient),CLSCTX_ALL,nullptr,(void**)&capture->render);
    WAVEFORMATEX* mix=nullptr;
    if(SUCCEEDED(hr))hr=capture->render->GetMixFormat(&mix);
    if(SUCCEEDED(hr))hr=capture->render->Initialize(AUDCLNT_SHAREMODE_SHARED,0,2000000,0,mix,nullptr);
    if(mix)CoTaskMemFree(mix);
    if(SUCCEEDED(hr))hr=capture->render->GetBufferSize(&capture->render_frames);
    if(SUCCEEDED(hr))hr=capture->render->GetService(__uuidof(IAudioRenderClient),(void**)&capture->silence);
    if(SUCCEEDED(hr))hr=capture->fill_silence();
    if(SUCCEEDED(hr))hr=capture->render->Start();
    if(device)device->Release();if(devices)devices->Release();
    return hr;
}
static HRESULT property(IPropertyStore* properties,REFPROPERTYKEY key,LONG n){
    PROPVARIANT value;PropVariantInit(&value);value.vt=VT_I4;value.lVal=n;
    return properties->SetValue(key,value);
}
static HRESULT boolean_property(IPropertyStore* properties,REFPROPERTYKEY key,bool enabled){
    PROPVARIANT value;PropVariantInit(&value);value.vt=VT_BOOL;value.boolVal=enabled?VARIANT_TRUE:VARIANT_FALSE;
    return properties->SetValue(key,value);
}
// Resolve both endpoints for the same Windows role as Web Audio and the silent
// render stream. In particular, a separate communications headset must not make
// the DSP listen to a different microphone or echo reference.
static HRESULT default_index(EDataFlow flow,WORD* index){
    IMMDeviceEnumerator* devices=nullptr;IMMDeviceCollection* collection=nullptr;IMMDevice* selected=nullptr;
    LPWSTR selected_id=nullptr;
    auto hr=CoCreateInstance(__uuidof(MMDeviceEnumerator),nullptr,CLSCTX_ALL,__uuidof(IMMDeviceEnumerator),(void**)&devices);
    if(SUCCEEDED(hr))hr=devices->GetDefaultAudioEndpoint(flow,eConsole,&selected);
    if(SUCCEEDED(hr))hr=selected->GetId(&selected_id);
    if(SUCCEEDED(hr))hr=devices->EnumAudioEndpoints(flow,DEVICE_STATE_ACTIVE,&collection);
    UINT count=0;if(SUCCEEDED(hr))hr=collection->GetCount(&count);
    bool found=false;
    for(UINT i=0;SUCCEEDED(hr)&&i<count&&i<0xffff;++i){
        IMMDevice* candidate=nullptr;LPWSTR candidate_id=nullptr;
        hr=collection->Item(i,&candidate);
        if(SUCCEEDED(hr))hr=candidate->GetId(&candidate_id);
        if(SUCCEEDED(hr)&&wcscmp(selected_id,candidate_id)==0){*index=(WORD)i;found=true;}
        if(candidate_id)CoTaskMemFree(candidate_id);if(candidate)candidate->Release();
        if(found)break;
    }
    if(selected_id)CoTaskMemFree(selected_id);if(selected)selected->Release();
    if(collection)collection->Release();if(devices)devices->Release();
    return FAILED(hr)?hr:found?S_OK:E_FAIL;
}
extern "C" __declspec(dllexport) void* fred_aec_open() {
    last_error=S_OK;
    auto capture=new Capture;
    HRESULT hr=CoInitializeEx(nullptr,COINIT_MULTITHREADED);
    if(FAILED(hr)){last_error=hr;delete capture;return nullptr;}
    capture->initialized=true;
    hr=CoCreateInstance(CLSID_CWMAudioAEC,nullptr,CLSCTX_INPROC_SERVER,IID_IMediaObject,(void**)&capture->object);
    if(FAILED(hr)){last_error=hr;delete capture;return nullptr;}
    IPropertyStore* properties=nullptr;
    hr=capture->object->QueryInterface(IID_IPropertyStore,(void**)&properties);
    if(SUCCEEDED(hr)){
        hr=property(properties,MFPKEY_WMAAECMA_SYSTEM_MODE,SINGLE_CHANNEL_AEC);
        WORD input=0,output=0;
        if(SUCCEEDED(hr))hr=default_index(eCapture,&input);
        if(SUCCEEDED(hr))hr=default_index(eRender,&output);
        if(SUCCEEDED(hr))hr=property(properties,MFPKEY_WMAAECMA_DEVICE_INDEXES,LONG((DWORD(output)<<16)|input));
        if(SUCCEEDED(hr))hr=boolean_property(properties,MFPKEY_WMAAECMA_FEATURE_MODE,true);
        if(SUCCEEDED(hr))hr=property(properties,MFPKEY_WMAAECMA_FEATR_NS,1);
        if(SUCCEEDED(hr))hr=boolean_property(properties,MFPKEY_WMAAECMA_FEATR_AGC,true);
        PROPVARIANT source;PropVariantInit(&source);source.vt=VT_BOOL;source.boolVal=VARIANT_TRUE;
        if(SUCCEEDED(hr))hr=properties->SetValue(MFPKEY_WMAAECMA_DMO_SOURCE_MODE,source);
        properties->Release();
    }
    if(SUCCEEDED(hr))hr=start_reference(capture);
    if(FAILED(hr)){last_error=hr;delete capture;return nullptr;}
    WAVEFORMATEX wave={WAVE_FORMAT_PCM,1,16000,32000,2,16,0};
    DMO_MEDIA_TYPE format={};
    hr=MoInitMediaType(&format,sizeof(wave));
    if(SUCCEEDED(hr)){
        format.majortype=MEDIATYPE_Audio;format.subtype=MEDIASUBTYPE_PCM;
        format.bFixedSizeSamples=TRUE;format.bTemporalCompression=FALSE;
        format.lSampleSize=2;format.formattype=FORMAT_WaveFormatEx;
        memcpy(format.pbFormat,&wave,sizeof(wave));
        hr=capture->object->SetOutputType(0,&format,0);
        MoFreeMediaType(&format);
    }
    if(SUCCEEDED(hr))hr=capture->object->AllocateStreamingResources();
    if(FAILED(hr)){last_error=hr;delete capture;return nullptr;}
    return capture;
}
extern "C" __declspec(dllexport) int fred_aec_read(void* handle,char* bytes,int size){
    if(!handle||!bytes||size<3200)return -1;
    auto capture=(Capture*)handle;capture->buffer->length=0;
    auto hr=capture->fill_silence();if(FAILED(hr)){last_error=hr;return -1;}
    DMO_OUTPUT_DATA_BUFFER output={};output.pBuffer=capture->buffer;
    DWORD status=0;hr=capture->object->ProcessOutput(0,1,&output,&status);
    if(FAILED(hr)){last_error=hr;return -1;}
    int n=(int)capture->buffer->length;
    memcpy(bytes,capture->buffer->data.data(),n);return n;
}
extern "C" __declspec(dllexport) void fred_aec_close(void* handle){delete (Capture*)handle;}
