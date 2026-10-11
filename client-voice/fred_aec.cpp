// Windows Voice Capture DSP: system echo cancellation, noise suppression and AGC.
#include <windows.h>
#include <mediaobj.h>
#include <uuids.h>
#include <dmo.h>
#include <wmcodecdsp.h>
#include <propsys.h>
#include <mmdeviceapi.h>
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
    ~Capture(){if(object){object->FreeStreamingResources();object->Release();}buffer->Release();if(initialized)CoUninitialize();}
};
static HRESULT property(IPropertyStore* properties,REFPROPERTYKEY key,LONG n){
    PROPVARIANT value;PropVariantInit(&value);value.vt=VT_I4;value.lVal=n;
    return properties->SetValue(key,value);
}
extern "C" __declspec(dllexport) void* fred_aec_open() {
    auto capture=new Capture;
    HRESULT hr=CoInitializeEx(nullptr,COINIT_MULTITHREADED);
    if(FAILED(hr)){delete capture;return nullptr;}
    capture->initialized=true;
    hr=CoCreateInstance(CLSID_CWMAudioAEC,nullptr,CLSCTX_INPROC_SERVER,IID_IMediaObject,(void**)&capture->object);
    if(FAILED(hr)){delete capture;return nullptr;}
    IPropertyStore* properties=nullptr;
    hr=capture->object->QueryInterface(IID_IPropertyStore,(void**)&properties);
    if(SUCCEEDED(hr)){
        hr=property(properties,MFPKEY_WMAAECMA_SYSTEM_MODE,SINGLE_CHANNEL_AEC);
        // Default endpoints are resolved by the DSP in source mode.
        properties->Release();
    }
    if(FAILED(hr)){delete capture;return nullptr;}
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
    if(FAILED(hr)){delete capture;return nullptr;}
    return capture;
}
extern "C" __declspec(dllexport) int fred_aec_read(void* handle,char* bytes,int size){
    if(!handle||!bytes||size<3200)return -1;
    auto capture=(Capture*)handle;capture->buffer->length=0;
    DMO_OUTPUT_DATA_BUFFER output={};output.pBuffer=capture->buffer;
    DWORD status=0;auto hr=capture->object->ProcessOutput(0,1,&output,&status);
    if(FAILED(hr))return -1;
    int n=(int)capture->buffer->length;
    memcpy(bytes,capture->buffer->data.data(),n);return n;
}
extern "C" __declspec(dllexport) void fred_aec_close(void* handle){delete (Capture*)handle;}
