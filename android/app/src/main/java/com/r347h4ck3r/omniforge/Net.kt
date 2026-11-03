package com.r347h4ck3r.omniforge
import java.net.HttpURLConnection
import java.net.URL
import java.io.File
import java.security.MessageDigest

object Net {
    fun request(address: String, body: String? = null, token: String = ""): String {
        val c = URL(Policy.https(address)).openConnection() as HttpURLConnection
        c.connectTimeout = 20000; c.readTimeout = 180000; c.instanceFollowRedirects = false
        try {
            if (token.isNotBlank()) c.setRequestProperty("Authorization", "Bearer $token")
            if (body != null) { c.requestMethod = "POST"; c.doOutput = true; c.setRequestProperty("Content-Type", "application/json"); c.outputStream.use { it.write(body.toByteArray()) } }
            require(c.responseCode in 200..299) { "HTTP ${c.responseCode}: ${c.errorStream?.bufferedReader()?.use { it.readText().take(500) } ?: "Connection rejected"}" }
            return c.inputStream.bufferedReader().use { reader ->
                val out = StringBuilder(); val buf = CharArray(4096)
                while (true) { val n = reader.read(buf); if (n < 0) break; require(out.length + n <= 2_000_000) { "Response too large" }; out.append(buf, 0, n) }; out.toString()
            }
        } finally { c.disconnect() }
    }
    fun download(address: String, out: File, expected: String, limit: Long = 256L*1024*1024) {
        var current = Policy.https(address)
        for (attempt in 0..5) {
            val c = URL(current).openConnection() as HttpURLConnection
            c.instanceFollowRedirects = false; c.connectTimeout = 20000; c.readTimeout = 60000
            try {
                if (c.responseCode in listOf(301,302,303,307,308)) { current = Policy.https(URL(URL(current), c.getHeaderField("Location")).toString()); continue }
                require(c.responseCode == 200) { "Download HTTP ${c.responseCode}" }
                val hash = MessageDigest.getInstance("SHA-256"); var bytes = 0L
                try {
                    c.inputStream.use { input -> out.outputStream().use { output -> val buffer = ByteArray(65536); while(true) { val n=input.read(buffer); if(n<0)break; bytes+=n; require(bytes<=limit){"Download exceeds size limit"}; hash.update(buffer,0,n);output.write(buffer,0,n) } } }
                    require(hash.digest().joinToString("") { "%02x".format(it) } == Policy.digest(expected)) { "Download SHA-256 mismatch" }
                    return
                } catch (e: Exception) { out.delete(); throw e }
            } finally { c.disconnect() }
        }
        error("Too many download redirects")
    }
}
