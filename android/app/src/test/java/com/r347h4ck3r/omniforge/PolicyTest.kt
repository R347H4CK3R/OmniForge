package com.r347h4ck3r.omniforge
import org.junit.Assert.*
import org.junit.Test
import java.io.File
class PolicyTest {
    @Test fun errorBodyIsBoundedBeforeAllocation() {
        val reader=object:java.io.Reader(){var remaining=1000000;var consumed=0
            override fun close(){};override fun read(b:CharArray,off:Int,len:Int):Int{val n=minOf(len,remaining);if(n==0)return -1;for(i in 0 until n)b[off+i]='x';remaining-=n;consumed+=n;return n}}
        assertEquals(500,Policy.prefix(reader,500).length);assertEquals(500,reader.consumed)
    }
    @Test fun privateHttpsAccepted() { assertEquals("https://host.test:8443/vnc.html", Policy.https("https://host.test:8443/vnc.html")) }
    @Test(expected=IllegalArgumentException::class) fun cleartextRejected() { Policy.https("http://host.test") }
    @Test(expected=IllegalArgumentException::class) fun credentialsRejected() { Policy.https("https://secret@host.test") }
    @Test(expected=IllegalArgumentException::class) fun traversalRejected() { Policy.workspace(File("/tmp/omni"), "../other") }
    @Test fun workspaceChildAccepted() { assertEquals("/tmp/omni/a.kt", Policy.workspace(File("/tmp/omni"), "a.kt").path) }
    @Test(expected=IllegalArgumentException::class) fun apkTraversalRejected() { Policy.archiveName("res/../../other") }
    @Test(expected=IllegalArgumentException::class) fun windowsArchiveRejected() { Policy.archiveName("C:/bad") }
    @Test(expected=IllegalArgumentException::class) fun invalidDigestRejected() { Policy.digest("abc") }
}
