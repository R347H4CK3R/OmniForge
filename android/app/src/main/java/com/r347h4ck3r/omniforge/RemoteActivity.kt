package com.r347h4ck3r.omniforge
import android.app.Activity
import android.os.Bundle
import android.graphics.Color
import android.view.Gravity
import android.view.View
import android.view.WindowInsets
import android.webkit.WebView
import android.webkit.WebViewClient
import android.webkit.WebResourceRequest
import android.webkit.WebResourceError
import android.webkit.SslErrorHandler
import android.net.http.SslError
import android.widget.Button
import android.widget.FrameLayout
import android.widget.Toast

class RemoteActivity: Activity() {
    private lateinit var web: WebView
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val address=try{Policy.https(intent.getStringExtra("url") ?: "")}catch(e:Exception){Toast.makeText(this,e.message,Toast.LENGTH_LONG).show();finish();return}
        val root=FrameLayout(this);root.setBackgroundColor(Color.BLACK)
        web=WebView(this);web.setBackgroundColor(Color.BLACK)
        web.settings.javaScriptEnabled=true;web.settings.domStorageEnabled=true
        web.settings.allowFileAccess=false;web.settings.allowContentAccess=false
        web.settings.mixedContentMode=android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW
        web.settings.builtInZoomControls=true;web.settings.displayZoomControls=false
        web.settings.loadWithOverviewMode=true;web.settings.useWideViewPort=true
        web.webViewClient=object:WebViewClient(){
            override fun shouldOverrideUrlLoading(view:WebView,request:WebResourceRequest):Boolean = try{Policy.https(request.url.toString());false}catch(e:Exception){true}
            override fun onReceivedSslError(view:WebView,handler:SslErrorHandler,error:SslError){handler.cancel();Toast.makeText(this@RemoteActivity,"TLS certificate rejected",Toast.LENGTH_LONG).show()}
            override fun onReceivedError(view:WebView,request:WebResourceRequest,error:WebResourceError){if(request.isForMainFrame)Toast.makeText(this@RemoteActivity,"Connection failed. Check Tailscale and the private address.",Toast.LENGTH_LONG).show()}
            override fun onPageFinished(view:WebView,url:String){view.evaluateJavascript("""(function(){let m=document.querySelector('meta[name=viewport]');if(!m){m=document.createElement('meta');m.name='viewport';document.head.appendChild(m)}m.content='width=device-width,initial-scale=1';window.dispatchEvent(new Event('resize'));})();""",null)}
        }
        root.addView(web,FrameLayout.LayoutParams(-1,-1))
        val exit=Button(this).apply{text="✕";contentDescription="Exit remote full screen";alpha=0.8f;setOnClickListener{finish()}}
        val size=(52*resources.displayMetrics.density).toInt();root.addView(exit,FrameLayout.LayoutParams(size,size,Gravity.TOP or Gravity.END))
        setContentView(root)
        if(savedInstanceState==null)web.loadUrl(address) else web.restoreState(savedInstanceState)
    }
    override fun onWindowFocusChanged(hasFocus:Boolean){super.onWindowFocusChanged(hasFocus);if(hasFocus){
        if(android.os.Build.VERSION.SDK_INT>=30){window.insetsController?.hide(WindowInsets.Type.systemBars());window.insetsController?.systemBarsBehavior=android.view.WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE}
        else {@Suppress("DEPRECATION") window.decorView.systemUiVisibility=View.SYSTEM_UI_FLAG_FULLSCREEN or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY}
    }}
    override fun onSaveInstanceState(outState:Bundle){web.saveState(outState);super.onSaveInstanceState(outState)}
    override fun onDestroy(){if(::web.isInitialized){web.stopLoading();web.loadUrl("about:blank");web.destroy()};super.onDestroy()}
}
