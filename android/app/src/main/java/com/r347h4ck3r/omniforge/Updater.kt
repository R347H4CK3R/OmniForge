package com.r347h4ck3r.omniforge
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import org.json.JSONObject
import java.io.File

object Updater {
    const val CATALOG="https://raw.githubusercontent.com/R347H4CK3R/OmniForge/main/android-source.json"
    fun check(activity:Activity):JSONObject {
        val release=JSONObject(Net.request(CATALOG))
        require(release.getString("applicationId")==activity.packageName){"Catalog app ID mismatch"}
        Policy.https(release.getString("downloadUrl"));Policy.digest(release.getString("sha256"))
        return release
    }
    @Suppress("DEPRECATION")
    fun fetch(activity:Activity,release:JSONObject):File {
        val p=activity.packageManager
        val current=p.getPackageInfo(activity.packageName,PackageManager.GET_SIGNING_CERTIFICATES)
        val version=if(Build.VERSION.SDK_INT>=28)current.longVersionCode else current.versionCode.toLong()
        require(release.getLong("versionCode")>version){"You already have this version or newer"}
        val out=File(activity.cacheDir,"updates/OmniForge.apk").apply{parentFile?.mkdirs()}
        Net.download(release.getString("downloadUrl"),out,release.getString("sha256"))
        try {
            val downloaded=p.getPackageArchiveInfo(out.path,PackageManager.GET_SIGNING_CERTIFICATES) ?: error("Invalid APK")
            require(downloaded.packageName==activity.packageName){"APK package mismatch"}
            val actualVersion=if(Build.VERSION.SDK_INT>=28)downloaded.longVersionCode else downloaded.versionCode.toLong()
            require(actualVersion==release.getLong("versionCode")){"APK version mismatch"}
            if(Build.VERSION.SDK_INT>=28){
                val installed=current.signingInfo?.apkContentsSigners?.map{it.toCharsString()}?.toSet()
                val incoming=downloaded.signingInfo?.apkContentsSigners?.map{it.toCharsString()}?.toSet()
                require(!installed.isNullOrEmpty() && installed==incoming){"APK signer differs from installed app"}
            } else {
                val old=p.getPackageInfo(activity.packageName,PackageManager.GET_SIGNATURES).signatures?.map{it.toCharsString()}?.toSet()
                val next=p.getPackageArchiveInfo(out.path,PackageManager.GET_SIGNATURES)?.signatures?.map{it.toCharsString()}?.toSet()
                require(!old.isNullOrEmpty() && old==next){"APK signer mismatch"}
            }
            return out
        }catch(e:Exception){out.delete();throw e}
    }
    fun install(activity:Activity,file:File) {
        if(!activity.packageManager.canRequestPackageInstalls()){
            activity.startActivity(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,Uri.parse("package:${activity.packageName}")))
            android.widget.Toast.makeText(activity,"Allow updates from OmniForge, then tap Install downloaded update again",android.widget.Toast.LENGTH_LONG).show();return
        }
        val uri=FileProvider.getUriForFile(activity,"${activity.packageName}.files",file)
        activity.startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(uri,"application/vnd.android.package-archive").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
    }
}
