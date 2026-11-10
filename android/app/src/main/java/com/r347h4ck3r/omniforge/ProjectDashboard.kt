package com.r347h4ck3r.omniforge

import android.app.Activity
import android.graphics.Color
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import org.json.JSONObject
import java.net.HttpURLConnection
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/** A separate, cancellable read-only request. It never occupies the agent worker. */
class ProjectDashboard(private val activity: Activity, private val container: LinearLayout,
                       private val endpoint: () -> String, private val token: () -> String) {
    private val executor = Executors.newSingleThreadExecutor()
    private val timer = Executors.newSingleThreadScheduledExecutor()
    private var activeRequest: ProjectRequestLifecycle? = null
    private var generation = 0
    private var closed = false
    private val refresh = Button(activity).apply { text = "Refresh host readiness"; isAllCaps = false }
    private val result = TextView(activity).apply { setTextColor(Color.LTGRAY); textSize = 14f }
    init {
        container.addView(TextView(activity).apply { text = "Host project readiness"; textSize = 22f; setTextColor(Color.WHITE) })
        container.addView(result)
        container.addView(refresh)
        result.text = "Read-only snapshot. Refresh to inspect project prerequisites and stored queue status. No builds, updates or installations are started."
        refresh.setOnClickListener { load() }
    }
    private fun load() {
        if (closed || !refresh.isEnabled) return
        val url = try { ProjectDashboardPolicy.endpoint(endpoint()).toURL() } catch (_: Exception) {
            result.text = "Configure a valid HTTPS host address without URL credentials, query or fragment in Settings."; return
        }
        val key = token().trim()
        if (key.isEmpty() || key.any { it.isWhitespace() }) { result.text = "Configure your private agent API token in Settings."; return }
        val request = ++generation
        val lifecycle = ProjectRequestLifecycle()
        activeRequest = lifecycle
        refresh.isEnabled = false
        result.text = "Reading host readiness…"
        // A wall-clock deadline also bounds slow trickle responses. Generation rejects late results.
        val deadline = timer.schedule({
            if (lifecycle.cancel()) activity.runOnUiThread {
                if (!closed && request == generation) {
                    generation++; refresh.isEnabled = true
                    result.text = "The host did not respond within 20 seconds. Check the connection and retry."
                }
            }
        }, 20, TimeUnit.SECONDS)
        executor.execute {
            if (!lifecycle.isActive || Thread.currentThread().isInterrupted) {
                deadline.cancel(false)
                return@execute
            }
            var c: HttpURLConnection? = null
            var accepted = false
            val message = try {
                val ownedConnection = url.openConnection() as HttpURLConnection
                c = ownedConnection
                c.instanceFollowRedirects = false; c.useCaches = false
                c.connectTimeout = 8000; c.readTimeout = 8000
                c.setRequestProperty("Authorization", "Bearer $key")
                c.setRequestProperty("Accept", "application/json")
                c.setRequestProperty("Cache-Control", "no-store")
                if (!lifecycle.attach { ownedConnection.disconnect() } || !lifecycle.begin()) {
                    return@execute
                }
                when (c.responseCode) {
                    200 -> c.inputStream.bufferedReader().use { render(ProjectDashboardPolicy.read(it, 524288)) }
                    401, 403 -> "Authorization rejected. Check your saved API token in Settings."
                    404 -> "This host does not support project readiness yet. Update the host service separately."
                    in 300..399 -> "Host redirected the request. No credentials were forwarded. Check the host address in Settings."
                    else -> "Host readiness unavailable (HTTP ${c.responseCode}). Try again later."
                }
            } catch (_: Exception) { "Could not read a valid readiness report. Check the host connection and try again." }
            finally { accepted = lifecycle.finish(); c?.disconnect(); deadline.cancel(false) }
            activity.runOnUiThread {
                if (accepted && !closed && !activity.isDestroyed && request == generation) { result.text = message; refresh.isEnabled = true }
            }
        }
    }
    fun cancel() {
        generation++; activeRequest?.cancel(); activeRequest = null
        refresh.isEnabled = true
        result.text = "Refresh to read a current host snapshot."
    }
    fun close() {
        closed = true; cancel()
        executor.shutdownNow(); timer.shutdownNow()
    }
    companion object {
        fun render(body: String): String {
            val report = JSONObject(body)
            require(report.getInt("schema") == 1 && report.getBoolean("read_only") && !report.getBoolean("execution_enabled"))
            val scan = report.getJSONObject("scan")
            val projects = report.getJSONArray("projects")
            val queue = report.getJSONObject("queue")
            val lines = mutableListOf("Snapshot: ${report.getString("generated_at")}", "Detection is not a successful build. Builds remain unverified.")
            if (scan.getBoolean("truncated")) lines += "Partial scan: entry limit reached."
            val blockers = scan.getJSONArray("blockers")
            for (i in 0 until blockers.length()) lines += "Partial scan: ${blockers.getString(i)}"
            if (projects.length() == 0) lines += "No supported projects detected in the scanned workspace."
            require(projects.length() <= 101)
            for (i in 0 until projects.length()) {
                val project = projects.getJSONObject(i)
                lines += "\n${project.getString("path").let { if (it == ".") "Workspace root" else it }}"
                val targets = project.getJSONArray("targets")
                require(targets.length() <= 16)
                for (j in 0 until targets.length()) {
                    val target = targets.getJSONObject(j)
                    val state = when (target.getString("status")) {
                        "blocked" -> "Blocked"
                        "prerequisites_detected" -> "Prerequisites detected"
                        else -> "Unknown readiness"
                    }
                    lines += "${target.getString("platform").uppercase()}: $state · build unverified"
                    val reasons = target.getJSONArray("blockers")
                    for (k in 0 until reasons.length()) lines += "• ${reasons.getString(k)}"
                }
            }
            lines += "\nRemote Mac: ${report.getJSONObject("remote_mac").getString("status").replace('_', ' ')}"
            lines += report.getJSONObject("remote_mac").optString("blocker")
            lines += "\nQueue: ${queue.getString("status").replace('_', ' ')}"
            lines += "Stored statuses only; worker liveness and build success are not verified."
            if (queue.has("blocker")) lines += queue.getString("blocker")
            val jobs = queue.getJSONArray("jobs")
            require(jobs.length() <= 30)
            if (jobs.length() == 0) lines += "No stored jobs shown."
            for (i in 0 until jobs.length()) {
                val job = jobs.getJSONObject(i)
                lines += "${job.getString("id")}: ${job.getString("status")} (attempts: ${job.getInt("attempts")})"
            }
            if (queue.getBoolean("truncated")) lines += "Only the latest 30 jobs are shown."
            return lines.joinToString("\n")
        }
    }
}
