package com.r347h4ck3r.omniforge
object NativeModel {
    init { System.loadLibrary("omniforge-llama") }
    external fun generate(path: String, prompt: String, threads: Int): String
}
