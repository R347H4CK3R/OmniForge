package com.r347h4ck3r.omniforge;

/** One request owns one cancellation action. Never consults a shared current connection. */
public final class ProjectRequestLifecycle {
    private boolean active = true;
    private boolean started;
    private Runnable disconnect;

    public boolean attach(Runnable action) {
        synchronized (this) {
            if (active) { disconnect = action; return true; }
        }
        action.run();
        return false;
    }
    /** Called by the worker immediately before starting I/O, not when queued. */
    public synchronized boolean begin() {
        if (!active || started || Thread.currentThread().isInterrupted()) return false;
        started = true;
        return true;
    }
    public synchronized boolean isActive() { return active; }
    public boolean cancel() {
        Runnable action;
        synchronized (this) {
            if (!active) return false;
            active = false;
            action = disconnect;
            disconnect = null;
        }
        if (action != null) action.run();
        return true;
    }
    public synchronized boolean finish() {
        boolean accepted = active;
        active = false; disconnect = null;
        return accepted;
    }
}
