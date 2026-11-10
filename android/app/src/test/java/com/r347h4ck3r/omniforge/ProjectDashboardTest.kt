package com.r347h4ck3r.omniforge

import org.junit.Assert.*
import org.junit.Test
import java.io.StringReader
import java.io.IOException

class ProjectDashboardTest {
    @Test fun proxyPrefixIsPreserved() {
        assertEquals("https://host.test:8443/proxy/android-api/v1/projects",
            ProjectDashboardPolicy.endpoint("https://host.test:8443/proxy/android-api/").toString())
        assertEquals("https://host.test/v1/projects", ProjectDashboardPolicy.endpoint("https://host.test").toString())
        assertEquals("https://host.test/a%20b/v1/projects", ProjectDashboardPolicy.endpoint("https://host.test/a%20b").toString())
    }
    @Test fun unsafeAddressesAreRejected() {
        listOf("http://host.test", "https://secret@host.test", "https://host.test/?token=x", "https://host.test/#x", "https:///empty").forEach {
            try { ProjectDashboardPolicy.endpoint(it); fail("Unsafe endpoint accepted") } catch (_: IllegalArgumentException) {}
        }
    }
    @Test fun readsAreBounded() {
        assertEquals("abc", ProjectDashboardPolicy.read(StringReader("abc"), 3))
        try { ProjectDashboardPolicy.read(StringReader("abcd"), 3); fail("Oversized report accepted") } catch (_: IOException) {}
    }

    private val emptyReport = """{"schema":1,"generated_at":"today","read_only":true,"execution_enabled":false,"scan":{"truncated":false,"blockers":[]},"projects":[],"queue":{"status":"not_initialized","jobs":[],"truncated":false},"remote_mac":{"status":"not_configured"}}"""
    @Test fun emptyReportExplainsLimits() {
        val text = ProjectDashboard.render(emptyReport)
        assertTrue(text.contains("No supported projects detected"))
        assertTrue(text.contains("Remote Mac: not configured"))
        assertTrue(text.contains("No stored jobs shown"))
        assertTrue(text.contains("Builds remain unverified"))
    }
    @Test fun partialReportSeparatesPrerequisitesFromBuildSuccess() {
        val report = org.json.JSONObject(emptyReport)
        report.getJSONObject("scan").put("truncated", true)
        report.put("projects", org.json.JSONArray("""[{"path":"Demo","targets":[{"platform":"android","status":"prerequisites_detected","blockers":[],"build_verified":false},{"platform":"ios","status":"blocked","blockers":["Needs Mac"],"build_verified":false}]}]"""))
        report.getJSONObject("queue").put("jobs", org.json.JSONArray("""[{"id":"job-1","status":"running","attempts":1}]"""))
        val text = ProjectDashboard.render(report.toString())
        assertTrue(text.contains("Partial scan"))
        assertTrue(text.contains("ANDROID: Prerequisites detected · build unverified"))
        assertTrue(text.contains("IOS: Blocked · build unverified"))
        assertTrue(text.contains("Needs Mac"))
        assertTrue(text.contains("job-1: running"))
    }
    @Test(expected=IllegalArgumentException::class) fun unknownSchemaIsRejected() {
        ProjectDashboard.render(emptyReport.replace("\"schema\":1", "\"schema\":2"))
    }
    @Test(expected=org.json.JSONException::class) fun incompleteReportIsRejected() {
        ProjectDashboard.render("{}")
    }

    @Test fun cancelledQueuedRequestCannotBegin() {
        val request = ProjectRequestLifecycle()
        assertTrue(request.cancel())
        assertFalse(request.begin())
        var closed = false
        assertFalse(request.attach { closed = true })
        assertTrue(closed)
    }
    @Test fun oldDeadlineCannotCancelNewRequest() {
        var oldClosed = 0
        var newClosed = 0
        val old = ProjectRequestLifecycle()
        val newer = ProjectRequestLifecycle()
        old.attach { oldClosed++ }; assertTrue(old.begin())
        newer.attach { newClosed++ }; assertTrue(newer.begin())
        assertTrue(old.cancel()); assertFalse(old.cancel())
        assertEquals(1, oldClosed); assertEquals(0, newClosed)
        assertTrue(newer.isActive)
        newer.finish()
        assertFalse(newer.cancel())
        assertEquals(0, newClosed)
    }
}
