#include "fred_voice.h"
#include "whisper.h"
#include "ggml-backend.h"
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <cstring>
#include <deque>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace {
constexpr int RATE = 16000;
constexpr int MAX_SESSION = 120 * RATE;
constexpr int MAX_SEGMENT = 18 * RATE;
constexpr int SILENCE = 24 * RATE / 16; // 1.5 s ends a phrase, never sends a chat.
constexpr size_t MAX_JOBS = 8;

std::string clean(std::string text) {
    const auto first = text.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return "";
    text = text.substr(first, text.find_last_not_of(" \t\r\n") - first + 1);
    if (text.size() > 32000) {size_t end=32000;while(end>0 && (static_cast<unsigned char>(text[end])&0xc0)==0x80)--end;text.resize(end);}
    return text;
}
std::string quote(const std::string& text) {
    std::string result = "\"";
    for (unsigned char c : text) {
        if (c == '"' || c == '\\') { result += '\\'; result += char(c); }
        else if (c == '\n') result += "\\n";
        else if (c == '\r') result += "\\r";
        else if (c == '\t') result += "\\t";
        else if (c >= 32) result += char(c);
    }
    return result + '"';
}
struct Job { int id; std::vector<float> audio; bool final; unsigned epoch=0; };
struct Turn {int id;int speech_id;std::string text;};

