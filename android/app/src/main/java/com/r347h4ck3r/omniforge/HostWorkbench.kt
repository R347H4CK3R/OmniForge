package com.r347h4ck3r.omniforge
import android.content.Context
import org.json.JSONObject
import java.io.File
import java.net.URI
import java.util.zip.ZipOutputStream
import java.util.zip.ZipEntry

/** Real host actions exposed to the local agent, with file writes controlled by its setting. */
class HostWorkbench(private val context:Context,private val workspace:File){
    private val prefs=context.getSharedPreferences("settings",Context.MODE_PRIVATE)
    private fun url(path:String,query:String?=null):String{
        val base=URI(Policy.https(prefs.getString("hostBase","https://gaminglaptop-1.tail54e01b.ts.net/android-api") ?: ""))
        return URI(base.scheme,null,base.host,base.port,base.path.trimEnd('/')+"/v1/android/"+path,query,null).toString()
    }
    private fun token()=prefs.getString("token","") ?: ""
    fun action(action:String,args:JSONObject):JSONObject{
        if(action=="write_file")require(prefs.getBoolean("edits",false)){"Enable agent workspace edits in Settings first"}
        val body=JSONObject(args.toString()).put("action",action)
        return JSONObject(Net.request(url("workbench"),body.toString(),token()))
    }
    fun analyze(path:String,operation:String):JSONObject{
        require(operation in listOf("inspect","decompile","decode")){"Unsupported APK analysis action"}
        val file=Policy.workspace(workspace,path);require(file.extension.equals("apk",true)){"Select an APK"}
        val result=JSONObject(Net.upload(url("upload","name="+file.name),file,token()))
        return action(operation,JSONObject().put("path",result.getString("host_path")))
    }
    fun buildSource():JSONObject{
        require(listOf("settings.gradle","settings.gradle.kts").any{File(workspace,it).isFile}){"Create Android Gradle source in Projects first"}
        val archive=File(context.cacheDir,"agent-source.zip")
        try {
            var total=0L;var count=0
            ZipOutputStream(archive.outputStream()).use{zip->workspace.walkTopDown().filter{it.isFile && it.extension !in listOf("apk","gguf","zip")}.forEach{file->
                require(++count<=10000){"Too many project files"};total+=file.length();require(total<=256L*1024*1024){"Project exceeds upload budget"}
                zip.putNextEntry(ZipEntry(file.relativeTo(workspace).invariantSeparatorsPath));file.inputStream().use{it.copyTo(zip)};zip.closeEntry()
            }}
            val uploaded=JSONObject(Net.upload(url("project-upload","name=agent-source.zip"),archive,token()))
            val result=action("build",JSONObject().put("path",uploaded.getString("host_path")))
            val artifacts=result.optJSONArray("artifacts")
            if(result.optBoolean("built") && artifacts!=null && artifacts.length()>0){
                val artifact=artifacts.getJSONObject(0)
                val out=File(workspace,"BuildOutputs/built.apk").apply{parentFile?.mkdirs()}
                Net.download(url("artifact","path="+artifact.getString("path")),out,artifact.getString("sha256"),512L*1024*1024,token())
                result.put("local_apk",out.relativeTo(workspace).invariantSeparatorsPath)
            }
            return result
        }finally{archive.delete()}
    }
}
