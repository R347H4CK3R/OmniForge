package com.r347h4ck3r.omniforge

import java.io.File
import java.net.URI

object Policy {
    fun https(value: String): String {
        val u = URI(value.trim())
        require(u.scheme == "https" && !u.host.isNullOrBlank() && u.userInfo == null) { "Use an HTTPS address without embedded credentials" }
        require(u.fragment == null) { "Remove the URL fragment" }
        return u.toASCIIString()
    }
    fun workspace(root: File, path: String): File {
        require(path.isNotBlank() && !path.contains('\u0000')) { "Empty or invalid path" }
        val f = File(root, path).canonicalFile
        require(f.path == root.canonicalPath || f.path.startsWith(root.canonicalPath + File.separator)) { "Path outside workspace" }
        return f
    }
    fun archiveName(name: String) {
        require(!name.startsWith('/') && !name.contains('\\') && !name.contains(':') && name.split('/').none { it == ".." }) { "Unsafe archive path" }
    }
    fun digest(value: String): String { require(Regex("[0-9a-fA-F]{64}").matches(value)) { "Invalid SHA-256" }; return value.lowercase() }
}