// All audio/recognition buffers are session-local and never written to disk.
class Voice {
public:
    std::mutex mutex;
    std::condition_variable changed;
    std::atomic<bool> aborted{false};
    std::thread worker;
    std::string model, backend_dir, phase="loading", message="Chargement de la dictée française…";
    std::string committed, provisional;
    std::vector<float> audio, preroll;
    std::deque<Job> finals;
    Job partial{0, {}, false};
    bool partial_pending=false, speech=false, stopping=false, processing=false;
    int threads, segment=0, quiet=0, seen=0, last_partial=0, provisional_id=-1, last_final_id=-1;
    unsigned revision=0;
    double inference_seconds=0;
    bool conversation=false,capture_paused=false;
    unsigned capture_epoch=0;
    int turn_id=0;
    std::deque<Turn> turns;
    Voice(const char* path, const char* backends, int count, bool talking=false):model(path),backend_dir(backends?backends:""),threads(std::clamp(count,1,4)),conversation(talking) {
        worker=std::thread([this]{run();});
    }
    ~Voice() { cancel(); if(worker.joinable()) worker.join(); }
    void pause_capture(bool paused) {
        std::lock_guard<std::mutex> lock(mutex);
        if(!conversation || capture_paused==paused)return;
        capture_paused=paused;++capture_epoch;
        audio.clear();preroll.clear();finals.clear();partial.audio.clear();partial_pending=false;
        speech=false;quiet=0;last_partial=0;provisional.clear();provisional_id=-1;++segment;++revision;
    }
    void ack(int id){std::lock_guard<std::mutex> lock(mutex);while(!turns.empty()&&turns.front().id<=id)turns.pop_front();}
    void cancel() { aborted=true; {std::lock_guard<std::mutex> lock(mutex);stopping=true;phase="cancelling";++revision;} changed.notify_all(); }
    void end_phrase() { // mutex held
        if(speech && audio.size() >= RATE/4) {
            if(finals.size()+(conversation?turns.size():0)>=MAX_JOBS) { phase="error";message=conversation?"La reconnaissance ne suit plus. Terminez puis recommencez avec des phrases plus courtes.":"La dictée ne suit plus. Terminez puis recommencez avec des phrases plus courtes.";aborted=true; }
            else finals.push_back({segment, std::move(audio), true,capture_epoch});
        }
        audio.clear(); speech=false;quiet=0;last_partial=0;++segment;
        partial_pending=false;partial.audio.clear();changed.notify_all();
    }
    void feed(const int16_t* samples,int count) {
        if(!samples || count<=0 || count>RATE) return;
        std::lock_guard<std::mutex> lock(mutex);
        if(phase!="listening" || stopping || aborted || capture_paused) return;
        const int limit=conversation?900*RATE:MAX_SESSION;
        count=std::min(count,limit-seen);
        if(count<=0) return;
        seen+=count;
        double energy=0;for(int i=0;i<count;++i) energy+=double(samples[i])*samples[i];
        const bool loud=std::sqrt(energy/count)>=160.0;
        if(!speech && loud) {speech=true;audio=std::move(preroll);preroll.clear();}
        if(speech) {
            for(int i=0;i<count;++i) audio.push_back(float(samples[i])/32768.f);
            quiet=loud?0:quiet+count;
            if(quiet>=SILENCE || audio.size()>=MAX_SEGMENT) end_phrase();
            else if(audio.size()>=3*RATE && int(audio.size())-last_partial>=3*RATE) {
                partial={segment,audio,false,capture_epoch};partial_pending=true;last_partial=int(audio.size());changed.notify_all();
            }
        } else {
            for(int i=0;i<count;++i) preroll.push_back(float(samples[i])/32768.f);
            if(preroll.size()>RATE/4) preroll.erase(preroll.begin(),preroll.end()-RATE/4);
        }
        if(seen>=limit) {stopping=true;phase="finishing";message=conversation?"Conversation terminée après quinze minutes.":"Limite de deux minutes atteinte. Finalisation du texte…";end_phrase();}
        ++revision;
    }
    void stop() {
        std::lock_guard<std::mutex> lock(mutex);
        if(phase!="loading" && phase!="listening") return;
        stopping=true;phase="finishing";message="Microphone fermé. Finalisation du texte…";end_phrase();++revision;changed.notify_all();
    }
    std::string status() {
        std::lock_guard<std::mutex> lock(mutex);
        const auto text=clean(committed+(provisional.empty()?"":" "+provisional));
        std::ostringstream s;
        s<<"{\"phase\":"<<quote(phase)<<",\"message\":"<<quote(message)<<",\"text\":"<<quote(text)
         <<",\"seconds\":"<<seen/RATE<<",\"revision\":"<<revision<<",\"pending\":"<<finals.size()
         <<",\"processing\":"<<(processing?"true":"false")<<",\"inference_seconds\":"<<inference_seconds;
        if(conversation){
            s<<",\"speech_id\":"<<segment+(speech?1:0)<<",\"speaking\":"<<(speech&&quiet<RATE/4?"true":"false")
             <<",\"partial\":"<<quote(provisional)<<",\"partial_speech_id\":"<<provisional_id+1<<",\"turns\":[";
            bool first=true;for(const auto& turn:turns){if(!first)s<<',';first=false;s<<"{\"id\":"<<turn.id<<",\"speech_id\":"<<turn.speech_id<<",\"text\":"<<quote(turn.text)<<'}';}s<<']';
        }
        s<<'}';
        return s.str();
    }
    static bool abort_callback(void* userdata) {return static_cast<Voice*>(userdata)->aborted.load();}
    static void no_log(enum ggml_log_level,const char*,void*) {}
    void run() {
        whisper_context* ctx=nullptr;
        try {
            whisper_log_set(no_log,nullptr);
            if(!backend_dir.empty()) ggml_backend_load_all_from_path(backend_dir.c_str());
            auto setup=whisper_context_default_params();setup.use_gpu=false;
            ctx=whisper_init_from_file_with_params(model.c_str(),setup);
            if(!ctx || std::strcmp(whisper_model_type_readable(ctx),"small")!=0 || !whisper_is_multilingual(ctx))
                throw std::runtime_error("Le modèle Whisper Small multilingue est invalide. Réinstallez la dictée.");
            {std::lock_guard<std::mutex> lock(mutex);if(!stopping && !aborted){phase="listening";message="Microphone ouvert. Parlez, puis terminez la dictée.";}++revision;}
            while(!aborted) {
                Job job;
                {
                    std::unique_lock<std::mutex> lock(mutex);
                    changed.wait(lock,[this]{return aborted || stopping || !finals.empty() || partial_pending;});
                    if(aborted) break;
                    if(!finals.empty()) {job=std::move(finals.front());finals.pop_front();}
                    else if(stopping) break;
                    else {job=std::move(partial);partial_pending=false;}
                    processing=true;
                }
                auto options=whisper_full_default_params(WHISPER_SAMPLING_GREEDY);
                options.n_threads=threads;options.language="fr";options.translate=false;options.detect_language=false;
                options.no_context=true;options.no_timestamps=true;options.single_segment=true;
                options.print_progress=false;options.print_realtime=false;options.print_timestamps=false;options.print_special=false;
                options.suppress_blank=true;options.suppress_nst=true;
                // Short previews use a smaller audio context; the authoritative
                // final pass always retains the model's complete 30 s context.
                if(!job.final)options.audio_ctx=std::min(whisper_n_audio_ctx(ctx),std::max(300,int(job.audio.size()*50/RATE)+150));
                options.abort_callback=abort_callback;options.abort_callback_user_data=this;
                const auto started=std::chrono::steady_clock::now();
                // Manual stop can end a very short word; Whisper needs >= 1 s.
                if(job.audio.size()<RATE)job.audio.resize(RATE,0.f);
                const int result=whisper_full(ctx,options,job.audio.data(),int(job.audio.size()));
                if(result!=0 && !aborted) throw std::runtime_error("La transcription a échoué. Réessayez la dictée.");
                std::string text;
                if(!aborted) for(int i=0;i<whisper_full_n_segments(ctx);++i) text+=whisper_full_get_segment_text(ctx,i);
                text=clean(text);
                {
                    std::lock_guard<std::mutex> lock(mutex);
                    processing=false;inference_seconds+=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
                    if(!aborted && (!conversation || job.epoch==capture_epoch)) {
                        if(job.final) {if(!text.empty()){if(conversation){if(turns.size()>=MAX_JOBS)throw std::runtime_error("Trop de phrases en attente. Raccrochez puis recommencez.");turns.push_back({++turn_id,job.id+1,text});}else committed=clean(committed+" "+text);}last_final_id=job.id;if(job.id==provisional_id){provisional.clear();provisional_id=-1;}}
                        else if(job.id>last_final_id && job.id>=provisional_id) {provisional=text;provisional_id=job.id;}
                    }
                    ++revision;
                }
            }
        } catch(const std::exception& error) {std::lock_guard<std::mutex> lock(mutex);phase="error";message=error.what();}
          catch(...) {std::lock_guard<std::mutex> lock(mutex);phase="error";message="Le moteur de dictée s’est arrêté. Réessayez.";}
        if(ctx) whisper_free(ctx);
        std::lock_guard<std::mutex> lock(mutex);
        if(phase!="error") {phase=aborted?"cancelled":"ready";message=aborted?"Dictée annulée.":"Texte prêt. Corrigez-le puis envoyez votre message.";}
        if(aborted && phase!="error") {committed.clear();provisional.clear();}
        processing=false;audio.clear();audio.shrink_to_fit();preroll.clear();preroll.shrink_to_fit();finals.clear();partial.audio.clear();partial.audio.shrink_to_fit();++revision;
    }
};
}

