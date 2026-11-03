package com.r347h4ck3r.omniforge

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.widget.*
import org.json.JSONObject
import java.io.File
import java.util.concurrent.Executors

class MainActivity:Activity() {
    private val worker=Executors.newSingleThreadExecutor()
    private val prefs by lazy{getSharedPreferences("settings",MODE_PRIVATE)}
    private val agent by lazy{Agent(this)}
    private lateinit var content:LinearLayout
    private lateinit var status:TextView
    private lateinit var chatLog:TextView
    private var page="Chat"
    private var importKind="apk"
    private var busy=false
    private val ink=Color.rgb(230,237,246)
    private val surface=Color.rgb(27,36,51)
    override fun onCreate(savedInstanceState:Bundle?){
        super.onCreate(savedInstanceState)
        page=savedInstanceState?.getString("page") ?: "Chat"
        importKind=savedInstanceState?.getString("importKind") ?: "apk"
        val root=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setBackgroundColor(Color.rgb(16,21,30));setPadding(dp(16),dp(12),dp(16),dp(6))}
        root.setOnApplyWindowInsetsListener { view, insets ->
            val bottom=if(android.os.Build.VERSION.SDK_INT>=30)insets.getInsets(android.view.WindowInsets.Type.systemBars() or android.view.WindowInsets.Type.ime()).bottom else insets.systemWindowInsetBottom
            view.setPadding(dp(16)+insets.systemWindowInsetLeft,dp(12)+insets.systemWindowInsetTop,dp(16)+insets.systemWindowInsetRight,dp(6)+bottom)
            insets
        }
        root.addView(label("OmniForge",28).apply{setTypeface(null,android.graphics.Typeface.BOLD)})
        root.addView(label("ANDROID · YOUR WORKSPACE",11).apply{setTextColor(Color.rgb(130,170,220))})
        val nav=LinearLayout(this)
        listOf("Chat","Projects","Remote","Settings").forEach{title->nav.addView(Button(this).apply{text=title;isAllCaps=false;setOnClickListener{if(!busy){page=title;showPage()}}},LinearLayout.LayoutParams(0,dp(52),1f))}
        root.addView(nav)
        status=label("Ready",12);root.addView(status)
        content=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL}
        root.addView(content,LinearLayout.LayoutParams(-1,0,1f));setContentView(root)
        showPage()
    }
    private fun dp(n:Int)=(n*resources.displayMetrics.density).toInt()
    private fun label(text:String,size:Int=16)=TextView(this).apply{this.text=text;textSize=size.toFloat();setTextColor(ink);setPadding(0,dp(6),0,dp(6))}
    private fun field(hint:String,value:String="",secret:Boolean=false)=EditText(this).apply{
        this.hint=hint;setText(value);setTextColor(ink);setHintTextColor(Color.LTGRAY);textSize=16f
        if(secret)inputType=InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
    }
    private fun button(title:String,action:()->Unit)=Button(this).apply{text=title;isAllCaps=false;setOnClickListener{action()}}
    private fun scroll():LinearLayout{val scroll=ScrollView(this);val column=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL};scroll.addView(column);content.addView(scroll,LinearLayout.LayoutParams(-1,-1));return column}
    private fun failure(e:Throwable){status.text="${e.javaClass.simpleName}: ${e.message}"}
    private fun background(title:String,task:()->String,done:(String)->Unit={status.text=it}){
        if(busy){status.text="Wait for the current task to finish";return};busy=true;status.text=title
        worker.execute{try{val r=task();runOnUiThread{if(!isDestroyed){busy=false;done(r)}}}catch(e:Exception){runOnUiThread{if(!isDestroyed){busy=false;failure(e)}}}catch(e:LinkageError){runOnUiThread{if(!isDestroyed){busy=false;status.text="Native runtime unavailable: ${e.message}"}}}}
    }
    private fun showPage(){content.removeAllViews();when(page){"Projects"->projects();"Remote"->remote();"Settings"->settings();else->chat()}}
    private fun chat(){
        val logScroll=ScrollView(this)
        chatLog=label(prefs.getString("chat","") ?: "",16).apply{setTextIsSelectable(true)}
        logScroll.addView(chatLog);content.addView(logScroll,LinearLayout.LayoutParams(-1,0,1f))
        if(chatLog.text.isEmpty())chatLog.text="Welcome. Import a GGUF model in Settings for offline chat, or configure your private online agent. Use Projects to inspect APKs and edit Android source.\n\nTry /self-test or /files."
        val input=field("Ask OmniForge about Android apps…").apply{maxLines=4}
        content.addView(input)
        content.addView(button("Send"){
            val prompt=input.text.toString().trim();if(prompt.isEmpty()||busy)return@button
            input.setText("");appendChat("\n\nYou: $prompt\n")
            background("Working…",{agent.ask(prompt)}){reply->appendChat("\nOmniForge: $reply");status.text="Ready";logScroll.post{logScroll.fullScroll(View.FOCUS_DOWN)}}
        })
    }
    private fun appendChat(text:String){val existing=prefs.getString("chat","") ?: "";val value=(existing+text).takeLast(150000);prefs.edit().putString("chat",value).apply();chatLog.text=value}
    private fun projects(){
        val col=scroll();col.addView(label("Android projects & APKs",22))
        col.addView(label("Inspect imported APKs locally. Edit source in your private workspace. Full SDK builds and decompilation use the laptop host; inspection does not recover original source.",14))
        col.addView(button("Import APK"){pick("apk")})
        col.addView(button("New Android source project"){
            val sources=mapOf(
                "settings.gradle.kts" to "pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\nrootProject.name=\"MyAndroidApp\"\ninclude(\":app\")\n",
                "app/build.gradle.kts" to "plugins { id(\"com.android.application\") version \"8.7.3\"; id(\"org.jetbrains.kotlin.android\") version \"2.0.21\" }\nrepositories { google(); mavenCentral() }\nandroid { namespace=\"dev.omniforge.generated\"; compileSdk=35; defaultConfig { applicationId=\"dev.omniforge.generated\"; minSdk=26; targetSdk=35; versionCode=1; versionName=\"1.0\" } }\n",
                "app/src/main/AndroidManifest.xml" to "<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\"><application android:label=\"My Android App\"><activity android:name=\".MainActivity\" android:exported=\"true\"><intent-filter><action android:name=\"android.intent.action.MAIN\"/><category android:name=\"android.intent.category.LAUNCHER\"/></intent-filter></activity></application></manifest>",
                "app/src/main/java/dev/omniforge/generated/MainActivity.kt" to "package dev.omniforge.generated\nclass MainActivity : android.app.Activity() { override fun onCreate(state: android.os.Bundle?) { super.onCreate(state);setContentView(android.widget.TextView(this).apply {text=\"Hello from OmniForge\"}) } }\n"
            )
            if(sources.keys.any{Policy.workspace(agent.workspace,it).exists()}){status.text="A project already exists; edit its files below";return@button}
            sources.forEach{(path,text)->Policy.workspace(agent.workspace,path).apply{parentFile?.mkdirs();writeText(text)}}
            status.text="Android source project created. Edit files, then upload to build.";showPage()
        })
        col.addView(button("Upload source project to laptop"){
            background("Uploading Android source workspace…",{
                require(listOf("settings.gradle","settings.gradle.kts").any{File(agent.workspace,it).isFile}){"Create a source project first"}
                val archive=File(cacheDir,"source-project.zip")
                try {
                    var total=0L
                    java.util.zip.ZipOutputStream(archive.outputStream()).use{zip->agent.workspace.walkTopDown().filter{it.isFile && it.extension !in listOf("apk","gguf","zip")}.take(10000).forEach{f->
                        total+=f.length();require(total<=256L*1024*1024){"Source project too large"};zip.putNextEntry(java.util.zip.ZipEntry(f.relativeTo(agent.workspace).invariantSeparatorsPath));f.inputStream().use{it.copyTo(zip)};zip.closeEntry()
                    }}
                    val base=java.net.URI(Policy.https(prefs.getString("hostBase","https://gaminglaptop-1.tail54e01b.ts.net/android-api") ?: ""))
                    val url=java.net.URI(base.scheme,null,base.host,base.port,base.path.trimEnd('/')+"/v1/android/project-upload","name=source-project.zip",null).toString()
                    val result=JSONObject(Net.upload(url,archive,prefs.getString("token","") ?: ""))
                    prefs.edit().putString("lastHostPath",result.getString("host_path")).apply()
                    "Source uploaded. Open Host Android workbench → Build source."
                }finally{archive.delete()}
            })
        })
        col.addView(button("Import source file"){pick("source")})
        col.addView(button("New source file"){
            val name=field("Relative path, e.g. app/MainActivity.kt")
            AlertDialog.Builder(this).setTitle("Create workspace file").setView(name).setPositiveButton("Create"){_,_->try{val f=Policy.workspace(agent.workspace,name.text.toString());require(!f.exists()){ "File already exists" };f.parentFile?.mkdirs();f.writeText("");edit(f)}catch(e:Exception){failure(e)}}.setNegativeButton("Cancel",null).show()
        })
        col.addView(button("Upload APK to laptop"){
            val apks=agent.workspace.listFiles()?.filter{it.extension.equals("apk",true)} ?: emptyList()
            if(apks.isEmpty()){status.text="Import an APK first";return@button}
            AlertDialog.Builder(this).setTitle("Upload authorized APK privately").setItems(apks.map{it.name}.toTypedArray()){_,index->
                background("Uploading APK to private host…",{
                    val base=java.net.URI(Policy.https(prefs.getString("hostBase","https://gaminglaptop-1.tail54e01b.ts.net/android-api") ?: ""))
                    val endpoint=java.net.URI(base.scheme,null,base.host,base.port,base.path.trimEnd('/')+"/v1/android/upload","name="+apks[index].name,null).toString()
                    val result=JSONObject(Net.upload(endpoint,apks[index],prefs.getString("token","") ?: ""))
                    prefs.edit().putString("lastHostPath",result.getString("host_path")).apply()
                    "Uploaded to ${result.getString("host_path")}. Open Host Android workbench to inspect or decompile."
                })
            }.setNegativeButton("Cancel",null).show()
        })
        col.addView(button("Decode / rebuild APK resources"){
            val path=field("Host APK or decoded resource directory",prefs.getString("lastHostPath","") ?: "")
            AlertDialog.Builder(this).setTitle("Resource and smali workbench").setMessage("Decode an uploaded APK, edit its decoded resources on the laptop, then rebuild and sign. This does not recover its original Gradle source.").setView(path)
                .setPositiveButton("Decode"){_,_->hostTask("decode",path.text.toString())}.setNeutralButton("Rebuild"){_,_->hostTask("rebuild",path.text.toString())}.setNegativeButton("Cancel",null).show()
        })
        col.addView(button("Host Android workbench") { hostDialog() })
        col.addView(button("Install last built APK") {val exported=File(filesDir,"exports/built.apk");val generated=File(agent.workspace,"BuildOutputs/built.apk");val f=if(generated.isFile && generated.lastModified()>exported.lastModified())generated else exported;if(f.isFile){if(f==generated){exported.parentFile?.mkdirs();generated.copyTo(exported,true)};Updater.install(this,exported)}else status.text="Download a successful host build first"})
        col.addView(label("Workspace",20))
        val files=agent.workspace.walkTopDown().filter{it.isFile}.take(200).toList()
        if(files.isEmpty())col.addView(label("No files yet. Import an APK or create source.",14))
        files.forEach{f->col.addView(button(f.relativeTo(agent.workspace).path){if(f.extension.equals("apk",true))inspect(f)else edit(f)})}
    }
    private fun edit(file:File){
        if(file.length()>500000){status.text="File exceeds the editor's text size budget";return}
        val editor=field("Source",file.readText()).apply{gravity=Gravity.TOP;minLines=12;typeface=android.graphics.Typeface.MONOSPACE;setHorizontallyScrolling(true)}
        AlertDialog.Builder(this).setTitle(file.name).setView(editor).setPositiveButton("Save"){_,_->try{file.writeText(editor.text.toString());status.text="Saved ${file.name}"}catch(e:Exception){failure(e)}}.setNegativeButton("Cancel",null).show()
    }
    private fun inspect(file:File){background("Inspecting ${file.name}…",{ApkInspector.inspect(this,file).toString(2)}){result->
        status.text="APK inspected locally"
        val text=label(result,13).apply{setTextIsSelectable(true)};val s=ScrollView(this);s.addView(text)
        AlertDialog.Builder(this).setTitle(file.name).setView(s).setPositiveButton("Save report"){_,_->val out=File(filesDir,"exports/${file.name}.json");out.parentFile?.mkdirs();out.writeText(result);status.text="Report saved; use Share to export";share(out,"application/json")}.setNegativeButton("Close",null).show()
    }}
    private fun share(file:File,type:String){val uri=androidx.core.content.FileProvider.getUriForFile(this,"$packageName.files",file);startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).setType(type).putExtra(Intent.EXTRA_STREAM,uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION),"Export"))}
    private fun hostDialog(){
        val col=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(dp(16),0,dp(16),0)}
        col.addView(label("Runs Android SDK/JADX tools on your private laptop. Paths refer to its authorized workspace. API token and endpoint come from Settings.",14))
        val path=field("Host path, e.g. android-project",prefs.getString("lastHostPath","") ?: "");col.addView(path)
        AlertDialog.Builder(this).setTitle("Android host tools").setView(col).setPositiveButton("Build source"){_,_->hostTask("build",path.text.toString())}.setNeutralButton("Inspect APK"){_,_->hostTask("inspect",path.text.toString())}.setNegativeButton("Decompile APK"){_,_->hostTask("decompile",path.text.toString())}.show()
    }
    private fun hostTask(action:String,path:String){background("Running host $action…",{
        val base=Policy.https(prefs.getString("hostBase","https://gaminglaptop-1.tail54e01b.ts.net/android-api") ?: "");val u=java.net.URI(base)
        val endpoint=java.net.URI(u.scheme,null,u.host,u.port,u.path.trimEnd('/')+"/v1/android/workbench",null,null).toString()
        Net.request(endpoint,JSONObject().put("action",action).put("path",path).toString(),prefs.getString("token","") ?: "")
    }){r->val text=label(r,13).apply{setTextIsSelectable(true)};val s=ScrollView(this);s.addView(text);val dialog=AlertDialog.Builder(this).setTitle("Host result").setView(s).setPositiveButton("Close",null)
        val artifacts=try{JSONObject(r).optJSONArray("artifacts")}catch(e:Exception){null}
        if(artifacts!=null && artifacts.length()>0)dialog.setNeutralButton("Download built APK"){_,_->downloadBuilt(artifacts.getJSONObject(0))}
        dialog.show();status.text="Host task finished; read result for build status"}}
    private fun downloadBuilt(artifact:JSONObject){
        background("Downloading built APK privately…",{
            val base=java.net.URI(Policy.https(prefs.getString("hostBase","https://gaminglaptop-1.tail54e01b.ts.net/android-api") ?: ""))
            val address=java.net.URI(base.scheme,null,base.host,base.port,base.path.trimEnd('/')+"/v1/android/artifact","path="+artifact.getString("path"),null).toString()
            val out=File(filesDir,"exports/built.apk").apply{parentFile?.mkdirs()}
            Net.download(address,out,artifact.getString("sha256"),512L*1024*1024,prefs.getString("token","") ?: "")
            out.path
        }){path->status.text="Built APK downloaded and hash verified"
            AlertDialog.Builder(this).setTitle("Built APK ready").setMessage("Install this Android app or export its APK?")
                .setPositiveButton("Install"){_,_->Updater.install(this,File(path))}.setNeutralButton("Share"){_,_->share(File(path),"application/vnd.android.package-archive")}.setNegativeButton("Later",null).show()}
    }
    private fun remote(){
        val col=scroll();col.addView(label("Private remote access",22));col.addView(label("Connect Tailscale on this tablet first. Both sessions open full-screen and stay in landscape.",14))
        val desktop=field("Desktop HTTPS URL",prefs.getString("desktop","https://gaminglaptop-1.tail54e01b.ts.net:8443/vnc.html?autoconnect=1&resize=scale&path=websockify") ?: "")
        val terminal=field("Terminal HTTPS URL",prefs.getString("terminal","https://gaminglaptop-1.tail54e01b.ts.net/terminal/") ?: "")
        col.addView(desktop);col.addView(button("Open desktop") {openRemote("desktop",desktop.text.toString())})
        col.addView(terminal);col.addView(button("Open terminal") {openRemote("terminal",terminal.text.toString())})
        col.addView(label("Use the remote service's sign-in prompt. Passwords are never embedded in the public update source.",14))
    }
    private fun openRemote(key:String,url:String){try{val address=Policy.https(url);prefs.edit().putString(key,address).apply();startActivity(Intent(this,RemoteActivity::class.java).putExtra("url",address))}catch(e:Exception){failure(e)}}
    private fun settings(){
        val col=scroll();col.addView(label("Models & connection",22))
        val offline=Switch(this).apply{text="Offline GGUF mode";setTextColor(ink);isChecked=prefs.getBoolean("offline",true)};col.addView(offline)
        col.addView(label("Import a small instruction-tuned GGUF (start with 0.5B Q4). Model files remain private on this tablet. Larger models may exceed its memory.",14))
        col.addView(button("Import GGUF model"){pick("model")})
        col.addView(label("Imported model: "+File(filesDir,"models/model.gguf").let{if(it.isFile)"${it.length()/1024/1024} MiB" else "none"},13))
        val endpoint=field("Private AI address (HTTPS)",prefs.getString("endpoint","https://gaminglaptop-1.tail54e01b.ts.net/android-api/v1/android/completions") ?: "")
        val hostBase=field("Android host base URL",prefs.getString("hostBase","https://gaminglaptop-1.tail54e01b.ts.net/android-api") ?: "")
        val model=field("Online model name",prefs.getString("model","qwen2.5-coder:1.5b") ?: "")
        val token=field("Private agent API token",prefs.getString("token","") ?: "",true)
        val edits=Switch(this).apply{text="Allow agent edits inside app workspace";setTextColor(ink);isChecked=prefs.getBoolean("edits",false)}
        listOf(endpoint,hostBase,model,token,edits).forEach{col.addView(it)}
        col.addView(button("Save settings") {try{if(!offline.isChecked)Policy.https(endpoint.text.toString());prefs.edit().putBoolean("offline",offline.isChecked).putBoolean("edits",edits.isChecked).putString("endpoint",endpoint.text.toString().trim()).putString("hostBase",Policy.https(hostBase.text.toString())).putString("model",model.text.toString().trim()).putString("token",token.text.toString()).apply();status.text="Settings saved"}catch(e:Exception){failure(e)}})
        col.addView(label("Diagnostics & updates",22))
        col.addView(button("Run self-test"){background("Checking…",{agent.ask("/self-test")})})
        col.addView(button("Check APK updates"){checkUpdate()})
        col.addView(button("Install downloaded update") {val f=File(cacheDir,"updates/OmniForge.apk");if(f.isFile)Updater.install(this,f)else status.text="Check for updates first"})
        col.addView(button("Clear chat history"){AlertDialog.Builder(this).setMessage("Delete this tablet's chat history?").setPositiveButton("Delete"){_,_->prefs.edit().remove("chat").apply();File(filesDir,"conversation.json").delete();status.text="Chat deleted"}.setNegativeButton("Cancel",null).show()})
        col.addView(label("Android app tools · APK edition\nRepository: R347H4CK3R/OmniForge\nSource: ${Updater.CATALOG}",12).apply{setTextIsSelectable(true)})
    }
    private fun checkUpdate(){var release:JSONObject?=null;background("Checking update source…",{release=Updater.check(this);release.toString()}){
        val r=release ?: return@background
        AlertDialog.Builder(this).setTitle("OmniForge ${r.optString("versionName")}").setMessage("Download and verify this APK? Android will ask before installation.").setPositiveButton("Download"){_,_->background("Downloading and verifying update…",{Updater.fetch(this,r).path}){path->status.text="APK verified";Updater.install(this,File(path))}}.setNegativeButton("Cancel",null).show()
    }}
    private fun pick(kind:String){if(busy)return;importKind=kind;val intent=Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*");startActivityForResult(intent,40)}
    @Deprecated("Activity result API used for minimal native dependencies")
    override fun onActivityResult(requestCode:Int,resultCode:Int,data:Intent?){super.onActivityResult(requestCode,resultCode,data);if(requestCode!=40||resultCode!=RESULT_OK)return;val uri=data?.data ?: return;val kind=importKind
        background("Importing file…",{
            val name=contentResolver.query(uri,arrayOf(android.provider.OpenableColumns.DISPLAY_NAME),null,null,null)?.use{if(it.moveToFirst())it.getString(0) else null} ?: "imported"
            val clean=name.substringAfterLast('/').substringAfterLast('\\');require(clean.isNotBlank() && clean!="." && clean!=".."){"Invalid filename"}
            val out=if(kind=="model")File(filesDir,"models/model.gguf")else Policy.workspace(agent.workspace,clean)
            val temp=File(cacheDir,"import.tmp");var total=0L
            try{contentResolver.openInputStream(uri)?.use{input->temp.outputStream().use{output->val b=ByteArray(65536);while(true){val n=input.read(b);if(n<0)break;total+=n;require(total<=if(kind=="model")3L*1024*1024*1024 else 512L*1024*1024){"Import exceeds size budget"};output.write(b,0,n)}}} ?: error("Cannot open file")
                if(kind=="model"){val magic=temp.inputStream().use{val h=ByteArray(4);it.read(h);String(h)};require(magic=="GGUF"){"Not a GGUF model"}}
                if(kind=="apk")ApkInspector.inspect(this,temp)
                out.parentFile?.mkdirs();temp.copyTo(out,true);out.path
            }finally{temp.delete()}
        }){path->status.text="Imported ${File(path).name}";if(kind=="apk")inspect(File(path))else showPage()}
    }
    override fun onSaveInstanceState(outState:Bundle){outState.putString("page",page);outState.putString("importKind",importKind);super.onSaveInstanceState(outState)}
    override fun onDestroy(){worker.shutdown();super.onDestroy()}
}
