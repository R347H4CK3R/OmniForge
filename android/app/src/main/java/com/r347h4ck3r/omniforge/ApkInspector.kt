package com.r347h4ck3r.omniforge
import android.content.Context
import android.content.pm.PackageManager
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.util.zip.ZipFile
object ApkInspector {
    fun inspect(context: Context, file: File): JSONObject {
        val names=mutableListOf<String>();var total=0L
        ZipFile(file).use { z -> val entries=z.entries();while(entries.hasMoreElements()) { val e=entries.nextElement();Policy.archiveName(e.name);require(names.size<50000){"Too many ZIP entries"};require(e.size>=0){"Invalid ZIP size"};total+=e.size;require(total<=2L*1024*1024*1024){"Archive too large"};names.add(e.name) } }
        require(names.contains("AndroidManifest.xml")){"Not an APK: manifest missing"}
        @Suppress("DEPRECATION") val info=context.packageManager.getPackageArchiveInfo(file.path,PackageManager.GET_PERMISSIONS or PackageManager.GET_SIGNING_CERTIFICATES)
        val certificates=if(android.os.Build.VERSION.SDK_INT>=28)info?.signingInfo?.apkContentsSigners else {
            @Suppress("DEPRECATION") val legacy=context.packageManager.getPackageArchiveInfo(file.path,PackageManager.GET_SIGNATURES)
            @Suppress("DEPRECATION") val signatures=legacy?.signatures
            signatures
        }
        val signerHashes=certificates?.map{cert->MessageDigest.getInstance("SHA-256").digest(cert.toByteArray()).joinToString(""){"%02x".format(it)}} ?: emptyList()
        val hash=MessageDigest.getInstance("SHA-256");file.inputStream().use { val b=ByteArray(65536);while(true){val n=it.read(b);if(n<0)break;hash.update(b,0,n)} }
        return JSONObject().put("package",info?.packageName ?: "Unparsed").put("version",info?.versionName ?: "Unknown").put("entries",names.size)
            .put("sha256",hash.digest().joinToString(""){"%02x".format(it)}).put("permissions",JSONArray(info?.requestedPermissions?.toList() ?: emptyList<String>()))
            .put("dex_files",JSONArray(names.filter{it.endsWith(".dex")})).put("abis",JSONArray(names.filter{it.startsWith("lib/")}.mapNotNull{it.split('/').getOrNull(1)}.distinct()))
            .put("signer_sha256",JSONArray(signerHashes)).put("signature_validation","Certificate parsing only; Android installation performs final signature validation").put("files",JSONArray(names.take(5000))).put("original_source_recovered",false).put("note","Read-only APK inspection. Decompiled code and rebuilt behavior require separate verification.")
    }
}