void* fred_voice_create(const char* model,const char* backends,int threads) {
    if(!model || !*model) return nullptr;
    try {return new Voice(model,backends,threads);} catch(...) {return nullptr;}
}
void* fred_voice_create_conversation(const char* model,const char* backends,int threads) {
    if(!model || !*model)return nullptr;
    try{return new Voice(model,backends,threads,true);}catch(...){return nullptr;}
}
void fred_voice_pause_capture(void* handle,bool paused){if(handle)static_cast<Voice*>(handle)->pause_capture(paused);}
void fred_voice_ack(void* handle,int turn){if(handle)static_cast<Voice*>(handle)->ack(turn);}
void fred_voice_feed(void* handle,const int16_t* audio,int count) {if(handle) static_cast<Voice*>(handle)->feed(audio,count);}
void fred_voice_stop(void* handle) {if(handle) static_cast<Voice*>(handle)->stop();}
void fred_voice_cancel(void* handle) {if(handle) static_cast<Voice*>(handle)->cancel();}
int fred_voice_status(void* handle,char* output,int capacity) {
    if(!handle || !output || capacity<2) return 0;
    auto text=static_cast<Voice*>(handle)->status();
    if(int(text.size())>=capacity) return -1;
    std::memcpy(output,text.c_str(),text.size()+1);return int(text.size());
}
void fred_voice_destroy(void* handle) {delete static_cast<Voice*>(handle);}

