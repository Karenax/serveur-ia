#include "fred_voice.h"
#include <jni.h>
#include <vector>
#include <string>
#include <thread>
#include <algorithm>
extern "C" JNIEXPORT jlong JNICALL Java_net_karenax_fred_LocalVoice_nativeCreate(JNIEnv* env,jclass,jstring path,jstring backends) {
    const char* text=env->GetStringUTFChars(path,nullptr);
    const char* directory=env->GetStringUTFChars(backends,nullptr);
    const int threads=std::clamp(int(std::thread::hardware_concurrency()),1,4);
    void* handle=fred_voice_create(text,directory,threads);
    env->ReleaseStringUTFChars(path,text);env->ReleaseStringUTFChars(backends,directory);return reinterpret_cast<jlong>(handle);
}
extern "C" JNIEXPORT void JNICALL Java_net_karenax_fred_LocalVoice_nativeFeed(JNIEnv* env,jclass,jlong handle,jshortArray samples,jint count) {
    if(count<=0 || count>16000 || count>env->GetArrayLength(samples)) return;
    std::vector<int16_t> copy(count);env->GetShortArrayRegion(samples,0,count,reinterpret_cast<jshort*>(copy.data()));
    if(!env->ExceptionCheck()) fred_voice_feed(reinterpret_cast<void*>(handle),copy.data(),count);
}
extern "C" JNIEXPORT jstring JNICALL Java_net_karenax_fred_LocalVoice_nativeStatus(JNIEnv* env,jclass,jlong handle) {
    char buffer[131072];if(fred_voice_status(reinterpret_cast<void*>(handle),buffer,sizeof(buffer))<=0) return env->NewStringUTF("{}");
    // UTF-8 transcripts can contain non-BMP characters; use Java's UTF-8 decoder.
    const auto length=static_cast<jsize>(std::char_traits<char>::length(buffer));
    jbyteArray bytes=env->NewByteArray(length);env->SetByteArrayRegion(bytes,0,length,reinterpret_cast<const jbyte*>(buffer));
    jclass type=env->FindClass("java/lang/String");jmethodID init=env->GetMethodID(type,"<init>","([BLjava/lang/String;)V");
    jstring encoding=env->NewStringUTF("UTF-8");return static_cast<jstring>(env->NewObject(type,init,bytes,encoding));
}
extern "C" JNIEXPORT void JNICALL Java_net_karenax_fred_LocalVoice_nativeStop(JNIEnv*,jclass,jlong handle) {fred_voice_stop(reinterpret_cast<void*>(handle));}
extern "C" JNIEXPORT void JNICALL Java_net_karenax_fred_LocalVoice_nativeCancel(JNIEnv*,jclass,jlong handle) {fred_voice_cancel(reinterpret_cast<void*>(handle));}
extern "C" JNIEXPORT void JNICALL Java_net_karenax_fred_LocalVoice_nativeDestroy(JNIEnv*,jclass,jlong handle) {fred_voice_destroy(reinterpret_cast<void*>(handle));}
