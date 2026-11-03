#include <jni.h>
#include <string>
#include <vector>
#include <mutex>
#include <algorithm>
#include "llama.h"
static std::mutex model_mutex;
static std::string utf8(JNIEnv *env, jstring value) {
    const char *data=env->GetStringUTFChars(value,nullptr);std::string result(data);env->ReleaseStringUTFChars(value,data);return result;
}
extern "C" JNIEXPORT jstring JNICALL Java_com_r347h4ck3r_omniforge_NativeModel_generate(JNIEnv *env,jobject,jstring path,jstring prompt,jint threads) {
    std::lock_guard<std::mutex> guard(model_mutex);
    llama_backend_init();
    auto mp=llama_model_default_params();mp.n_gpu_layers=0;
    auto model=llama_model_load_from_file(utf8(env,path).c_str(),mp);
    if(!model){env->ThrowNew(env->FindClass("java/lang/IllegalStateException"),"GGUF model failed to load. Try a compatible small model.");return nullptr;}
    auto cp=llama_context_default_params();cp.n_ctx=8192;cp.n_batch=512;cp.n_threads=std::max(1,std::min(4,(int)threads));cp.n_threads_batch=cp.n_threads;
    auto ctx=llama_init_from_model(model,cp);
    if(!ctx){llama_model_free(model);env->ThrowNew(env->FindClass("java/lang/IllegalStateException"),"Insufficient memory for model context");return nullptr;}
    auto vocab=llama_model_get_vocab(model);
    std::string input=utf8(env,prompt);
    llama_chat_message msg={"user",input.c_str()};
    auto tmpl=llama_model_chat_template(model,nullptr);
    int needed=llama_chat_apply_template(tmpl,&msg,1,true,nullptr,0);
    if(needed>0){std::vector<char> formatted(needed+1);llama_chat_apply_template(tmpl,&msg,1,true,formatted.data(),formatted.size());input.assign(formatted.data(),needed);}
    int n=-llama_tokenize(vocab,input.c_str(),input.size(),nullptr,0,true,true);
    std::string output;
    if(n<=0 || n>7168){output="Prompt exceeds offline context. Start a shorter conversation.";}
    else {
        std::vector<llama_token> tokens(n);llama_tokenize(vocab,input.c_str(),input.size(),tokens.data(),n,true,true);
        auto params=llama_sampler_chain_default_params();auto sampler=llama_sampler_chain_init(params);
        llama_sampler_chain_add(sampler,llama_sampler_init_greedy());
        bool ok=true;
        for(int start=0;start<n;start+=512){int count=std::min(512,n-start);auto batch=llama_batch_get_one(tokens.data()+start,count);if(llama_decode(ctx,batch)!=0){ok=false;break;}}
        for(int i=0;ok && i<1024;i++){
            llama_token token=llama_sampler_sample(sampler,ctx,-1);
            if(llama_vocab_is_eog(vocab,token))break;
            char piece[512];int count=llama_token_to_piece(vocab,token,piece,sizeof(piece),0,true);
            if(count>0)output.append(piece,count);
            auto batch=llama_batch_get_one(&token,1);if(llama_decode(ctx,batch)!=0){ok=false;break;}
        }
        llama_sampler_free(sampler);
        if(!ok && output.empty())output="Model evaluation failed.";
    }
    llama_free(ctx);llama_model_free(model);
    // Construct Java text from UTF-8 bytes, avoiding JNI modified-UTF8 corruption for emoji.
    jbyteArray bytes=env->NewByteArray(output.size());env->SetByteArrayRegion(bytes,0,output.size(),reinterpret_cast<const jbyte*>(output.data()));
    jclass cls=env->FindClass("java/lang/String");auto ctor=env->GetMethodID(cls,"<init>","([BLjava/lang/String;)V");
    return (jstring)env->NewObject(cls,ctor,bytes,env->NewStringUTF("UTF-8"));
}
