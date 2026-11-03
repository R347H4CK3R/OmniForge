package com.r347h4ck3r.omniforge
import org.junit.Assert.*
import org.junit.Test
import java.io.File
class PolicyTest {
    @Test fun privateHttpsAccepted() { assertEquals("https://host.test:8443/vnc.html", Policy.https("https://host.test:8443/vnc.html")) }
    @Test(expected=IllegalArgumentException::class) fun cleartextRejected() { Policy.https("http://host.test") }
    @Test(expected=IllegalArgumentException::class) fun credentialsRejected() { Policy.https("https://secret@host.test") }
    @Test(expected=IllegalArgumentException::class) fun traversalRejected() { Policy.workspace(File("/tmp/omni"), "../other") }
    @Test fun workspaceChildAccepted() { assertEquals("/tmp/omni/a.kt", Policy.workspace(File("/tmp/omni"), "a.kt").path) }
    @Test(expected=IllegalArgumentException::class) fun apkTraversalRejected() { Policy.archiveName("res/../../other") }
    @Test(expected=IllegalArgumentException::class) fun windowsArchiveRejected() { Policy.archiveName("C:/bad") }
    @Test(expected=IllegalArgumentException::class) fun invalidDigestRejected() { Policy.digest("abc") }
}
